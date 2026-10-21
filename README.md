# National Days API

REST API (Flask + Swagger) serving the national day, capital, currency, language and key facts of 195 countries.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/apidocs/` | Swagger UI (`/` redirects here) |
| GET | `/health` | Health check |
| GET | `/national-days?continent=europe&month=10` | List all, optional filters |
| GET | `/national-days/id/<id>` | By id |
| GET | `/national-days/country/<name>` | By English country name (case-insensitive) |
| GET | `/national-days/iso/<code>` | By ISO 3166-1 alpha-3 code |
| GET | `/national-days/description/<keyword>` | Keyword search in name/description |

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest                # regression tests
python app.py         # http://127.0.0.1:5000/apidocs/
```

## Deploy

Deployed on Render (free plan) via `render.yaml`. Every push to `main` redeploys automatically.
