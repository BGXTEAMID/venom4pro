from bgxdesk.services.policy import FindingPolicy, OperationPolicy, ScopePolicy


def test_scope_cidr_and_public_policy() -> None:
    assert ScopePolicy([{"value": "192.168.1.0/24", "included": True}]).explain("https://192.168.1.10").allowed
    assert not OperationPolicy(allow_public_targets=False).validate_scan("https://example.com", 5, 1, 10000).allowed


def test_transition_matrix_is_explicit() -> None:
    policy = FindingPolicy()
    assert policy.can_transition("draft", "open").allowed
    assert not policy.can_transition("draft", "closed").allowed
