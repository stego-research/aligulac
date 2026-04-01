# Stage 1: Builder
FROM python:3.12-slim-bookworm AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIPENV_VENV_IN_PROJECT=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv
RUN pip install --no-cache-dir pipenv

WORKDIR /app

# Install python dependencies
COPY Pipfile Pipfile.lock ./
RUN pipenv install --deploy

# Stage 2: Final Image
FROM python:3.12-slim-bookworm

WORKDIR /app

# Install runtime dependencies (PostgreSQL lib and client tools)
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    ca-certificates \
    gnupg \
    gettext \
    && curl -fSs https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor | tee /etc/apt/trusted.gpg.d/apt.postgresql.org.gpg >/dev/null \
    && echo "deb https://apt.postgresql.org/pub/repos/apt/ bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update && apt-get install -y \
    postgresql-client-18 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv and app code from builder
COPY --from=builder /app/.venv /app/.venv
# Copy the whole project to /app/aligulac
COPY . /app/aligulac/

# Ensure local.py exists even if it was ignored by git
RUN if [ ! -f /app/aligulac/aligulac/aligulac/local.py ]; then \
        cp /app/aligulac/aligulac/aligulac/template.local.py /app/aligulac/aligulac/aligulac/local.py; \
    fi

# Create untracked directory for cache and standard log directory
# This must happen BEFORE collectstatic because Django initializes logging on startup
RUN mkdir -p /app/aligulac/untracked /var/log/aligulac && \
    touch /var/log/aligulac/error.log && \
    chmod -R 777 /app/aligulac/untracked /var/log/aligulac

# Compile translation files
RUN cd /app/aligulac && PYTHONPATH=/app/aligulac/aligulac /app/.venv/bin/python /app/aligulac/aligulac/manage.py compilemessages

# Run collectstatic to gather all assets for whitenoise
RUN SECRET_KEY=build-time-only-key PYTHONPATH=/app/aligulac/aligulac /app/.venv/bin/python /app/aligulac/aligulac/manage.py collectstatic --noinput

# Set environment variables for the app
ENV PATH="/app/.venv/bin:$PATH"
# PYTHONPATH should point to /app/aligulac so 'aligulac.settings' works correctly
ENV PYTHONPATH="/app/aligulac"
ENV PYTHONUNBUFFERED=1

# Use a non-root user for security
RUN useradd -m aligulac && chown -R aligulac:aligulac /app/aligulac
USER aligulac

EXPOSE 8000

# Start Gunicorn from the project root
WORKDIR /app/aligulac
CMD ["gunicorn", "--chdir", "aligulac", "aligulac.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-"]
