# Cluster Orientation

This note captures the current repository shape as of 2026-05-12 and gives us a
shared starting point for a later rebuild/refactor discussion.

## What This Repo Is

This is a Flux-managed k3s homelab GitOps repository derived from an older
`onedr0p/cluster-template` generation. The active cluster manifests are in
`kubernetes/`; most other directories are either operational support, original
bootstrap machinery, or manual test fixtures.

The current committed cluster model is three k3s controller nodes on the
`192.168.1.0/24` network:

- `odroid-01`: `192.168.1.201`
- `odroid-02`: `192.168.1.202`
- `odroid-03`: `192.168.1.203`
- Kubernetes API VIP: `192.168.1.200`

The owner confirmed on 2026-05-12 that this hardware and IP layout is still
accurate.

## GitOps Flow

- `kubernetes/flux/config/cluster.yaml` defines the repo source and the Flux
  `cluster` Kustomization.
- `kubernetes/flux/apps.yaml` defines `cluster-apps`, which reconciles
  `./kubernetes/apps`.
- `cluster-apps` enables SOPS decryption and substitutes values from
  `cluster-settings`, `cluster-secrets`, and optional user override objects.
- Namespaces under `kubernetes/apps/` include root `kustomization.yaml` files
  that list the Flux `ks.yaml` resources for each app.

## Platform Components

- Kubernetes: k3s, currently pinned in Ansible vars to `v1.30.1+k3s1`.
- GitOps: Flux v2, Renovate, GitHub Actions kubeconform and Flux diff checks.
- Networking: Cilium, kube-vip, CoreDNS, ingress-nginx internal/external,
  k8s-gateway, external-dns, cloudflared, and pod-gateway VPN routing.
- Storage: Rook-Ceph, OpenEBS hostpath, MinIO, VolSync/Restic, and Synology/NFS
  for media/backups.
- Observability: kube-prometheus-stack, Alertmanager, Grafana, metrics-server,
  and Hubble.
- Maintenance: system-upgrade-controller, kured, reloader, descheduler,
  node-feature-discovery, Intel GPU device plugins.

## App Inventory

Active app trees currently visible in Git include:

- `cert-manager`: cert-manager and issuers.
- `database`: CloudNativePG manifests exist, but the namespace root currently
  comments out the CloudNativePG `ks.yaml`.
- `default`: homepage, discord-template-notifier, pictshare, open-webui,
  limesurvey, financial-planner.
- `flux-system`: webhooks and Discord notifications.
- `kube-system`: Cilium, metrics-server, reloader, descheduler,
  system-upgrade-controller, node-feature-discovery, Intel GPU plugin, kured,
  kube-vip, CoreDNS.
- `media`: Overseerr, Plex, Prowlarr, Radarr, Sonarr, Transmission.
- `mymindinai`: Discord bot dev/prod environments.
- `network`: cloudflared, echo-server, external-dns, ingress-nginx,
  k8s-gateway, vpn-gateway.
- `observability`: Grafana and kube-prometheus-stack.
- `rook-ceph`: operator and cluster.
- `storage`: OpenEBS, VolSync, snapshot-controller, MinIO.

## Owner Priorities

The owner described the current service priorities this way:

- Critical: everything under the `media` namespace, or a replacement tool with
  equivalent function.
- Critical: `mymindinai` / `mymindinai-dev`, which supports internal business
  tooling.
- Important but replaceable: homepage or equivalent dashboard functionality.
- Keep and update if practical: discord-template-notifier, pictshare,
  open-webui, and limesurvey.
- Disposable: financial-planner is abandoned.
- Supporting platform services are important because the cluster needs them,
  but they are not directly user-facing.

The current network design should stay in place during the rebuild:
Cloudflare tunnel, ingress-nginx internal/external, k8s-gateway, external-dns,
VPN routing, and the flat LAN. The owner has moved to UniFi networking gear and
plans a future server/homelab VLAN migration, but does not want to combine that
with the cluster rebuild unless necessary.

The owner is leaning toward Talos for a future rebuild, but wants to discuss it
after inventory and tradeoffs are clearer.

## State And Backup Inventory

The highest-priority state to preserve is whatever is backed by VolSync/Restic.
Live read-only inventory on 2026-05-12 showed these ReplicationSources:

