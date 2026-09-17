# Application restoration after node 1 repair — September 2026

Node 1 returned on September 17 after replacement of its failed power brick.
All three Kubernetes nodes are Ready; Ceph has three monitors in quorum, three
OSDs up/in, and all 33 placement groups active and clean. The overdue deep-scrub
warnings cleared during validation; only two September 10 exporter crash records
remain. No degraded or inconsistent PGs were observed during the pre-restoration
check, and enabled application pods are Ready.

## GitOps restoration scope

Remove only the temporary zero-replica Helm post-render patches for:

- `default/discord-template-notifier`
- `default/limesurvey` (web application and its existing MariaDB StatefulSet)
- `default/open-webui` (web StatefulSet and pipelines Deployment)
- `default/pictshare`
- `network/echo-server`

The existing charts, image references, values, persistent claims, and secret
references remain unchanged. These seven workloads return to chart-defined
replica counts through Flux/Helm after the PR is merged. No PVC, PV, Ceph object,
application, release, or Secret is deleted or recreated as part of this change.
Plex and MMIA production are already running and are not modified.

## Intentionally still paused

- `financial-planner`: abandoned application.
- Descheduler: avoid automatically moving healthy workloads during recovery.
- Kured and system-upgrade-controller: no automatic reboots/upgrades immediately
  after a hardware incident.
- Monitoring: retain the separate incident pause for now. Prometheus and
  Alertmanager retain their existing data; resuming them requires considering
  their normal history-retention behavior under the owner's no-data-loss rule.
- MMIA development: already paused before the incident; not part of this restore.
- Four manually suspended VolSync Jobs: not controlled by the replica patches
  changed here. Their node-1-local cache storage is available again, but job
  resumption is a separate backup operation. Existing repositories are retained.

The pre-existing failed Cilium Helm upgrade remains a separate issue; this PR
does not alter the CNI, storage configuration, or control plane.

## Validation and rollback

Validate repository manifests with `scripts/kubeconform.sh`, perform server-side
dry-run validation of the five changed HelmReleases, and render the exact cached
Flux chart artifacts with placeholder values. Compare post-rendered objects to
confirm that only the seven replica fields change and persistent resource
identities/templates remain unchanged. Do not read Secret values to render charts.

Before publication, the full repository schema check and all five server-side
dry runs passed. Cached-chart SHA-256 digests were verified. Rendering confirmed
exactly seven replica changes from 0 to 1, identical resource inventories, and
no Helm hooks. Both existing application StatefulSets have live `Retain` policies
for scale-down and deletion. No Secret values were read or decrypted.

After merge, verify the applied Flux revision, Helm release readiness, restored
workload readiness, PVC identities/bindings, Ceph state, and Plex/MMIA health.
Keep unrelated Renovate/version-upgrade PRs out of this recovery rollout.

Rollback is a Git revert of the restoration commit, reinstating the seven
zero-replica patches without removing their releases or persistent storage.
See [the original reduction](Reduced-Capacity-2026-09.md) for its context.
