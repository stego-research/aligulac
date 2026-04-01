#!/usr/bin/env python3

import os
import subprocess
from datetime import datetime
from subprocess import Popen

import boto3
from botocore.config import Config

from aligulac.settings import (
    DATABASES,
    DUMP_PATH,
    S3_BUCKET,
    S3_ACCESS_KEY,
    S3_SECRET_KEY,
    S3_REGION,
    S3_ENDPOINT_URL,
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


dt = datetime.now()

# {{{ Backup and private dump

info("Dumping full database.")

pg_dump = [
    "pg_dump", "-O", "-c",
    "-U", DATABASES['default']['USER'],
    "-h", DATABASES['default']['HOST'],
    "-p", str(DATABASES['default']['PORT']),
    DATABASES['default']['NAME']
]

env = os.environ.copy()
if DATABASES['default']['PASSWORD']:
    env['PGPASSWORD'] = DATABASES['default']['PASSWORD']

full_path = os.path.join(DUMP_PATH, 'full.sql.gz')
with open(full_path, "w") as f:
    p_pg = Popen(pg_dump, stdout=subprocess.PIPE, env=env)
    p_gzip = Popen(["gzip"], stdin=p_pg.stdout, stdout=f)
    p_gzip.communicate()
# }}}

# {{{ Public dump

info("Dumping public database.")

public_path = os.path.join(DUMP_PATH, 'aligulac.sql')

pub_pg_dump = pg_dump[:9]

for tbl in public_tables:
    pub_pg_dump.extend(['-t', tbl])

pub_pg_dump.append(pg_dump[-1])

with open(public_path, 'w') as f:
    subprocess.call(pub_pg_dump, stdout=f, env=env)


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
    info("Uploading {} to S3://{}/{}".format(source, S3_BUCKET, destination))
    s3_kwargs = {
        'region_name': S3_REGION,
        'endpoint_url': S3_ENDPOINT_URL,
        'config': Config(signature_version='s3v4'),
    }
    if S3_ACCESS_KEY and S3_SECRET_KEY:
        s3_kwargs['aws_access_key_id'] = S3_ACCESS_KEY
        s3_kwargs['aws_secret_access_key'] = S3_SECRET_KEY

    s3 = boto3.client('s3', **s3_kwargs)
    s3.upload_file(source, S3_BUCKET, destination)


if S3_BUCKET:
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
