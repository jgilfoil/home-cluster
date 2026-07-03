# Current State

Captured: 2026-05-12
Updated: 2026-07-02

## Hardware

The live hardware still matches the committed README and Ansible inventory:

- `odroid-01`: `192.168.1.201`
- `odroid-02`: `192.168.1.202`
- `odroid-03`: `192.168.1.203`
- Kubernetes API VIP: `192.168.1.200`

The cluster is currently k3s-based. The committed k3s version is
`v1.30.1+k3s1`.

A separate disposable Hyper-V Talos lab VM exists for narrow smoke/restore
validation. It is not a full parallel homelab.

## Network Constraints

The current network design must remain stable through the rebuild:

- Cloudflare tunnel
- ingress-nginx internal and external ingress classes
- external-dns
- k8s-gateway
- pod-gateway VPN routing
- current flat LAN

The owner has migrated to UniFi networking gear and has future plans for a
server/homelab VLAN, but does not want to combine that VLAN migration with the
cluster rebuild if avoidable.

## Workload Priority

Critical:

- Everything under `media`, or an equivalent replacement tool.
- `mymindinai` and `mymindinai-dev`, which support internal business tooling for
  the owner's wife.

Important but replaceable:

- `homepage`, or an equivalent dashboard/bookmark/status landing page.

Keep and update if practical:

- `discord-template-notifier`
- `pictshare`
- `open-webui`
- `limesurvey`

Disposable:

- `financial-planner`, which is abandoned.
- `open-webui-pipelines`, which is discard-for-now for v3 planning.

Supporting platform services are important because the cluster needs them, but
they are not directly user-facing in the same way as media and MMIA.

## State Inventory

The highest-priority state to preserve is whatever is protected by
VolSync/Restic.

Live ReplicationSources observed on 2026-05-12:

- `default/open-webui`
- `media/overseerr`
- `media/plex`
- `media/prowlarr`
- `media/radarr`
- `media/sonarr`
- `media/transmission`

Live notable PVCs observed on 2026-05-12:

- `media/overseerr`: Ceph, `1Gi`
- `media/plex`: Ceph, `100Gi`
- `media/plex-cache`: Ceph, `50Gi`
- `media/prowlarr`: Ceph, `1Gi`
- `media/radarr`: Ceph, `1Gi`
- `media/sonarr`: Ceph, `1Gi`
- `media/transmission`: Ceph, `500Mi`
- `default/open-webui`: Ceph, `2Gi`
- `default/open-webui-pipelines`: Ceph, `2Gi`
- `default/limesurvey-uploads-pvc`: Ceph, `500Mi`
- `default/limesurvey-mariadb-pvc`: Ceph, `1Gi`
- `mymindinai/mymindinai-images-nfs`: NFS retained PV, `10Gi`
- `mymindinai-dev/mymindinai-images-nfs`: NFS retained PV, `10Gi`
- `observability/grafana`: OpenEBS hostpath, `10Gi`
- Prometheus and Alertmanager PVCs: OpenEBS hostpath

## State Notes

Plex metadata is the highest-emotional-cost restore target. Losing the Plex
library would be a major pain and should be treated as unacceptable unless every
backup/restore path has failed.

All media apps include the VolSync template in Git. `open-webui` includes the
basic VolSync template. `limesurvey` has Ceph-backed uploads and MariaDB PVCs
but no VolSync coverage yet. LimeSurvey backup coverage is deferred until the
last pre-cutover hardening pass if the app will remain.

`open-webui-pipelines` exists live as a PVC and StatefulSet, but there is no
explicit `pipelines` configuration in the current Open WebUI HelmRelease values.
It is discard-for-now for v3 planning unless the owner later reclassifies it.

MMIA is not purely stateless. The Discord bot deployments mount
`mymindinai-images-nfs` at `/app/images`. The retained NFS PVs point to:

- `/volume11/MyMindInAI/images`
- `/volume11/MyMindInAI/images-dev`

CloudNativePG appears unused right now. The CRD exists in the live cluster, Git
contains manifests, and there is a database doc, but:

- `kubernetes/apps/database/kustomization.yaml` comments out the CloudNativePG
  `ks.yaml`.
- The live cluster has no CNPG Cluster resources.
- There were no pods in the `database` namespace on 2026-05-12.

## Talos Lab Snapshot

Read-only Talos lab verification on 2026-07-02 showed:

- Single-node Hyper-V Talos lab is reachable and Kubernetes node is `Ready`.
- Talos is `v1.13.3`; Kubernetes server is `v1.36.1`.
- `local-path-storage` and `volsync-system` are installed and healthy.
- Rook-Ceph is not installed yet: no `rook-ceph` namespace and no Rook/Ceph CRDs
  were present.
- No PVs/PVCs or VolSync `ReplicationSource`/`ReplicationDestination` resources
  were present at the time of the check.

## Known Current Issues

These were intentionally set aside for the larger roadmap conversation, but they
should not be forgotten:

- `kube-system/cilium` HelmRelease was not ready on 2026-05-12 because chart
  `cilium@1.16.6` rejected the deprecated `containerRuntime.integration` Helm
  value.
- LimeSurvey should probably get backup coverage if it will remain deployed, but
  this is deferred until the last pre-cutover hardening pass.

## Git/Repo Notes

The active GitOps manifests live under `kubernetes/`. Older bootstrap,
Makejinja, Ansible, and Talos scaffolding also exists. For v3, old k3s/Ansible
and Makejinja/bootstrap scaffolding should be archived as historical reference
once Talos-focused replacement docs/runbooks are durable. It should not remain
the maintained v3 build path.
