# Temporary two-node operation — September 2026

`odroid-01` stopped reporting on 2026-09-10. The owner reports that it will not
power on. Keep media and MMIA production available while hardware is repaired.
Do not shut down either remaining node for component testing: both Kubernetes
and Ceph currently depend on the two survivors.

## Evidence before the reduction

- `odroid-02` and `odroid-03` are Ready, with four allocatable CPU cores each.
  Active/scheduled pod CPU requests total 3465m and 3390m respectively; completed
  jobs and pods assigned to the failed node are excluded. Requests include the
  larger of each pod's regular-container total and its init-container maximum.
- A CPU usage sample showed 1952m and 785m, with memory at 41% and 60%.
  This is a point-in-time sample, not a peak-load measurement.
- Flux source and Kustomizations are healthy and follow `main` in this repository.
  The source polls every 30 minutes. Helm releases are healthy except for an
  existing Cilium upgrade failure involving removed `containerRuntime.integration`
  configuration. Leave the running CNI alone during this incident.
- `mymindinai/discord-bot` is the production workload and is Ready, with its image
  directory on the existing NFS claim. Development already has zero replicas.
- Plex, Prowlarr, and Transmission are Ready. Sonarr, Radarr, and Overseerr have
  replacement pods scheduled on `odroid-02` but cannot attach their Ceph volumes;
  their old pods are still Terminating on `odroid-01`.
- Ceph has two of three OSDs up and monitor quorum `d,g`. All 33 placement groups
  are active but undersized/degraded. One third of the expected object replicas
  are missing; this is reduced redundancy, not evidence that objects are lost.

## Temporary workload reductions

| Helm release | Change | CPU requests freed on surviving nodes |
| --- | --- | ---: |
| `kube-system/descheduler` | Deployment to zero | 500m |
| `default/limesurvey` | Web Deployment and MariaDB StatefulSet to zero | 300m |
| `default/financial-planner` | Deployment to zero | 50m |
| `network/echo-server` | Deployment to zero | 10m |
| `default/discord-template-notifier` | Deployment to zero | 5m |
| `default/open-webui` | Web StatefulSet and pipelines Deployment to zero | 0m |
| `default/pictshare` | Deployment to zero | 0m |
| `observability/grafana` | Deployment to zero | 0m |
| `observability/kube-prometheus-stack` | Prometheus and Alertmanager to zero, kube-state-metrics to zero, node-exporter requires an absent node label | 0m |
| `kube-system/system-upgrade-controller` | Deployment to zero | 0m |
| `kube-system/kured` | Require an absent node label so no reboot daemon runs | 0m |

Zero CPU requests does not mean zero CPU or memory use. The total reservation
reduction is 865m: from 6855m to 5990m of 8000m, leaving about two cores unreserved.
The expected per-node requests are 2950m on `odroid-02` and 3040m on `odroid-03`,
assuming no other scheduling changes. This does not by itself repair storage
attachments or guarantee sufficient CPU during transcoding peaks.

Keep all media and MMIA production manifests unchanged. Keep Flux, Ceph and CSI,
OpenEBS, MinIO, VolSync, snapshot-controller, DNS, Cilium, ingress, Cloudflare,
VPN routing, certificates, GPU discovery/plugins, and metrics-server running.
Pause Prometheus, Alertmanager, kube-state-metrics, node-exporter, and Grafana
at the owner's request. These workloads have no CPU requests, so the reservation
savings above are unchanged; a later sample measured about 0.3 CPU and 2 GiB of
memory in total actual usage. Metrics collection, alert delivery, and Grafana
will be unavailable. Homepage remains available.

Keep the Prometheus operator running only to reconcile the zero-replica
Prometheus and Alertmanager custom resources. It used 1m CPU and 37 MiB in the
sample. Scaling their StatefulSets directly would let the operator restore them;
stopping the operator in the same rollout could prevent it from scaling them
down at all. It also serves the existing PrometheusRule admission webhooks used
by other Helm releases. Embedded metrics endpoints in essential storage/network
components and the Kubernetes metrics API remain unchanged.

