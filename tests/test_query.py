from pathlib import Path
from tempfile import TemporaryDirectory

from bgxdesk.services.query import ProjectQuery
from bgxdesk.services.sqlite_store import SQLiteStore


def setup_store() -> SQLiteStore:
    folder = TemporaryDirectory(); store = SQLiteStore(Path(folder.name) / "query.db"); store._test_folder = folder
    store.add_finding({"title": "Header issue", "severity": "low", "summary": "Missing header", "affected_asset": "app.local"})
    store.add_finding({"title": "Auth issue", "severity": "high", "summary": "Authorization review", "affected_asset": "api.local"})
    store.add_asset({"name": "app.local", "asset_type": "domain", "environment": "staging"}, True)
    return store


def test_query_filters_and_pages() -> None:
    store = setup_store(); query = ProjectQuery(store)
    page = query.find_findings("header", page=1, page_size=1)
    assert page.total == 1 and page.pages == 1
    assert query.find_findings(severity="high").items[0]["title"] == "Auth issue"
    assert "staging" in query.environment_values()


def test_search_everything() -> None:
    store = setup_store(); result = ProjectQuery(store).search_everything("app.local")
    assert len(result["assets"]) == 1
