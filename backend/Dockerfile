# The API's image. deploy/deploy.sh builds it (for ARM: the server is a t4g),
# pushes it to ECR, and deploy/server/compose.yml runs it twice: as the API,
# and once per deploy as the migration step (python -m app.migrate).
# The official Python image, from AWS's copy on ECR Public: no Docker Hub pull limits.
FROM public.ecr.aws/docker/library/python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY migrations ./migrations

# Don't run as root inside the container.
RUN useradd --system --uid 10001 --no-create-home app
USER app

EXPOSE 8000
# --proxy-headers: the visitor's IP comes from X-Forwarded-For, which Caddy sets
# (see deploy/server/Caddyfile). Trusting any sender is safe here only because
# nothing but Caddy can reach port 8000: it isn't published outside Docker.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
