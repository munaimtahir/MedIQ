FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Production: Use uvicorn with workers for better concurrency
# Workers formula: (2 * CPU cores) + 1
# For container with 1.5 CPUs: (2 * 1.5) + 1 = 4 workers (rounded)
# Using 5 workers as safe default (can be overridden via env)
ENV UVICORN_WORKERS=${UVICORN_WORKERS:-5}
ENV UVICORN_TIMEOUT_KEEP_ALIVE=${UVICORN_TIMEOUT_KEEP_ALIVE:-5}
ENV UVICORN_LIMIT_CONCURRENCY=${UVICORN_LIMIT_CONCURRENCY:-200}
ENV UVICORN_LIMIT_MAX_REQUESTS=${UVICORN_LIMIT_MAX_REQUESTS:-10000}

CMD uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers ${UVICORN_WORKERS} \
    --timeout-keep-alive ${UVICORN_TIMEOUT_KEEP_ALIVE} \
    --limit-concurrency ${UVICORN_LIMIT_CONCURRENCY} \
    --limit-max-requests ${UVICORN_LIMIT_MAX_REQUESTS}