- `default/open-webui`
- `media/overseerr`
- `media/plex`
- `media/prowlarr`
- `media/radarr`
- `media/sonarr`
- `media/transmission`

Git also shows the same media apps include `kubernetes/templates/volsync`, and
`open-webui` includes `kubernetes/templates/volsync-basic`.

Live PVC inventory showed these notable stateful volumes:

- Media namespace Ceph PVCs: `overseerr`, `plex`, `plex-cache`, `prowlarr`,
  `radarr`, `sonarr`, `transmission`.
- Default namespace Ceph PVCs: `open-webui`, `open-webui-pipelines`,
  `limesurvey-uploads-pvc`, `limesurvey-mariadb-pvc`.
- MMIA NFS PVCs: `mymindinai/mymindinai-images-nfs` and
  `mymindinai-dev/mymindinai-images-nfs`, backed by retained NFS PVs.
- Observability PVCs: Prometheus, Grafana, and Alertmanager use OpenEBS
  hostpath PVCs.

LimeSurvey currently has Ceph-backed upload and MariaDB PVCs but no VolSync
template. The owner would prefer adding backups for LimeSurvey, though it is not
as critical as the media and MMIA workloads.

`open-webui-pipelines` exists as a live PVC and StatefulSet, but there is no
explicit `pipelines` configuration in the current Open WebUI HelmRelease values.
Decide whether that data should be backed up, preserved manually, or treated as
disposable before rebuilding.

MMIA is not purely stateless: the Discord bot deployments mount
`mymindinai-images-nfs` at `/app/images`. The backing PVs point at Synology/NFS
paths under `/volume11/MyMindInAI/images` and `/volume11/MyMindInAI/images-dev`
with `persistentVolumeReclaimPolicy: Retain`.

CloudNativePG appears unused right now: Git contains manifests and the CRD is
installed in the live cluster, but the database namespace root comments out the
CloudNativePG `ks.yaml`, the live cluster has no CNPG Cluster resources, and
there were no pods in the `database` namespace on 2026-05-12.

## Things That Look Worth Reviewing

- The repo has both generated manifests and old `bootstrap/templates/`. We
  should decide whether bootstrap remains maintained or becomes archived
  reference.
- There is Talos bootstrap scaffolding, but the committed inventory is still
  k3s/Ansible-based.
- `kubernetes/flux/config/flux.yaml` and one HelmRepository still use
  `source.toolkit.fluxcd.io/v1beta2`; many `kustomization.yaml` files use the
  normal Kustomize API `kustomize.config.k8s.io/v1beta1`.
- Several HelmRelease schema comments still point at `helmrelease_v2beta2`
  schemas even though the manifests use `helm.toolkit.fluxcd.io/v2`.
- The database namespace has CloudNativePG resources present but not currently
  included from the namespace root.
- Rook-Ceph is configured directly against `/dev/sda` on each Odroid and should
  be treated as a high-risk area.
- Rook-Ceph has been a performance pain point for the owner and may be related
  to regular CPU alerts, but the replacement must preserve easy PVC
  provisioning.
- Renovate has broad automerge rules for many infrastructure categories; that
  may or may not match the desired rebuild posture.
- Renovate can be made more conservative during the rebuild if that reduces
  churn.
- Live HelmRelease inventory on 2026-05-12 showed `kube-system/cilium` not
  ready because chart `cilium@1.16.6` rejected the deprecated
  `containerRuntime.integration` Helm value. The cluster may still be running
  the previously successful Cilium release, but this should be fixed before or
  during modernization.

## Owner Questions

Open questions for the rebuild/refactor discussion:

1. What should replace or simplify Rook-Ceph while preserving convenient PVC
   provisioning?
2. Should Talos be adopted on the existing Odroid-H2 hardware, and what does
   the bootstrap/migration path look like?
3. Should `open-webui-pipelines` be included in backup coverage or intentionally
   treated as disposable?
4. Should LimeSurvey get VolSync backup coverage before any rebuild starts?
5. Should the unused CloudNativePG manifests be archived, removed, or kept as a
   future template?
6. Should old bootstrap/Ansible/Talos scaffolding be preserved, documented as
   historical, or pruned once a new path is chosen?
