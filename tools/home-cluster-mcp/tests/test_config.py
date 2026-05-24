from pathlib import Path

from home_cluster_mcp.config import load_settings


def test_load_settings_resolves_paths_and_namespaces(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        """
kubeconfig: .private/codex-mcp/kubeconfig
repo_root: repo
exec:
  allowed_namespaces: [default, media]
  denied_namespaces: [kube-system]
limits:
  log_tail_default: 50
  log_tail_max: 100
  event_max: 25
  exec_timeout_seconds: 5
  output_max_bytes: 4096
prometheus:
  url: http://prometheus.example
  timeout_seconds: 3
""",
        encoding="utf-8",
    )

    settings = load_settings(config)

    assert settings.repo_root == (tmp_path / "repo").resolve()
    assert settings.kubeconfig == (tmp_path / "repo/.private/codex-mcp/kubeconfig").resolve()
    assert settings.exec.is_allowed_namespace("default")
    assert not settings.exec.is_allowed_namespace("kube-system")
    assert settings.limits.clamp_log_tail(200) == 100
    assert settings.prometheus.enabled


def test_invalid_log_limits_fail(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        """
limits:
  log_tail_default: 300
  log_tail_max: 100
""",
        encoding="utf-8",
    )

    try:
        load_settings(config)
    except ValueError as exc:
        assert "log_tail_default" in str(exc)
    else:
        raise AssertionError("expected invalid limits to fail")
