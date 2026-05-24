from pathlib import Path
from types import SimpleNamespace as NS

from home_cluster_mcp.config import ExecSettings, Limits, PrometheusSettings, Settings
from home_cluster_mcp.kube import KubernetesClient, _api_client_from_kubeconfig, summarize_pod


def test_summarize_pod_omits_literal_env_values() -> None:
    pod = NS(
        metadata=NS(name="app-123", namespace="default", owner_references=[NS(kind="ReplicaSet", name="app")]),
        spec=NS(
            node_name="node-a",
            containers=[
                NS(
                    name="app",
                    image="example/app:1.0",
                    ports=[NS(name="http", container_port=8080, protocol="TCP")],
                    env=[
                        NS(name="LITERAL_SECRET", value="do-not-return", value_from=None),
                        NS(
                            name="FROM_SECRET",
                            value_from=NS(
                                secret_key_ref=NS(name="app-secret"),
                                config_map_key_ref=None,
                                field_ref=None,
                                resource_field_ref=None,
                            ),
                        ),
                    ],
                    env_from=[],
                    volume_mounts=[NS(name="config", mount_path="/config", read_only=True)],
                    liveness_probe=object(),
                    readiness_probe=None,
                    startup_probe=None,
                )
            ],
            init_containers=[],
            volumes=[NS(name="config", config_map=NS(name="app-config"))],
        ),
        status=NS(
            phase="Running",
            conditions=[NS(type="Ready", status="True", reason=None, message=None)],
            container_statuses=[NS(name="app", ready=True, restart_count=0, state=None, last_state=None)],
            init_container_statuses=[],
        ),
    )

    summary = summarize_pod(pod)

    assert "do-not-return" not in repr(summary)
    assert summary["containers"][0]["env_refs"]["secrets"] == ["app-secret"]


def test_pod_exec_denied_before_streaming() -> None:
    settings = Settings(
        kubeconfig=Path("/tmp/kubeconfig"),
        repo_root=Path("/tmp/repo"),
        exec=ExecSettings(allowed_namespaces=frozenset({"default"}), denied_namespaces=frozenset({"database"})),
        limits=Limits(),
        prometheus=PrometheusSettings(),
    )

    client = KubernetesClient(
        settings,
        core=object(),
        apps=object(),
        batch=object(),
        custom=object(),
        networking=object(),
        storage=object(),
        stream_func=lambda *args, **kwargs: "should-not-run",
    )
    result = client.pod_exec("database", "postgres-0", None, ["ps"], "test")

    assert result["executed"] is False
    assert result["decision"]["risk"] == "denied"


def test_api_client_maps_authorization_to_bearer_token() -> None:
    class FakeConfiguration:
        def __init__(self) -> None:
            self.api_key = {"authorization": "Bearer token"}

        @classmethod
        def get_default_copy(cls) -> "FakeConfiguration":
            return cls()

    class FakeClientModule:
        Configuration = FakeConfiguration

        class ApiClient:
            def __init__(self, configuration: FakeConfiguration) -> None:
                self.configuration = configuration

    class FakeConfigModule:
        loaded_config_file = None

        @classmethod
        def load_kube_config(cls, config_file: str) -> None:
            cls.loaded_config_file = config_file

    api_client = _api_client_from_kubeconfig(
        FakeClientModule,
        FakeConfigModule,
        "/tmp/kubeconfig",
    )

    assert FakeConfigModule.loaded_config_file == "/tmp/kubeconfig"
    assert api_client.configuration.api_key["BearerToken"] == "Bearer token"
