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

# Install runtime dependencies (PostgreSQL lib)
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv and app code from builder
COPY --from=builder /app/.venv /app/.venv
COPY . /app/

# Create untracked directory for logs/cache
RUN mkdir -p /app/untracked && \
    touch /app/untracked/error.log && \
    chmod -R 777 /app/untracked

# Set environment variables for the app
ENV PATH="/app/.venv/bin:$PATH"
# Point PYTHONPATH to the folder containing the aligulac package
ENV PYTHONPATH="/app/aligulac"

# Use a non-root user for security
RUN useradd -m aligulac && chown -R aligulac:aligulac /app
USER aligulac

EXPOSE 8000

# Start Gunicorn from the app root
WORKDIR /app/aligulac
CMD ["gunicorn", "aligulac.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
