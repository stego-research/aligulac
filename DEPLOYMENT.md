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
| `DB_NAME` | Name of the PostgreSQL database. | `aligulac` |
| `DB_USER` | PostgreSQL username. | `postgres` |
| `DB_PASSWORD` | PostgreSQL password. | `postgres` |
| `ALLOWED_HOSTS` | Comma-separated list of domains/IPs (e.g. `aligulac.com,1.2.3.4`). | `*` |

### **Optional Configuration**
| Variable | Description | Default |
| :--- | :--- | :--- |
| `DEBUG` | Enable/Disable Django debug mode (`True`/`False`). | `False` |
| `DEBUG_TOOLBAR`| Enable/Disable the debug toolbar. | `False` |
| `ERROR_LOG_FILE`| Path where application errors are logged. | `/var/log/aligulac/error.log` |
| `CACHE_BACKEND` | Django cache backend. | `DummyCache` |
| `EXCHANGE_ID` | API key for openexchangerates.org. | `""` |

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
Always run Aligulac behind a reverse proxy like Nginx to handle SSL (HTTPS) and serve static files efficiently.

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
