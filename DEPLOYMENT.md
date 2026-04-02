# Aligulac Deployment Guide

This guide outlines how to deploy Aligulac using two primary methods: **Docker/Podman** (recommended) or **Manual Setup** on Amazon Linux 2023.

---

## 1. Container Deployment (Docker/Podman)

The recommended way to deploy Aligulac is using the provided Docker image. This image is minimal, secure, and pre-configured for production.

### Build the Image
```bash
make build-image
```

### Run the Container
```bash
docker run -d \
  -p 8000:8000 \
  -e SECRET_KEY="your-secret-key" \
  -e DB_HOST="your-db-host" \
  -e DB_NAME="aligulac" \
  -e DB_USER="postgres" \
  -e DB_PASSWORD="your-password" \
  -e S3_BUCKET_DB="your-aligulac-dumps-bucket" \
  --name aligulac-app \
  aligulac-app:latest
```

---

## 2. Configuration (Environment Variables)

The application is configured via environment variables. These can be passed to Docker or set in your shell for manual deployment.

### **Required for Production**
| Variable | Description | Default |
| :--- | :--- | :--- |
| `SECRET_KEY` | A long, random string used for security. | `change-me` |
| `DB_HOST` | Database server address (e.g., RDS endpoint). | `127.0.0.1` |
| `DB_PORT` | Database server port. | `5432` |
| `DB_SSLMODE` | SSL mode for PostgreSQL (`prefer`, `require`, `disable`). | `prefer` |
| `DB_NAME` | Name of the PostgreSQL database. | `aligulac` |
| `DB_USER` | PostgreSQL username. | `postgres` |
| `DB_PASSWORD` | PostgreSQL password. | `postgres` |
| `ALLOWED_HOSTS` | Comma-separated list of domains/IPs (e.g. `aligulac.com,1.2.3.4`). | `*` |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated list of trusted origins (e.g. `https://aligulac.stego.ai`). | `""` |

### **Optional Configuration**
| Variable | Description | Default |
| :--- | :--- | :--- |
| `DEBUG` | Enable/Disable Django debug mode (`True`/`False`). | `False` |
| `DEBUG_TOOLBAR`| Enable/Disable the debug toolbar. | `False` |
| `ERROR_LOG_FILE`| Path where application errors are logged. | `/var/log/aligulac/error.log` |
| `CACHE_BACKEND` | Django cache backend. | `DummyCache` |
| `CACHE_LOCATION`| Cache location (URL for Redis, path for File). | `/app/aligulac/untracked/cache/` |
| `EXCHANGE_ID` | API key for openexchangerates.org. | `""` |

### **Redis Cache (Recommended for Multi-instance)**
To use a shared Redis cache across multiple parallel ECS instances (recommended for consistent shared page caching across instances):

1. Set `CACHE_BACKEND="django_redis.cache.RedisCache"`.
2. Set `CACHE_LOCATION="redis://<redis-host>:6379"`.

Replace `<redis-host>` with the hostname or IP address of your own Redis or Valkey instance (for example, `redis://localhost:6379` for a single-instance deployment).

**Note:** Cache durations for dynamic views (homepage, player profiles, etc.) have been reduced to **15 minutes** to ensure content stays fresh.

| Variable | Description | Default |
| :--- | :--- | :--- |
| `CACHE_DB` | Redis database index (Source of truth). | `1` |
| `CACHE_PREFIX` | Key prefix for the cache to avoid collisions. | `aligulac` |
| `REDIS_PASSWORD` | Password for Redis authentication (optional). | `None` |
| `VALKEY_PASSWORD` | Password for Valkey authentication (optional). | `None` |

### **S3/CDN Storage**
The application supports separate buckets for database dumps and static assets. This allows for high-performance delivery via a CDN (CloudFront/Cloudflare).

#### **Database Dumps**
If `S3_BUCKET_DB` is configured, the database dump job (`dump.py`) will upload files to S3.

| Variable | Description | Default |
| :--- | :--- | :--- |
| `S3_BUCKET_DB` | The name of the S3 bucket for database dumps. | `""` (Disabled) |
| `S3_BUCKET` | Legacy variable for `S3_BUCKET_DB` (backwards compatible). | `""` |

#### **Static Assets & CDN**
If `S3_BUCKET_STATIC` is configured, `collectstatic` will upload hashed assets to S3/R2 during the build. These assets can then be served via a CDN.

| Variable | Description | Default |
| :--- | :--- | :--- |
| `S3_BUCKET_STATIC`| The name of the S3/R2 bucket for static assets. | `""` (Use WhiteNoise) |
| `S3_CUSTOM_DOMAIN`| Your CDN domain (e.g. `static.aligulac.com` or `d123.cloudfront.net`). | `None` |
| `S3_REGION` | AWS region for the S3 bucket. | `us-east-1` |
| `S3_ACCESS_KEY` | AWS/R2 Access Key ID. | `None` |
| `S3_SECRET_KEY` | AWS/R2 Secret Access Key. | `None` |
| `S3_ENDPOINT_URL` | Custom S3 endpoint (required for Cloudflare R2). | `None` |
| `S3_DEFAULT_ACL` | S3 ACL (leave empty/unset for Cloudflare R2). | `None` |

**Note:** Environment variables like `S3_DEFAULT_ACL`, `S3_ENDPOINT_URL`, etc., are normalized: values of `None`, `null`, or an empty string are treated as Python `None`.

**Important:** If `S3_BUCKET_STATIC` is **not** set, the application falls back to **WhiteNoise** to serve assets from the local filesystem with automatic cache-busting.

---

## 3. Manual Deployment (Amazon Linux 2023)

### System Setup
1. **Install Dependencies:**
   ```bash
   sudo dnf update -y
   sudo dnf install -y python3.12 python3.12-devel git gcc postgresql15-devel
   ```
2. **Install Pipenv:**
   ```bash
   python3.12 -m pip install --user pipenv
   export PATH=$PATH:$HOME/.local/bin
   ```

### Application Setup
1. **Install Python Packages:**
   ```bash
   pipenv install
   ```
2. **Prepare Logs:**
   ```bash
   sudo mkdir -p /var/log/aligulac
   sudo chown $USER:$USER /var/log/aligulac
   touch /var/log/aligulac/error.log
   ```
3. **Database Sync:**
   ```bash
   pipenv run python aligulac/manage.py migrate --fake-initial
   pipenv run python aligulac/manage.py collectstatic
   ```

---

## 4. Production Best Practices

### **Reverse Proxy (Nginx)**
Always run Aligulac behind a reverse proxy like Nginx to handle SSL (HTTPS) and serve static files efficiently (if not using S3/CDN).

**Example Nginx Snippet:**
```nginx
location /static/ {
    alias /app/static/;
}

location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### **Monitoring Logs**
Logs are written to `/var/log/aligulac/error.log` inside the container.
- **Docker:** `docker logs aligulac-app`
- **File:** `tail -f /var/log/aligulac/error.log`

---

## 5. Troubleshooting Connectivity

If your container cannot reach a database running on the host:

1. **Host Network (Simplest for Local):**
   Run the container with `--network=host`. This allows it to bypass network isolation.
   ```bash
   podman run --network=host --env-file .env aligulac-app:latest
   ```

2. **Internal Bridge (Cleanest for Production):**
   Use `DB_HOST=host.containers.internal` (Podman) or `DB_HOST=host.docker.internal` (Docker). Ensure your DB is listening on the bridge interface and `pg_hba.conf` allows the container's IP range.
