from home_cluster_mcp.config import ExecSettings
from home_cluster_mcp.exec_policy import classify_exec


SETTINGS = ExecSettings(
    allowed_namespaces=frozenset({"default", "media"}),
    denied_namespaces=frozenset({"kube-system", "database"}),
)


def test_denies_namespace_not_allowed() -> None:
    decision = classify_exec("database", ["ps"], SETTINGS)

    assert not decision.allowed
    assert decision.risk == "denied"


def test_denies_shell_and_env_dump() -> None:
    assert not classify_exec("default", ["sh"], SETTINGS).allowed
    assert not classify_exec("default", ["env"], SETTINGS).allowed


def test_allows_low_risk_diagnostics() -> None:
    decision = classify_exec("default", ["ps", "aux"], SETTINGS)

    assert decision.allowed
    assert decision.risk == "low"


def test_allows_internal_curl_probe() -> None:
    decision = classify_exec("default", ["curl", "-fsS", "http://localhost:8080/health"], SETTINGS)

    assert decision.allowed
    assert decision.risk == "low"


def test_denies_external_curl_probe() -> None:
    decision = classify_exec("default", ["curl", "https://example.com"], SETTINGS)

    assert not decision.allowed


def test_cat_safe_file_is_low_risk_but_secret_path_is_denied() -> None:
    assert classify_exec("default", ["cat", "/etc/resolv.conf"], SETTINGS).risk == "low"
    assert not classify_exec(
        "default", ["cat", "/var/run/secrets/kubernetes.io/serviceaccount/token"], SETTINGS
    ).allowed


def test_unknown_app_command_is_medium_risk() -> None:
    decision = classify_exec("media", ["sonarr", "--version"], SETTINGS)

    assert decision.allowed
    assert decision.risk == "medium"
