from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from .config import Settings
from .exec_policy import ExecDecision, classify_exec
from .redaction import cap_text, redact_text, redact_value


class KubernetesClient:
    def __init__(
        self,
        settings: Settings,
        *,
        core: Any | None = None,
        apps: Any | None = None,
        batch: Any | None = None,
        custom: Any | None = None,
        networking: Any | None = None,
        storage: Any | None = None,
        api_client: Any | None = None,
        stream_func: Callable[..., Any] | None = None,
    ) -> None:
        self.settings = settings
        if all(api is not None for api in (core, apps, batch, custom, networking, storage)):
            self.core = core
            self.apps = apps
            self.batch = batch
            self.custom = custom
            self.networking = networking
            self.storage = storage
            self.api_client = api_client
            self.stream_func = stream_func
            return

        from kubernetes import client, config
        from kubernetes.stream import stream as kubernetes_stream

        config.load_kube_config(config_file=str(settings.kubeconfig))
        self.api_client = client.ApiClient()
        self.core = client.CoreV1Api(self.api_client)
        self.apps = client.AppsV1Api(self.api_client)
        self.batch = client.BatchV1Api(self.api_client)
        self.custom = client.CustomObjectsApi(self.api_client)
        self.networking = client.NetworkingV1Api(self.api_client)
        self.storage = client.StorageV1Api(self.api_client)
        self.stream_func = kubernetes_stream

    def cluster_overview(self) -> dict[str, Any]:
        nodes = _items(self.core.list_node())
        namespaces = _items(self.core.list_namespace())
        pods = _items(self.core.list_pod_for_all_namespaces())
        deployments = _items(self.apps.list_deployment_for_all_namespaces())
        statefulsets = _items(self.apps.list_stateful_set_for_all_namespaces())
        daemonsets = _items(self.apps.list_daemon_set_for_all_namespaces())
        jobs = _items(self.batch.list_job_for_all_namespaces())

        return redact_value(
            {
                "nodes": {
                    "total": len(nodes),
                    "ready": sum(1 for node in nodes if _has_condition(node, "Ready", "True")),
                    "not_ready": [
                        _metadata_name(node)
                        for node in nodes
                        if not _has_condition(node, "Ready", "True")
                    ],
                },
                "namespaces": sorted(_metadata_name(ns) for ns in namespaces),
                "pods": _pod_counts(pods),
                "workloads": {
                    "deployments": _ready_counts(deployments),
                    "statefulsets": _ready_counts(statefulsets),
                    "daemonsets": _daemonset_counts(daemonsets),
                    "jobs": _job_counts(jobs),
                },
            }
        )

    def flux_status(self) -> dict[str, Any]:
        return redact_value(
            {
                "kustomizations": self._flux_items(
                    "kustomize.toolkit.fluxcd.io", "v1", "kustomizations"
                ),
                "helmreleases": self._flux_items("helm.toolkit.fluxcd.io", "v2", "helmreleases"),
                "sources": {
                    "gitrepositories": self._flux_items(
                        "source.toolkit.fluxcd.io", "v1", "gitrepositories"
                    ),
                    "helmrepositories": self._flux_items(
                        "source.toolkit.fluxcd.io", "v1", "helmrepositories"
                    ),
                    "ocirepositories": self._flux_items(
                        "source.toolkit.fluxcd.io", "v1", "ocirepositories"
                    ),
                },
            }
        )

    def recent_events(
        self,
        namespace: str | None = None,
        involved_kind: str | None = None,
        involved_name: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        max_items = min(limit or self.settings.limits.event_max, self.settings.limits.event_max)
        raw_events = (
            _items(self.core.list_namespaced_event(namespace))
            if namespace
            else _items(self.core.list_event_for_all_namespaces())
        )
        events = []
        for event in raw_events:
            involved = getattr(event, "involved_object", None)
            if involved_kind and getattr(involved, "kind", None) != involved_kind:
                continue
            if involved_name and getattr(involved, "name", None) != involved_name:
                continue
            events.append(_event_summary(event))
        events.sort(key=lambda item: item.get("time") or "", reverse=True)
        return {"events": redact_value(events[:max_items])}

    def workload_status(self, namespace: str | None = None) -> dict[str, Any]:
        return redact_value(
            {
                "deployments": [
                    _deployment_summary(item)
                    for item in _list_by_namespace(
                        namespace,
                        self.apps.list_deployment_for_all_namespaces,
                        self.apps.list_namespaced_deployment,
                    )
                ],
                "statefulsets": [
                    _statefulset_summary(item)
                    for item in _list_by_namespace(
                        namespace,
                        self.apps.list_stateful_set_for_all_namespaces,
                        self.apps.list_namespaced_stateful_set,
                    )
                ],
                "daemonsets": [
                    _daemonset_summary(item)
                    for item in _list_by_namespace(
                        namespace,
                        self.apps.list_daemon_set_for_all_namespaces,
                        self.apps.list_namespaced_daemon_set,
                    )
                ],
                "jobs": [
                    _job_summary(item)
                    for item in _list_by_namespace(
                        namespace,
                        self.batch.list_job_for_all_namespaces,
                        self.batch.list_namespaced_job,
                    )
                ],
                "pods": [
                    _pod_summary_brief(item)
                    for item in _list_by_namespace(
                        namespace,
                        self.core.list_pod_for_all_namespaces,
                        self.core.list_namespaced_pod,
                    )
                ],
            }
        )

    def pod_summary(self, namespace: str, name: str) -> dict[str, Any]:
        pod = self.core.read_namespaced_pod(name=name, namespace=namespace)
        events = self.recent_events(
            namespace=namespace,
            involved_kind="Pod",
            involved_name=name,
            limit=20,
        )["events"]
        return redact_value({"pod": summarize_pod(pod), "events": events})

    def pod_logs(
        self,
        namespace: str,
        name: str,
        container: str | None = None,
        previous: bool = False,
        tail_lines: int | None = None,
    ) -> dict[str, Any]:
        tail = self.settings.limits.clamp_log_tail(tail_lines)
        logs = self.core.read_namespaced_pod_log(
            name=name,
            namespace=namespace,
            container=container,
            previous=previous,
            tail_lines=tail,
            timestamps=True,
            _request_timeout=30,
        )
        redacted = redact_text(str(logs))
        return {
            "namespace": namespace,
            "pod": name,
            "container": container,
            "previous": previous,
            "tail_lines": tail,
            "logs": cap_text(redacted, self.settings.limits.output_max_bytes),
        }

    def pod_exec_plan(self, namespace: str, argv: list[str]) -> dict[str, Any]:
        return classify_exec(namespace, argv, self.settings.exec).to_dict()

    def pod_exec(
        self,
        namespace: str,
        pod: str,
        container: str | None,
        argv: list[str],
        reason: str,
    ) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("pod_exec requires a short reason")
        decision = classify_exec(namespace, argv, self.settings.exec)
        if not decision.allowed:
            return {"decision": decision.to_dict(), "executed": False, "output": ""}
        output = self._exec(namespace, pod, container, decision)
        redacted = cap_text(redact_text(str(output)), self.settings.limits.output_max_bytes)
        audit = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "namespace": namespace,
            "pod": pod,
            "container": container,
            "command": decision.command,
            "risk": decision.risk,
            "reason": reason,
        }
        return {
            "decision": decision.to_dict(),
            "executed": True,
            "audit": redact_value(audit),
            "output": redacted,
        }

    def _exec(
        self,
        namespace: str,
        pod: str,
        container: str | None,
        decision: ExecDecision,
    ) -> str:
        if self.stream_func is None:
            raise RuntimeError("Kubernetes stream support is not configured")
        return self.stream_func(
            self.core.connect_get_namespaced_pod_exec,
            pod,
            namespace,
            container=container,
            command=decision.command,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
            _request_timeout=self.settings.limits.exec_timeout_seconds,
        )

    def _flux_items(self, group: str, version: str, plural: str) -> list[dict[str, Any]]:
        try:
            result = self.custom.list_cluster_custom_object(group, version, plural)
        except Exception as exc:  # noqa: BLE001 - surface API discovery failures as data.
            return [{"kind": plural, "error": str(exc)}]
        return [_custom_status_summary(item, plural) for item in result.get("items", [])]


