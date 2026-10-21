"""National Days API - REST API serving the national day of 195 countries."""
import json
from pathlib import Path

from flasgger import Swagger
from flask import Flask, abort, jsonify, redirect, request

DATA_FILE = Path(__file__).parent / "data" / "nationaldays.json"


def load_nationaldays(path=DATA_FILE):
    """Load the dataset once at startup (read-only, kept in memory)."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


app = Flask(__name__)
app.json.sort_keys = False  # keep the field order of the JSON file
app.json.ensure_ascii = False

app.config["SWAGGER"] = {
    "title": "National Days API",
    "uiversion": 3,
    "specs_route": "/apidocs/",
}
Swagger(
    app,
    template={
        "info": {
            "title": "National Days API",
            "description": "National day, capital, currency and key facts for 195 countries.",
            "version": "1.0.0",
        }
    },
)

NATIONALDAYS = load_nationaldays()
BY_ID = {d["id"]: d for d in NATIONALDAYS}
BY_COUNTRY = {d["country"].lower(): d for d in NATIONALDAYS}
BY_ISO = {d["iso"].upper(): d for d in NATIONALDAYS}


def not_found(message):
    return jsonify({"error": message}), 404


@app.get("/")
def index():
    """Redirect the root URL to the Swagger UI."""
    return redirect("/apidocs/")


@app.get("/health")
def health():
    """Health check used by Render.
    ---
    tags: [system]
    responses:
      200:
        description: Service is up
    """
    return jsonify({"status": "ok", "countries": len(NATIONALDAYS)})


@app.get("/national-days")
def list_national_days():
    """List all national days, optionally filtered.
    ---
    tags: [national-days]
    parameters:
      - name: continent
        in: query
        type: string
        required: false
        description: Filter by continent (e.g. europe, asia, africa)
      - name: month
        in: query
        type: integer
        required: false
        description: Filter by month of the national day (1-12)
    responses:
      200:
        description: List of national days
      400:
        description: Invalid month
    """
    result = NATIONALDAYS
    continent = request.args.get("continent")
    if continent:
        result = [d for d in result if d["continent"].lower() == continent.lower()]
    month = request.args.get("month")
    if month is not None:
        if not month.isdigit() or not 1 <= int(month) <= 12:
            return jsonify({"error": "month must be an integer between 1 and 12"}), 400
        result = [d for d in result if int(d["date"][5:7]) == int(month)]
    return jsonify(result)


@app.get("/national-days/id/<int:day_id>")
def get_by_id(day_id):
    """Get a national day by its id.
    ---
    tags: [national-days]
    parameters:
      - name: day_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: National day found
      404:
        description: Unknown id
    """
    national_day = BY_ID.get(day_id)
    return jsonify(national_day) if national_day else not_found("National day not found")


@app.get("/national-days/country/<country_name>")
def get_by_country(country_name):
    """Get a national day by country name (case-insensitive).
    ---
    tags: [national-days]
    parameters:
      - name: country_name
        in: path
        type: string
        required: true
        description: English country name, e.g. france, germany
    responses:
      200:
        description: National day found
      404:
        description: Unknown country
    """
    national_day = BY_COUNTRY.get(country_name.strip().lower())
    return jsonify(national_day) if national_day else not_found("Country not found")


@app.get("/national-days/iso/<iso_code>")
def get_by_iso(iso_code):
    """Get a national day by ISO 3166-1 alpha-3 code.
    ---
    tags: [national-days]
    parameters:
      - name: iso_code
        in: path
        type: string
        required: true
        description: ISO alpha-3 code, e.g. FRA, DEU
    responses:
      200:
        description: National day found
      404:
        description: Unknown ISO code
    """
    national_day = BY_ISO.get(iso_code.strip().upper())
    return jsonify(national_day) if national_day else not_found("ISO code not found")


@app.get("/national-days/description/<keyword>")
def search_by_description(keyword):
    """Search national days by keyword in holiday name or description.
    ---
    tags: [national-days]
    parameters:
      - name: keyword
        in: path
        type: string
        required: true
        description: e.g. independence, revolution, unity
    responses:
      200:
        description: Matching national days (may be several)
      404:
        description: No match
    """
    kw = keyword.strip().lower()
    matches = [d for d in NATIONALDAYS if kw in d["holiday"].lower() or kw in d["description"].lower()]
    return jsonify(matches) if matches else not_found("No national day matches this keyword")


if __name__ == "__main__":
    # Local development only; Render runs the app with gunicorn
    app.run(debug=True)
