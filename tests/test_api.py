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
    assert r.get_json() == {"status": "ok", "countries": 195}


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
    assert len(client.get("/national-days").get_json()) == 195


def test_filter_continent_and_month(client):
    data = client.get("/national-days?continent=Europe&month=10").get_json()
    assert data and all(d["continent"] == "europe" and d["date"][5:7] == "10" for d in data)
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
    assert d["date"].endswith("-07-14")


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