def summarize_pod(pod: Any) -> dict[str, Any]:
    spec = getattr(pod, "spec", None)
    status = getattr(pod, "status", None)
    metadata = getattr(pod, "metadata", None)
    return {
        "name": getattr(metadata, "name", None),
        "namespace": getattr(metadata, "namespace", None),
        "node": getattr(spec, "node_name", None),
        "phase": getattr(status, "phase", None),
        "conditions": [
            {
                "type": getattr(condition, "type", None),
                "status": getattr(condition, "status", None),
                "reason": getattr(condition, "reason", None),
                "message": getattr(condition, "message", None),
            }
            for condition in getattr(status, "conditions", None) or []
        ],
        "containers": [
            _container_summary(container, _container_status(status, getattr(container, "name", "")))
            for container in getattr(spec, "containers", None) or []
        ],
        "init_containers": [
            _container_summary(container, _container_status(status, getattr(container, "name", "")))
            for container in getattr(spec, "init_containers", None) or []
        ],
        "volumes": [_volume_summary(volume) for volume in getattr(spec, "volumes", None) or []],
        "owner_refs": [
            {"kind": getattr(ref, "kind", None), "name": getattr(ref, "name", None)}
            for ref in getattr(metadata, "owner_references", None) or []
        ],
    }


def _items(value: Any) -> list[Any]:
    return list(getattr(value, "items", value or []))


