from pathlib import Path

from bgxdesk.services.tool_catalog import categories, category_counts, count, find


def test_catalog_exceeds_requested_size() -> None:
    assert count() >= 600
    assert len(categories()) >= 15
    assert sum(category_counts().values()) == count()


def test_catalog_safe_command_matrix() -> None:
    results = find("graphql")
    assert results
    commands = results[0].safe_commands()
    assert commands["presence"].startswith("command -v ")
    assert "--version" in commands["version"]
    assert "--help" in commands["help"]


def test_catalog_risk_filter() -> None:
    safe = find(risk="safe")
    restricted = find(risk="restricted")
    assert safe and restricted
    assert all(item.risk == "safe" for item in safe)
    assert all(item.risk == "restricted" for item in restricted)


def test_standalone_gui_uses_provided_wallpaper() -> None:
    source = Path("bgxdesk/tool_catalog_gui.py").read_text(encoding="utf-8")
    assert "venom4pro-wide.png" in source
    assert "assets" in source and "wallpapers" in source
