"""Regression tests for the National Days API."""
import pytest

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok", "countries": 250}


def test_root_redirects_to_swagger(client):
    r = client.get("/")
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/apidocs/")


def test_swagger_spec_lists_all_routes(client):
    paths = client.get("/apispec_1.json").get_json()["paths"]
    for p in ["/national-days", "/national-days/id/{day_id}", "/national-days/country/{country_name}",
              "/national-days/iso/{iso_code}", "/national-days/description/{keyword}"]:
        assert p in paths


def test_list_all(client):
    data = client.get("/national-days").get_json()
    assert len(data) == 250
    # 193 UN members + 2 observers (Vatican, Palestine)
    assert sum(d["status"] == "un_member" for d in data) == 193
    assert sum(d["status"] == "un_observer" for d in data) == 2


def test_filter_continent_and_month(client):
    data = client.get("/national-days?continent=Europe&month=10").get_json()
    assert data and all(d["continent"] == "europe" and d["date"][:2] == "10" for d in data)
    assert "germany" in [d["country"] for d in data]


@pytest.mark.parametrize("month", ["0", "13", "abc"])
def test_invalid_month(client, month):
    assert client.get(f"/national-days?month={month}").status_code == 400


def test_by_id(client):
    r = client.get("/national-days/id/1")
    assert r.status_code == 200
    assert r.get_json()["country"] == "afghanistan"


def test_by_country_case_insensitive(client):
    d = client.get("/national-days/country/FRANCE").get_json()
    assert d["iso"] == "FRA"
    assert d["date"] == "07-14"


def test_by_iso(client):
    assert client.get("/national-days/iso/deu").get_json()["country"] == "germany"


def test_description_search_returns_list(client):
    data = client.get("/national-days/description/independence").get_json()
    assert isinstance(data, list) and len(data) > 1


@pytest.mark.parametrize("url", ["/national-days/id/9999", "/national-days/country/atlantis",
                                 "/national-days/iso/XXX", "/national-days/description/zzzz"])
def test_not_found(client, url):
    r = client.get(url)
    assert r.status_code == 404
    assert "error" in r.get_json()


# --- Sorting and filtering ---

def test_sort_by_country_alphabetical(client):
    from app import sort_key
    names = [d["country"] for d in client.get("/national-days?sort=country").get_json()]
    assert names == sorted(names, key=sort_key)
    # accented names sort with their base letter, not after "z"
    assert names.index("türkiye") < names.index("tuvalu")


def test_sort_by_country_desc(client):
    from app import sort_key
    names = [d["country"] for d in client.get("/national-days?sort=country&order=desc").get_json()]
    assert names == sorted(names, key=sort_key, reverse=True)


def test_sort_by_first_celebration_puts_nulls_last(client):
    years = [d["first_celebration"] for d in client.get("/national-days?sort=first_celebration").get_json()]
    known = [y for y in years if y is not None]
    assert known == sorted(known)
    assert all(y is None for y in years[len(known):])


def test_sort_by_event_year_handles_bc(client):
    data = client.get("/national-days?sort=event_year").get_json()
    assert data[0]["country"] == "japan"
    assert data[0]["event_year"] == -660


def test_filter_currency_eur(client):
    data = client.get("/national-days?currency_code=eur&sort=country").get_json()
    names = [d["country"] for d in data]
    assert all(d["currency_code"] == "EUR" for d in data)
    assert {"france", "germany", "croatia", "bulgaria"} <= set(names)


def test_filter_language(client):
    data = client.get("/national-days?language=French").get_json()
    assert data and all(d["language"] == "french" for d in data)


@pytest.mark.parametrize("query", ["sort=unknown", "order=up"])
def test_invalid_sort_params(client, query):
    assert client.get(f"/national-days?{query}").status_code == 400


# --- Lookups by former names and ISO alpha-2 ---

@pytest.mark.parametrize("old,new", [("turkey", "türkiye"), ("swaziland", "eswatini"),
                                     ("czech republic", "czechia"), ("east timor", "timor-leste")])
def test_former_names(client, old, new):
    assert client.get(f"/national-days/country/{old}").get_json()["country"] == new


def test_iso_alpha2(client):
    assert client.get("/national-days/iso/fr").get_json()["iso"] == "FRA"


# --- Data integrity of the JSON file ---

def test_dataset_integrity():
    import re
    from app import NATIONALDAYS as data
    assert len(data) == 250
    for key in ("id", "iso", "iso2", "country"):
        values = [d[key] for d in data]
        assert len(values) == len(set(values)), f"duplicate {key}"
    for d in data:
        assert re.fullmatch(r"(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])", d["date"]), d["country"]
        assert d["event_date"] is None or re.fullmatch(r"-?\d{4}-\d{2}-\d{2}", d["event_date"]), d["country"]
        assert d["area"] > 0, d["country"]
        if d["population"] == 0:
            # Uninhabited entries (Antarctica, Bouvet, ...) may have no currency or founding year
            assert d["currency_code"] is None or re.fullmatch(r"[A-Z]{3}", d["currency_code"]), d["country"]
            assert d["creation"] is None or isinstance(d["creation"], int), d["country"]
        else:
            assert re.fullmatch(r"[A-Z]{3}", d["currency_code"]), d["country"]
            assert isinstance(d["creation"], int) and d["population"] > 0, d["country"]
        if d["event_year"] is not None and d["first_celebration"] is not None:
            assert d["first_celebration"] >= d["event_year"], d["country"]