def _list_by_namespace(
    namespace: str | None,
    list_all: Callable[..., Any],
    list_namespaced: Callable[..., Any],
) -> list[Any]:
    return _items(list_namespaced(namespace)) if namespace else _items(list_all())


def _metadata_name(item: Any) -> str:
    return str(getattr(getattr(item, "metadata", None), "name", ""))


def _metadata_namespace(item: Any) -> str | None:
    return getattr(getattr(item, "metadata", None), "namespace", None)


def _has_condition(item: Any, condition_type: str, status: str) -> bool:
    conditions = getattr(getattr(item, "status", None), "conditions", None) or []
    return any(
        getattr(condition, "type", None) == condition_type
        and getattr(condition, "status", None) == status
        for condition in conditions
    )


def _pod_counts(pods: list[Any]) -> dict[str, Any]:
    phases: dict[str, int] = {}
    restarts = 0
    unready: list[dict[str, Any]] = []
    for pod in pods:
        phase = getattr(getattr(pod, "status", None), "phase", "Unknown")
        phases[phase] = phases.get(phase, 0) + 1
        statuses = getattr(getattr(pod, "status", None), "container_statuses", None) or []
        restarts += sum(getattr(status, "restart_count", 0) or 0 for status in statuses)
        if phase not in {"Running", "Succeeded"} or not _has_condition(pod, "Ready", "True"):
            unready.append(
                {
                    "namespace": _metadata_namespace(pod),
                    "name": _metadata_name(pod),
                    "phase": phase,
                }
            )
    return {"total": len(pods), "phases": phases, "total_restarts": restarts, "unready": unready}


def _ready_counts(items: list[Any]) -> dict[str, Any]:
    unready = []
    for item in items:
        status = getattr(item, "status", None)
        spec = getattr(item, "spec", None)
        desired = getattr(spec, "replicas", 0) or 0
        ready = getattr(status, "ready_replicas", 0) or 0
        if ready < desired:
            unready.append(
                {
                    "namespace": _metadata_namespace(item),
                    "name": _metadata_name(item),
                    "ready": ready,
                    "desired": desired,
                }
            )
    return {"total": len(items), "unready": unready}


def _daemonset_counts(items: list[Any]) -> dict[str, Any]:
    unready = []
    for item in items:
        status = getattr(item, "status", None)
        desired = getattr(status, "desired_number_scheduled", 0) or 0
        ready = getattr(status, "number_ready", 0) or 0
        if ready < desired:
            unready.append(
                {
                    "namespace": _metadata_namespace(item),
                    "name": _metadata_name(item),
                    "ready": ready,
                    "desired": desired,
                }
            )
    return {"total": len(items), "unready": unready}


def _job_counts(items: list[Any]) -> dict[str, Any]:
    active = []
    failed = []
    for item in items:
        status = getattr(item, "status", None)
        summary = {"namespace": _metadata_namespace(item), "name": _metadata_name(item)}
        if getattr(status, "active", 0):
            active.append(summary)
        if getattr(status, "failed", 0):
            failed.append(summary | {"failed": getattr(status, "failed", 0)})
    return {"total": len(items), "active": active, "failed": failed}


