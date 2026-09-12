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
Keep Prometheus, Alertmanager, and exporters to observe the degraded cluster;
Prometheus used about 0.2 CPU in the sample. Homepage remains available.

The edits use explicit HelmRelease `postRenderers` to set workload replicas
after Helm renders the existing chart. This makes the temporary state part of
each Helm release, so both Flux and subsequent Helm reconciliation preserve it.
Kured's post-render patch requires `maintenance.home.arpa/reboot-enabled=true`;
no node has that label. Do not add it during this incident.

No app is removed from a Kustomization, no release is uninstalled, and no storage
resource, Secret, or backup configuration is changed. The two affected
StatefulSets use existing PVCs and have `Retain` policies for deletion and scale
down. Grafana's PVC and Pictshare's NFS uploads remain in place. Paused services
are unavailable, but their persisted data is retained.

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
artifacts cached by Flux. Verify that post-rendering changes only the eleven
Deployment/StatefulSet replica fields and Kured's node selector, preserves the
rendered resource inventory, and introduces no upgrade hooks.

After rollout, verify the source revision, all ten HelmRelease conditions, zero
desired replicas for paused workloads, and zero eligible Kured nodes. Compare
PVC names, UIDs, bound PVs, and phases before and after. Recheck media/MMIA
readiness, node CPU requests, and Ceph health.

To restore normal operation after repair, revert the commit titled
`chore(cluster): reduce optional workloads for two-node operation` and push the
revert to `main`. Alternatively, remove only the temporary `postRenderers`
blocks. The original values and all resource declarations remain in place.
Restore application workloads first if needed; re-enable reboot and upgrade
automation only when node and storage health have been verified.

References: [Flux Helm post-renderers](https://fluxcd.io/flux/components/helm/helmreleases/#post-renderers)
and [Kubernetes non-graceful node shutdown](https://kubernetes.io/docs/concepts/cluster-administration/node-shutdown/#non-graceful-node-shutdown).
