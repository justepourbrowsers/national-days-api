"""National Days API - REST API serving the national day of 250 countries and territories."""
import json
import unicodedata
from pathlib import Path

from flasgger import Swagger
from flask import Flask, abort, jsonify, redirect, request
from flask_cors import CORS

DATA_FILE = Path(__file__).parent / "data" / "nationaldays.json"


def load_nationaldays(path=DATA_FILE):
    """Load the dataset once at startup (read-only, kept in memory)."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


app = Flask(__name__)
app.json.sort_keys = False  # keep the field order of the JSON file
app.json.ensure_ascii = False
# Allow browsers to call the API from any website (public, read-only data)
CORS(app)

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
            "description": "National day, capital, currency and key facts for 250 countries and territories.",
            "version": "1.1.0",
        }
    },
)

NATIONALDAYS = load_nationaldays()
BY_ID = {d["id"]: d for d in NATIONALDAYS}
# Lookup by current name and by former/alternative names (e.g. turkey -> türkiye)
BY_COUNTRY = {}
for _d in NATIONALDAYS:
    for _name in [_d["country"], *_d["alternative_names"]]:
        BY_COUNTRY[_name.lower()] = _d
BY_ISO = {}
for _d in NATIONALDAYS:
    BY_ISO[_d["iso"].upper()] = _d   # alpha-3, e.g. FRA
    BY_ISO[_d["iso2"].upper()] = _d  # alpha-2, e.g. FR

SORTABLE_FIELDS = ["id", "country", "date", "event_year", "first_celebration", "creation",
                   "population", "area", "capital", "continent", "currency_code"]


def not_found(message):
    return jsonify({"error": message}), 404


def bad_request(message):
    return jsonify({"error": message}), 400


def sort_key(value):
    """Accent- and case-insensitive key for strings (türkiye sorts like turkiye), numbers unchanged."""
    if isinstance(value, str):
        decomposed = unicodedata.normalize("NFKD", value)
        return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()
    return value


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
    """List all national days, with optional filters and sorting.
    ---
    tags: [national-days]
    parameters:
      - name: continent
        in: query
        type: string
        required: false
        description: Filter by continent (africa, america, antarctica, asia, europe, oceania)
      - name: month
        in: query
        type: integer
        required: false
        description: Filter by month of the national day (1-12)
      - name: currency_code
        in: query
        type: string
        required: false
        description: Filter by ISO 4217 currency code, e.g. EUR, USD, XOF
      - name: language
        in: query
        type: string
        required: false
        description: Filter by main language, e.g. french, arabic
      - name: sort
        in: query
        type: string
        required: false
        enum: [id, country, date, event_year, first_celebration, creation, population, area, capital, continent, currency_code]
        description: Field to sort by (BC years are negative, so they sort first)
      - name: order
        in: query
        type: string
        required: false
        enum: [asc, desc]
        default: asc
        description: Sort direction (entries without a value are always listed last)
    responses:
      200:
        description: List of national days
      400:
        description: Invalid parameter
    """
    result = NATIONALDAYS
    for field in ("continent", "language"):
        value = request.args.get(field)
        if value:
            result = [d for d in result if (d[field] or "").lower() == value.strip().lower()]
    currency_code = request.args.get("currency_code")
    if currency_code:
        result = [d for d in result if d["currency_code"] == currency_code.strip().upper()]
    month = request.args.get("month")
    if month is not None:
        if not month.isdigit() or not 1 <= int(month) <= 12:
            return bad_request("month must be an integer between 1 and 12")
        result = [d for d in result if int(d["date"][:2]) == int(month)]

    sort = request.args.get("sort")
    order = request.args.get("order", "asc").lower()
    if order not in ("asc", "desc"):
        return bad_request("order must be asc or desc")
    if sort:
        if sort not in SORTABLE_FIELDS:
            return bad_request(f"sort must be one of: {', '.join(SORTABLE_FIELDS)}")
        with_value = [d for d in result if d[sort] is not None]
        without_value = [d for d in result if d[sort] is None]
        result = sorted(with_value, key=lambda d: sort_key(d[sort]), reverse=order == "desc") + without_value
    elif order == "desc":
        result = list(reversed(result))
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
    """Get a national day by country name (case-insensitive, former names accepted).
    ---
    tags: [national-days]
    parameters:
      - name: country_name
        in: path
        type: string
        required: true
        description: English country name, e.g. france, germany, turkey (-> türkiye)
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
    """Get a national day by ISO 3166-1 code (alpha-3 or alpha-2).
    ---
    tags: [national-days]
    parameters:
      - name: iso_code
        in: path
        type: string
        required: true
        description: ISO code, e.g. FRA or FR, DEU or DE
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
