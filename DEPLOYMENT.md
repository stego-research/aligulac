# Aligulac Deployment Guide (Amazon Linux)

This guide outlines how to deploy Aligulac on a clean Amazon Linux 2023 instance using Python 3.12 and Gunicorn.

## 1. System Requirements
- Amazon Linux 2023 (AL2023)
- PostgreSQL (Local or RDS)
- 2GB+ RAM (Recommended for building `numpy`/`scipy`)

## 2. Automated Setup
Upload and run the provided `setup_amazon_linux.sh`:
```bash
chmod +x setup_amazon_linux.sh
./setup_amazon_linux.sh
source ~/.bashrc
```

## 3. Configuration
Copy the template configuration if you haven't already:
```bash
cp aligulac/aligulac/template.local.py aligulac/aligulac/local.py
```
**Important:** Edit `aligulac/aligulac/local.py` and set:
- `DEBUG = False`
- `ALLOWED_HOSTS = ['your-domain.com']`
- `DB_USER`, `DB_PASSWORD`, etc.

## 4. Database & Static Files
```bash
pipenv run python aligulac/manage.py migrate
pipenv run python aligulac/manage.py collectstatic
```

## 5. Running in Production
We use **Gunicorn** managed by **systemd** to ensure the server stays online.

### Create Systemd Service
Create a file at `/etc/systemd/system/aligulac.service`:
```ini
[Unit]
Description=Gunicorn instance to serve Aligulac
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/aligulac
Environment="PATH=/home/ec2-user/aligulac/.venv/bin"
ExecStart=/home/ec2-user/aligulac/.venv/bin/gunicorn \
    --chdir aligulac \
    --workers 3 \
    --bind 0.0.0.0:8000 \
    aligulac.wsgi:application

[Install]
WantedBy=multi-user.target
```

### Start the Service
```bash
sudo systemctl start aligulac
sudo systemctl enable aligulac
```

## 6. Nginx Reverse Proxy (Optional but Recommended)
Install Nginx to handle SSL and serve static files directly:
```bash
sudo dnf install -y nginx
```
Configure Nginx to proxy requests to `127.0.0.1:8000`.
