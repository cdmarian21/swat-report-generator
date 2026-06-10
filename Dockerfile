# syntax=docker/dockerfile:1

# Stage 1: builder = Python dependencies
# Stage 2: runtime = copies only the venv and the source,
# so build tooling/pip cache never reach the shipped image(smaller surface area)

#  Stage 1: builder 
FROM python:3.12-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt

# Stage 2: runtime 
FROM python:3.12-slim-bookworm AS runtime

# cleaning container logs.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Patch OS packages to pull in available security fixes (e.g. openssl, gnutls),
# then create an unprivileged user. Done in one layer; apt lists removed after.
RUN apt-get update && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser
WORKDIR /app

# prebuilt venv/application
COPY --from=builder /opt/venv /opt/venv
COPY src/ ./src/

RUN mkdir -p data output && chown -R appuser:appuser /app
USER appuser

# generate mock data then the report into /app/output.
CMD ["sh", "-c", "python src/generate_mock_data.py --output data/mock_swat.csv && python src/generate_report.py --input data/mock_swat.csv --output output/report.html"]
