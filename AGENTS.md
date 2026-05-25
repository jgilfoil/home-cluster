# Agent Instructions

This repository is the GitOps source of truth for a home Kubernetes cluster. The
active cluster state is managed primarily from `kubernetes/` by Flux; historical
bootstrap and provisioning assets live in `bootstrap/` and `ansible/`.

## Default Posture

- Prefer Git changes over live cluster mutation. Flux owns most live resources,
  so direct `kubectl patch`, `helm upgrade`, or manual edits may be reverted.
- Read first, then change narrowly. This repo has several years of accumulated
  patterns and partially retired bootstrap code.
- Treat untracked files and local edits as owner work. Do not overwrite or
  revert them unless explicitly asked.
- Do not decrypt, print, summarize, or exfiltrate SOPS secrets, age keys,
  kubeconfigs, API tokens, Cloudflare credentials, application credentials, or
  Kubernetes Secret values.

## Repository Map

- `kubernetes/`: primary GitOps manifests.
- `kubernetes/flux/`: Flux root configuration, repositories, and cluster-wide
  variables.
- `kubernetes/apps/`: namespace-oriented app tree reconciled by Flux.
- `kubernetes/templates/`: reusable manifest templates, currently mostly
  VolSync helpers.
- `docs/`: operational notes and runbooks.
- `ansible/`: k3s inventory and playbooks for cluster operations.
- `bootstrap/`: Makejinja templates/scripts originally used to generate repo
  content.
- `tests/`: disposable test/smoke manifests for manual cluster checks.
- `.taskfiles/`: Taskfile task modules for Flux, Kubernetes validation, SOPS,
  Ansible, Talos, and workstation setup.

## Kubernetes Layout

Flux starts at `kubernetes/flux/config/cluster.yaml`, which points the `cluster`
Kustomization at `./kubernetes/flux`. The `cluster-apps` Kustomization in
`kubernetes/flux/apps.yaml` reconciles `./kubernetes/apps` with SOPS decryption
and variable substitution from `cluster-settings` and `cluster-secrets`.

The common app pattern is:

```text
kubernetes/apps/<namespace>/<app>/ks.yaml
kubernetes/apps/<namespace>/<app>/app/kustomization.yaml
kubernetes/apps/<namespace>/<app>/app/helmrelease.yaml
```

Some apps intentionally define multiple Flux Kustomizations in one `ks.yaml`,
for example ingress-nginx, cert-manager issuers, VolSync, Rook-Ceph, Intel GPU,
external-dns, and the `mymindinai` Discord bot environments.

When adding or changing an app:

- Add or update the namespace root `kustomization.yaml` so Flux can see the
  `ks.yaml`.
- Keep Helm repositories under `kubernetes/flux/repositories/helm/`.
- Use the existing Flux `Kustomization` and `HelmRelease` style unless there is
  a concrete reason to deviate.
- Use `secret.sops.yaml` or similarly named `*.sops.yaml` files for secrets.
- If changing generated/bootstrapped content, check whether both
  `bootstrap/templates/` and generated files under `kubernetes/` or `ansible/`
  need corresponding updates.

## Safety Boundaries

Do not perform autonomous live mutation of these resources:

- SOPS-encrypted files or Kubernetes Secrets.
- Rook-Ceph resources, OSDs, pools, StorageClasses, PVs, PVCs, VolumeSnapshots,
  or backup/restore resources.
- Nodes, kube-vip, Cilium, cert-manager issuers, Flux root Kustomizations, or
  cluster networking primitives.
- Any destructive cluster operation such as wipes, resets, reboots, disk
  cleanup, or prune-style deletes.

For incident investigation, read status first:

```bash
flux get kustomizations -A
flux get helmreleases -A
kubectl get events -A --sort-by=.lastTimestamp
kubectl logs -n <namespace> <pod> --tail=100
```

Bound log reads with `--tail` unless the owner asks for more.

## Validation

Before proposing Kubernetes manifest changes, inspect available tasks instead
of inventing commands. Known useful commands include:

```bash
task --list
task kubernetes:kubeconform
bash ./scripts/kubeconform.sh ./kubernetes
```

CI currently includes kubeconform validation and Flux diff workflows for pull
requests that touch `kubernetes/**`.

For docs-only changes, at minimum run:

```bash
git diff --check
```

## Current Cluster Notes

- k3s inventory currently lists three Odroid controller nodes:
  `odroid-01`/`192.168.1.201`, `odroid-02`/`192.168.1.202`, and
  `odroid-03`/`192.168.1.203`.
- The Kubernetes API VIP is `192.168.1.200`.
- The current committed k3s version is `v1.30.1+k3s1`.
- Cilium is configured for kube-proxy replacement, native routing, BGP control
  plane enabled, L2 announcements enabled, and Hubble enabled.
- Storage is split between Rook-Ceph for default block storage, OpenEBS
  hostpath, MinIO, Synology/NFS-backed media and backups, and VolSync/Restic.
- Observability includes kube-prometheus-stack, Alertmanager, Grafana, metrics
  server, and Hubble.
- Renovate is active and handles Flux, Helm, Kubernetes, pip, Ansible Galaxy,
  GitHub Actions, and custom regex dependencies.
- Critical owner workloads are the `media` namespace and the `mymindinai` /
  `mymindinai-dev` business tooling. Do not remove or redesign these without an
  explicit migration plan.
- In `default`, `homepage` or equivalent dashboard functionality should be
  preserved. `financial-planner` is abandoned and may be removed during cleanup.
- The current network model must remain stable during rebuild work: Cloudflare
  tunnel, ingress-nginx internal/external, k8s-gateway, external-dns, and the
  current flat LAN should not be migrated at the same time as the cluster
  rebuild.

## Rebuild/Refactor Guidance

For large modernization work, start with inventory and intent before editing:

- What is currently running versus merely present in Git?
- Which services are still important?
- Which workloads have irreplaceable state?
- Which platform choices are intentional and which are inherited?
- What failure domains and recovery goals matter for a homelab-sized cluster?

Prefer small, reviewable migrations that preserve rollback paths. Major changes
to Kubernetes distribution, storage, CNI, ingress, DNS, or secret management
should get an explicit migration plan before manifests are changed.
