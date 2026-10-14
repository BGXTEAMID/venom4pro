from bgxdesk.services.formatting import TerminalFormatter


def test_terminal_formatter_without_color() -> None:
    formatter = TerminalFormatter(color=False, width=60)
    table = formatter.table([{"name": "asset", "status": "completed"}], ["name", "status"])
    assert "asset" in table and "completed" in table
    assert formatter.status("critical") == "CRITICAL"
    assert "hello" in formatter.wrapped("hello world")
    assert formatter.json({"ok": True}).startswith("{")
    assert formatter.jsonl([{"id": 1}, {"id": 2}]).count("\n") == 2