def _deployment_summary(item: Any) -> dict[str, Any]:
    status = getattr(item, "status", None)
    spec = getattr(item, "spec", None)
    return {
        "namespace": _metadata_namespace(item),
        "name": _metadata_name(item),
        "ready": getattr(status, "ready_replicas", 0) or 0,
        "desired": getattr(spec, "replicas", 0) or 0,
        "updated": getattr(status, "updated_replicas", 0) or 0,
        "images": _pod_template_images(item),
    }


def _statefulset_summary(item: Any) -> dict[str, Any]:
    status = getattr(item, "status", None)
    spec = getattr(item, "spec", None)
    return {
        "namespace": _metadata_namespace(item),
        "name": _metadata_name(item),
        "ready": getattr(status, "ready_replicas", 0) or 0,
        "desired": getattr(spec, "replicas", 0) or 0,
        "current_revision": getattr(status, "current_revision", None),
        "update_revision": getattr(status, "update_revision", None),
        "images": _pod_template_images(item),
    }


def _daemonset_summary(item: Any) -> dict[str, Any]:
    status = getattr(item, "status", None)
    return {
        "namespace": _metadata_namespace(item),
        "name": _metadata_name(item),
        "ready": getattr(status, "number_ready", 0) or 0,
        "desired": getattr(status, "desired_number_scheduled", 0) or 0,
        "updated": getattr(status, "updated_number_scheduled", 0) or 0,
        "images": _pod_template_images(item),
    }


def _job_summary(item: Any) -> dict[str, Any]:
    status = getattr(item, "status", None)
    return {
        "namespace": _metadata_namespace(item),
        "name": _metadata_name(item),
        "active": getattr(status, "active", 0) or 0,
        "succeeded": getattr(status, "succeeded", 0) or 0,
        "failed": getattr(status, "failed", 0) or 0,
    }


def _pod_summary_brief(item: Any) -> dict[str, Any]:
    status = getattr(item, "status", None)
    statuses = getattr(status, "container_statuses", None) or []
    return {
        "namespace": _metadata_namespace(item),
        "name": _metadata_name(item),
        "phase": getattr(status, "phase", None),
        "ready": _has_condition(item, "Ready", "True"),
        "restarts": sum(getattr(container, "restart_count", 0) or 0 for container in statuses),
        "node": getattr(getattr(item, "spec", None), "node_name", None),
        "owners": [
            {"kind": getattr(ref, "kind", None), "name": getattr(ref, "name", None)}
            for ref in getattr(getattr(item, "metadata", None), "owner_references", None) or []
        ],
    }


def _pod_template_images(item: Any) -> list[str]:
    template = getattr(getattr(item, "spec", None), "template", None)
    pod_spec = getattr(template, "spec", None)
    containers = getattr(pod_spec, "containers", None) or []
    return [getattr(container, "image", "") for container in containers]


def _container_summary(container: Any, status: Any | None) -> dict[str, Any]:
    state = getattr(status, "state", None) if status else None
    last_state = getattr(status, "last_state", None) if status else None
    return {
        "name": getattr(container, "name", None),
        "image": getattr(container, "image", None),
        "ready": getattr(status, "ready", None) if status else None,
        "restart_count": getattr(status, "restart_count", None) if status else None,
        "state": _state_summary(state),
        "last_state": _state_summary(last_state),
        "ports": [
            {
                "name": getattr(port, "name", None),
                "container_port": getattr(port, "container_port", None),
                "protocol": getattr(port, "protocol", None),
            }
            for port in getattr(container, "ports", None) or []
        ],
        "env_refs": _env_refs(container),
        "volume_mounts": [
            {
                "name": getattr(mount, "name", None),
                "mount_path": getattr(mount, "mount_path", None),
                "read_only": getattr(mount, "read_only", None),
            }
            for mount in getattr(container, "volume_mounts", None) or []
        ],
        "probes": {
            "liveness": getattr(container, "liveness_probe", None) is not None,
            "readiness": getattr(container, "readiness_probe", None) is not None,
            "startup": getattr(container, "startup_probe", None) is not None,
        },
    }


