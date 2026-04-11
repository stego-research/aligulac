#!/usr/bin/env python3

import os
import re
import subprocess
from datetime import datetime
from subprocess import Popen

import boto3
from botocore.config import Config

from aligulac.settings import (
    DATABASES,
    DB_SCHEMA,
    DUMP_PATH,
    S3_DB_BUCKET,
    S3_DB_ACCESS_KEY,
    S3_DB_SECRET_KEY,
    S3_DB_REGION,
    S3_DB_ENDPOINT_URL,
)

public_tables = [
    'alias',
    'earnings',
    'event',
    'eventadjacency',
    'group',
    'groupmembership',
    'match',
    'message',
    'period',
    'player',
    'rating',
    'story',
]


def info(string):
    print("[{}]: {}".format(datetime.now(), string), flush=True)


def perform_sanity_check(path, schema, tables, check_empty=True):
    info("Performing sanity check on dump (expecting schema: {}).".format(schema))
    allowed_tables_set = set(tables)
    found_tables = set()
    with open(path, 'r') as f:
        for line in f:
            # Check for schema markers in pg_dump comments
            if "Schema: " in line:
                m = re.search(r'Schema: ([\w"]+);', line)
                if m and m.group(1).strip('"') != schema:
                    raise Exception("SECURITY ALERT: Found unauthorized schema '{}' in dump!".format(m.group(1)))

            # Check for table/data markers
            # Matches: CREATE TABLE schema.table, COPY schema.table, ALTER TABLE schema.table
            m = re.search(r'(?:CREATE TABLE|COPY|ALTER TABLE) (?:(?P<schema>[\w"]+)\.)?(?P<table>[\w"]+)', line)
            if m:
                found_schema = m.group('schema')
                found_table = m.group('table').strip('"')

                if found_schema and found_schema.strip('"') != schema:
                     raise Exception("SECURITY ALERT: Found unauthorized schema '{}' in dump!".format(found_schema))

                # Only check table name if it's a CREATE TABLE or COPY
                if "CREATE TABLE" in line or "COPY" in line:
                    if found_table not in allowed_tables_set:
                        raise Exception("SECURITY ALERT: Found unauthorized table '{}' in dump!".format(found_table))
                    found_tables.add(found_table)
    
    if check_empty and not found_tables:
        raise Exception("SECURITY ALERT: No authorized tables found in dump! The dump is likely empty or failed.")

    info("Sanity check passed (found {}/{} tables).".format(len(found_tables), len(tables)))


def rewrite_schema(path, old_schema, new_schema, rewrite=False):
    if not rewrite or old_schema == new_schema:
        return
    info("Rewriting schema from '{}' to '{}' in {} (skipping data blocks).".format(old_schema, new_schema, path))
    
    temp_path = path + '.tmp'
    # Matches "schema". or schema. (qualifiers for tables, indexes, etc.)
    schema_dot_pattern = re.compile(r'(\b|"){}(\b|")\.'.format(re.escape(old_schema)))
    # Matches search_path = schema or search_path = "schema"
    search_path_pattern = re.compile(r'search_path = ([\'"]?){}([\'"]?)(,|\s|;)'.format(re.escape(old_schema)))
    # Matches Schema: schema; in pg_dump comments
    schema_comment_pattern = re.compile(r'Schema: ([\'"]?){}([\'"]?);'.format(re.escape(old_schema)))
    
    in_copy_data = False
    with open(path, 'r') as fin, open(temp_path, 'w') as fout:
        for line in fin:
            # Detect start of data block
            if line.startswith('COPY '):
                # The COPY command itself needs the rewrite so the table is found
                line = schema_dot_pattern.sub(r'\1{}\2.'.format(new_schema), line)
                fout.write(line)
                in_copy_data = True
                continue
            # Detect end of data block
            elif line.strip() == r'\.':
                in_copy_data = False
                fout.write(line)
                continue
            
            # Only perform replacements if we are NOT inside a COPY data block
            if not in_copy_data:
                line = schema_dot_pattern.sub(r'\1{}\2.'.format(new_schema), line)
                line = search_path_pattern.sub(r'search_path = \1{}\2\3'.format(new_schema), line)
                line = schema_comment_pattern.sub(r'Schema: \1{}\2;'.format(new_schema), line)
            
            fout.write(line)
            
    os.replace(temp_path, path)


dt = datetime.now()

# {{{ Backup and private dump

info("Dumping full database.")

