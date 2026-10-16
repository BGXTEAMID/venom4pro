from scripts.venom4pro import build_parser, normalize_target, target_in_scope


def test_cli_exposes_operational_commands() -> None:
    parser = build_parser()
    for command, argv in {
        "health": ["health"],
        "metrics": ["metrics"],
        "integrity": ["integrity"],
        "backup": ["backup", "backup.db"],
        "export": ["export", "project.json"],
        "migrate": ["migrate", "verify"],
        "search": ["search", "header"],
    }.items():
        assert parser.parse_args(argv).command == command


def test_scope_engine_handles_cidr_and_normalization() -> None:
    assert normalize_target("example.com") == "https://example.com"
    record = {"active": True, "rules": [{"value": "192.168.1.0/24", "included": True}]}
    assert target_in_scope(record, "http://192.168.1.25") is True