def _container_status(status: Any, name: str) -> Any | None:
    if status is None:
        return None
    statuses = (
        list(getattr(status, "container_statuses", None) or [])
        + list(getattr(status, "init_container_statuses", None) or [])
    )
    return next((item for item in statuses if getattr(item, "name", None) == name), None)


def _state_summary(state: Any | None) -> dict[str, Any] | None:
    if state is None:
        return None
    for state_name in ("waiting", "running", "terminated"):
        detail = getattr(state, state_name, None)
        if detail is not None:
            return {
                "state": state_name,
                "reason": getattr(detail, "reason", None),
                "message": getattr(detail, "message", None),
                "exit_code": getattr(detail, "exit_code", None),
            }
    return None


def _env_refs(container: Any) -> dict[str, list[str]]:
    refs = {"config_maps": [], "secrets": [], "field_refs": [], "resource_refs": []}
    for env_from in getattr(container, "env_from", None) or []:
        config_map_ref = getattr(env_from, "config_map_ref", None)
        secret_ref = getattr(env_from, "secret_ref", None)
        if config_map_ref:
            refs["config_maps"].append(getattr(config_map_ref, "name", None))
        if secret_ref:
            refs["secrets"].append(getattr(secret_ref, "name", None))
    for env in getattr(container, "env", None) or []:
        value_from = getattr(env, "value_from", None)
        if not value_from:
            continue
        if getattr(value_from, "config_map_key_ref", None):
            refs["config_maps"].append(getattr(value_from.config_map_key_ref, "name", None))
        if getattr(value_from, "secret_key_ref", None):
            refs["secrets"].append(getattr(value_from.secret_key_ref, "name", None))
        if getattr(value_from, "field_ref", None):
            refs["field_refs"].append(getattr(env, "name", None))
        if getattr(value_from, "resource_field_ref", None):
            refs["resource_refs"].append(getattr(env, "name", None))
    return {key: sorted({item for item in value if item}) for key, value in refs.items()}


def _volume_summary(volume: Any) -> dict[str, Any]:
    volume_type = "unknown"
    ref_name = None
    for attr, label in (
        ("persistent_volume_claim", "persistentVolumeClaim"),
        ("config_map", "configMap"),
        ("secret", "secret"),
        ("nfs", "nfs"),
        ("empty_dir", "emptyDir"),
        ("host_path", "hostPath"),
        ("projected", "projected"),
    ):
        detail = getattr(volume, attr, None)
        if detail is not None:
            volume_type = label
            ref_name = getattr(detail, "claim_name", None) or getattr(detail, "name", None)
            break
    return {"name": getattr(volume, "name", None), "type": volume_type, "ref_name": ref_name}


def _event_summary(event: Any) -> dict[str, Any]:
    involved = getattr(event, "involved_object", None)
    return {
        "time": _event_time(event),
        "namespace": getattr(getattr(event, "metadata", None), "namespace", None),
        "type": getattr(event, "type", None),
        "reason": getattr(event, "reason", None),
        "message": getattr(event, "message", None),
        "count": getattr(event, "count", None),
        "involved": {
            "kind": getattr(involved, "kind", None),
            "name": getattr(involved, "name", None),
            "namespace": getattr(involved, "namespace", None),
        },
    }


def _event_time(event: Any) -> str | None:
    value = (
        getattr(event, "last_timestamp", None)
        or getattr(event, "event_time", None)
        or getattr(getattr(event, "metadata", None), "creation_timestamp", None)
    )
    return value.isoformat() if hasattr(value, "isoformat") else value


def _custom_status_summary(item: dict[str, Any], plural: str) -> dict[str, Any]:
    metadata = item.get("metadata", {})
    status = item.get("status", {})
    ready_condition = _ready_condition(status.get("conditions", []))
    return {
        "kind": item.get("kind") or plural,
        "namespace": metadata.get("namespace"),
        "name": metadata.get("name"),
        "ready": ready_condition.get("status") == "True" if ready_condition else None,
        "reason": ready_condition.get("reason") if ready_condition else None,
        "message": ready_condition.get("message") if ready_condition else None,
        "last_transition_time": ready_condition.get("lastTransitionTime") if ready_condition else None,
    }


def _ready_condition(conditions: list[dict[str, Any]]) -> dict[str, Any]:
    return next((item for item in conditions if item.get("type") == "Ready"), {})
