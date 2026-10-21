# National Days API

REST API (Flask + Swagger) serving the national day, capital, currency, language and key facts of 195 countries.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/apidocs/` | Swagger UI (`/` redirects here) |
| GET | `/health` | Health check |
| GET | `/national-days` | List all. Filters: `continent`, `month`, `currency_code`, `language`. Sorting: `sort=<field>&order=asc\|desc` |
| GET | `/national-days/id/<id>` | By id |
| GET | `/national-days/country/<name>` | By English country name, former names accepted (turkey → türkiye) |
| GET | `/national-days/iso/<code>` | By ISO 3166-1 alpha-3 or alpha-2 code |
| GET | `/national-days/description/<keyword>` | Keyword search in name/description |

Examples: `/national-days?currency_code=EUR&sort=country`, `/national-days?sort=first_celebration&order=desc`.

## Data notes

- `date` is the day of the year (`MM-DD`); `movable: true` means it follows another calendar or a weekday rule (value given for 2024).
- `event_date` / `event_year` use ISO 8601 years: negative = BC (Japan: `-0660-02-11`).
- `first_celebration` is `null` when unknown; values without a documented source are estimates (event year + 1).
- `vehicle` is the official international vehicle registration code (`null` if the country has none); `iso2` is ISO 3166-1 alpha-2.
- `population` and `area` are approximate (around 2020); `creation` is a loosely defined founding year of the state.

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest                # regression tests
python app.py         # http://127.0.0.1:5000/apidocs/
```

## Deploy

Deployed on Render (free plan) via `render.yaml`. Every push to `main` redeploys automatically.