The edits use explicit HelmRelease `postRenderers` to set workload replicas
after Helm renders the existing chart. This makes the temporary state part of
each Helm release, so both Flux and subsequent Helm reconciliation preserve it.
Kured's post-render patch requires `maintenance.home.arpa/reboot-enabled=true`;
no node has that label. Do not add it during this incident.
Node-exporter similarly requires `maintenance.home.arpa/monitoring-enabled=true`,
which no node has. Do not add that label while monitoring is paused.

No app is removed from a Kustomization, no release is uninstalled, and no storage
resource, Secret, or backup configuration is changed. The application
StatefulSets use existing PVCs. All four affected StatefulSets have `Retain`
policies for deletion and scale down, including Prometheus and Alertmanager.
Grafana's PVC and Pictshare's NFS uploads remain in place. Monitoring CRs,
Services, dashboards, rules, and volume claim templates also remain declared.
Paused services are unavailable, but their persisted data is retained. Existing
Prometheus and Alertmanager retention settings resume when they restart; pausing
does not replace the need to export history if it must be kept past retention.

## Remaining storage recovery

There are five stale attachments on `odroid-01`: Sonarr, Radarr, Overseerr,
Open WebUI pipelines, and LimeSurvey MariaDB. Freeing CPU does not release them.

Kubernetes documents an `out-of-service` node taint for recovery after a
non-graceful shutdown. It forcefully removes eligible pods and triggers volume
detach, so it requires verification that the node is physically powered off and
cannot restart during recovery. The repository's node/storage mutation boundary
requires a separate owner-approved recovery operation. Do not force-delete pods,
remove attachment finalizers, or delete PVCs as part of this capacity change.

Plex, Sonarr, Transmission, and Open WebUI backup jobs also depend on local
OpenEBS cache PVCs pinned to `odroid-01`. Those jobs are Pending because the cache
node is unavailable, not because of CPU. Existing backup repositories and cache
claims must be preserved. Restoring backup execution needs a separate plan that
can use new cache claims on surviving storage without deleting the old claims.

## Validation and rollback

Before rollout, run the repository's `scripts/kubeconform.sh`, server-side dry-run
validation of the changed HelmReleases, and rendering of the exact chart
artifacts cached by Flux. Verify that post-rendering changes only the twelve
Deployment/StatefulSet replica fields, the two monitoring CR replica fields,
and Kured/node-exporter node selectors, and preserves the rendered resource
inventory. Review any existing upgrade hooks separately.
The monitoring chart's existing admission hooks create a missing admission
certificate Secret and patch the admission webhooks; these hooks are unchanged.
The local render check uses placeholder values and does not read the release's
Secret-based Alertmanager configuration.

After rollout, verify the source revision, all eleven HelmRelease conditions,
zero desired replicas for paused workloads (including operator-managed
Prometheus/Alertmanager StatefulSets), and zero eligible Kured/node-exporter
nodes. Compare PVC names, UIDs, bound PVs, and phases before and after. Recheck media/MMIA
readiness, node CPU requests, and Ceph health.

To restore normal operation after repair, revert the commits titled
`chore(cluster): pause monitoring during reduced-capacity operation` and
`chore(cluster): reduce optional workloads for two-node operation`, newest first,
and push the reverts to `main`. Alternatively, remove only the temporary
`postRenderers` blocks. The original values and all resource declarations remain in place.
Restore application workloads first if needed; re-enable reboot and upgrade
automation only when node and storage health have been verified.

References: [Flux Helm post-renderers](https://fluxcd.io/flux/components/helm/helmreleases/#post-renderers)
and [Kubernetes non-graceful node shutdown](https://kubernetes.io/docs/concepts/cluster-administration/node-shutdown/#non-graceful-node-shutdown).
Monitoring reconciliation follows the [Prometheus Operator API](https://prometheus-operator.dev/docs/api-reference/api/).
