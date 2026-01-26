# ranking-go

Mock exam ranking service (Task 145). Shadow/off by default; used for parity comparison with Python baseline.

## API

- `GET /health` — 200 OK
- `POST /rank` — Request: `{ "cohort_id": "...", "items": [{"user_id": "...", "percent": 83.5}] }`  
  Response: `{ "cohort_id": "...", "results": [{"user_id": "...", "rank": 1, "percentile": 100.0}] }`

Deterministic: sort by percent desc, tie-break by user_id.

## Run locally

```bash
go run ./cmd/server
```

## Docker

```bash
docker build -t ranking-go .
docker run -p 8080:8080 ranking-go
```

## Docker Compose

Added as service `ranking-go` in dev compose; **disabled by default** (profile or env). Exposed only to backend network.