pg_dump = [
    "pg_dump", "-O", "-c",
    "-n", DB_SCHEMA,
    "-U", DATABASES['default']['USER'],
    "-h", DATABASES['default']['HOST'],
    "-p", str(DATABASES['default']['PORT']),
    DATABASES['default']['NAME']
]

env = os.environ.copy()
if DATABASES['default']['PASSWORD']:
    env['PGPASSWORD'] = DATABASES['default']['PASSWORD']

# Set search_path to the DB_SCHEMA to ensure pg_dump finds tables correctly,
# especially when using -t which ignores -n.
env['PGOPTIONS'] = f"-c search_path={DB_SCHEMA},public"

full_path = os.path.join(DUMP_PATH, 'full.sql.gz')
with open(full_path, "w") as f:
    # Use Popen to capture stderr and pipe stdout to gzip
    p_pg = Popen(pg_dump, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    p_gzip = Popen(["gzip"], stdin=p_pg.stdout, stdout=f)
    
    # Allow p_pg to receive a SIGPIPE if p_gzip exits
    p_pg.stdout.close()
    p_gzip.communicate()
    
    # Check for pg_dump failure
    if p_pg.wait() != 0:
        # pg_dump failed, capture stderr for report
        err_msg = p_pg.stderr.read().decode()
        raise Exception("pg_dump failed (full dump):\n{}".format(err_msg))
# }}}

# {{{ Public dump

info("Dumping public database.")

public_path = os.path.join(DUMP_PATH, 'aligulac.sql')

# Construct the public dump command. 
# Note that pg_dump ignores -n when -t is used, so we rely on search_path in PGOPTIONS.
pub_pg_dump = pg_dump[:11]
for tbl in public_tables:
    pub_pg_dump.extend(['-t', tbl])
pub_pg_dump.append(pg_dump[-1])

with open(public_path, 'w') as f:
    # Use Popen to capture stderr
    p_pub = Popen(pub_pg_dump, stdout=f, stderr=subprocess.PIPE, env=env)
    _, stderr = p_pub.communicate()
    if p_pub.returncode != 0:
        raise Exception("pg_dump failed (public dump):\n{}".format(stderr.decode()))

# Schema rewriting is disabled by default for safety.
# Set rewrite=True once you have verified the transformation in a staging environment.
rewrite_schema(public_path, DB_SCHEMA, 'public', rewrite=False)
perform_sanity_check(public_path, DB_SCHEMA, public_tables)


# }}}

# {{{ Compress/decompress files

def compress_file(source):
    info("Compressing {}".format(source))
    with open(source, "r") as src:
        with open(source + ".gz", "w") as dst:
            subprocess.call(["gzip"], stdin=src, stdout=dst)


def decompress_file(source):
    info("Decompressing {}".format(source))
    with open(source, "r") as src:
        with open(source[:-3], "w") as dst:
            subprocess.call(["gunzip"], stdin=src, stdout=dst)


compress_file(public_path)
decompress_file(full_path)


# }}}

# {{{ Upload to S3

def upload_to_s3(source, destination):
    info("Uploading {} to S3://{}/{}".format(source, S3_DB_BUCKET, destination))
    s3_kwargs = {
        'region_name': S3_DB_REGION,
        'endpoint_url': S3_DB_ENDPOINT_URL,
        'config': Config(signature_version='s3v4'),
    }
    if S3_DB_ACCESS_KEY and S3_DB_SECRET_KEY:
        s3_kwargs['aws_access_key_id'] = S3_DB_ACCESS_KEY
        s3_kwargs['aws_secret_access_key'] = S3_DB_SECRET_KEY

    s3 = boto3.client('s3', **s3_kwargs)
    s3.upload_file(source, S3_DB_BUCKET, destination)


if S3_DB_BUCKET:
    upload_to_s3(os.path.join(DUMP_PATH, 'aligulac.sql'), 'aligulac.sql')
    upload_to_s3(os.path.join(DUMP_PATH, 'aligulac.sql.gz'), 'aligulac.sql.gz')
    upload_to_s3(os.path.join(DUMP_PATH, 'full.sql'), 'full.sql')
    upload_to_s3(os.path.join(DUMP_PATH, 'full.sql.gz'), 'full.sql.gz')
    # Removing local files after upload as requested "instead of to the local filesystem"
    os.remove(os.path.join(DUMP_PATH, 'aligulac.sql'))
    os.remove(os.path.join(DUMP_PATH, 'aligulac.sql.gz'))
    os.remove(os.path.join(DUMP_PATH, 'full.sql'))
    os.remove(os.path.join(DUMP_PATH, 'full.sql.gz'))

# }}}
