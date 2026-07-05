# Pre-Cutover Safety Checklist

Captured: 2026-07-05

This checklist is the safety gate before any destructive same-hardware Talos
rebuild action, especially formatting the existing k3s nodes. It is not the
cutover runbook itself. Its job is to prove that the cutover runbook is ready to
be executed and that the practical rollback story is understood.

## Scope

In scope:

- Backup/export confidence before the old cluster is changed.
- Restore acceptance criteria for critical workloads.
- Backup endpoint survival if the old cluster is offline.
- Real-node storage and Talos bootstrap readiness.
- The explicit point-of-no-return gate before formatting real nodes.

Out of scope for the initial cutover:

- VLAN migration.
- Gateway API / Envoy Gateway migration.
- Secret-management migration away from SOPS-age.
- Storage replacement unless Rook-Ceph hits a concrete blocker.
- Full GitOps clone of the Hyper-V Talos lab.

## Safety Model

Assume there may be no practical same-hardware rollback once real node disks are
formatted. The safety model is therefore:

1. make the target branch and cutover runbook reviewable,
2. freeze avoidable drift,
3. preserve final backups and inventory exports,
4. prove that backup objects and the backup API endpoint survive the old cluster
   going down,
5. define acceptance criteria before cutover starts,
6. keep old backup history untouched until acceptance criteria are met.

Do not format any real node until every `MUST PASS` item below is complete and
Jason explicitly approves the point-of-no-return gate.

## Status Legend

Use these markers while preparing for cutover:

- `[ ]` not started
- `[~]` in progress / partially known
- `[x]` complete
- `[!]` blocked / unsafe
- `[N/A]` intentionally not applicable

## 1. Decision And Freeze Gate

MUST PASS:

- `[ ]` Jason confirms the cutover target: same Odroid nodes, Talos target, and
  no parallel hardware assumption.
- `[ ]` Jason confirms the acceptable outage window for this attempt.
- `[ ]` The rebuild is staged from the agreed branch strategy: `main` as durable
  truth, short-lived PR branches for prep, and a long-lived rebuild branch only
  if unreconciled Talos/GitOps implementation changes need to accumulate before
  cutover.
- `[ ]` The exact cutover branch, commit, or tag is recorded.
- `[ ]` Renovate is placed into rebuild-safe mode for platform/storage/network
  components, or Jason explicitly accepts the churn risk.
- `[ ]` Nonessential changes are frozen for critical apps and platform
  components.
- `[ ]` The final cutover runbook exists and includes an ordered command log.

Abort if:

- The target branch is unclear.
- The owner cannot review the runbook before the outage.
- Renovate or app churn is still changing storage, networking, or Flux behavior
  during the cutover window.

## 2. Repo And GitOps Readiness

MUST PASS:

- `[ ]` `main` contains the accepted planning docs and latest safety checklist.
- `[ ]` Any real Talos/GitOps implementation changes are in a reviewed PR or an
  explicitly named rebuild staging branch.
- `[ ]` Local rendered manifests validate with the repository's chosen
  validation commands.
- `[ ]` Flux bootstrap source, branch, and path for the rebuilt cluster are
  explicit.
- `[ ]` SOPS-age usage stays unchanged unless a separate reviewed migration is
  approved.
- `[ ]` Old k3s/Ansible/bootstrap scaffolding is either archived or clearly
  labeled historical so it cannot be mistaken for the v3 path.
- `[ ]` GitHub access, repo access, and a local copy of the runbook are available
  even if the old cluster is offline.

Suggested repo-only validation:

```bash
cd /home/wadsworth/projects/github.com/jgilfoil/home-cluster

git fetch --prune origin
git status --short --branch
task --list
task kubernetes:kubeconform
# or, if that task is unavailable:
bash ./scripts/kubeconform.sh ./kubernetes
git diff --check
```

Do not invent validation commands if repository tasks change; inspect `task
--list` first.

## 3. Live Inventory Export Gate

This section requires explicit live-cluster approval at the time it is run. Do
not run these commands as part of docs work.

MUST PASS:

- `[ ]` Current nodes, versions, taints, labels, and storage-relevant hardware
  notes are exported.
- `[ ]` Current Flux Kustomization and HelmRelease status is exported.
- `[ ]` PVC, PV, VolumeSnapshot, VolSync `ReplicationSource`, and
  `ReplicationDestination` inventories are exported.
- `[ ]` Critical app deployment/statefulset status is exported.
- `[ ]` Network-critical resources are inventoried: Cilium, kube-vip,
  ingress-nginx, external-dns, k8s-gateway, cloudflared, cert-manager.
- `[ ]` The export location is outside the cluster being rebuilt.
- `[ ]` No Secret values, kubeconfigs, SOPS material, tokens, or application
  credentials are printed into the export.

Read-only command shape, to be run only with explicit approval:

```bash
# Set an explicit kubeconfig first; do not rely on ambient shell state.
export KUBECONFIG=/path/to/approved/kubeconfig
export OUT="/path/outside/cluster/cutover-inventory-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT"

flux get kustomizations -A > "$OUT/flux-kustomizations.txt"
flux get helmreleases -A > "$OUT/flux-helmreleases.txt"
kubectl get nodes -o wide > "$OUT/nodes-wide.txt"
kubectl get pods -A -o wide > "$OUT/pods-wide.txt"
kubectl get pvc -A -o wide > "$OUT/pvc-wide.txt"
kubectl get pv -o wide > "$OUT/pv-wide.txt"
kubectl get volumesnapshots.snapshot.storage.k8s.io -A -o wide \
  > "$OUT/volumesnapshots-wide.txt"
kubectl get replicationsources.volsync.backube -A -o wide \
  > "$OUT/volsync-replicationsources.txt"
kubectl get replicationdestinations.volsync.backube -A -o wide \
  > "$OUT/volsync-replicationdestinations.txt"
kubectl get events -A --sort-by=.lastTimestamp > "$OUT/events.txt"
```

Do not export `Secret` objects or decrypted SOPS values.

## 4. Backup And Restore Confidence Gate

MUST PASS:

- `[ ]` Each critical VolSync-backed workload has a recent successful backup
  recorded by status, not by Secret inspection.
- `[ ]` Plex restore confidence is recorded. The existing alternate-PVC restore
  drill has already validated expected restored files; do not repeat it unless a
  new risk appears.
- `[ ]` Media apps with small Ceph PVCs have either recent backup status or a
  deliberate reason why Plex restore coverage is sufficient for this cutover.
- `[ ]` MMIA production image storage is accounted for. The NFS-backed retained
  PV path must be reachable or otherwise protected before cutover.
- `[ ]` LimeSurvey is either explicitly retired/deferred or has final pre-cutover
  backup coverage for both uploads and MariaDB state.
- `[ ]` `open-webui-pipelines` remains discard-for-now unless Jason reclassifies
  it.
- `[ ]` Old backup history will remain untouched until acceptance criteria are
  met after the rebuild.

Hard guardrails:

- Do not replace live PVCs during a drill.
- Do not create a `ReplicationSource` for scratch restore PVCs.
- Do not run restic `prune`, `forget`, `unlock`, or retention-changing commands
  as part of the cutover gate.
- Do not print media filenames, Secret values, restic environment values, or
  SOPS content into notes.

## 5. Backup Endpoint Survival Gate

This is the main remaining storage/restore risk after the Talos Rook-Ceph/RBD
smoke test.

MUST PASS:

- `[ ]` The team knows whether VolSync/restic currently targets a
  cluster-internal service DNS name, a LAN-reachable MinIO/S3 URL, or another
  endpoint.
- `[ ]` If the endpoint is cluster-hosted MinIO/S3, the cutover plan explains how
  restore access works while the old cluster is offline.
- `[ ]` If MinIO stores objects on Synology/NFS, the object data and the S3 API
  front door are treated as separate dependencies.
- `[ ]` A restore-capable S3 endpoint is reachable from the Talos target or from
  the restore execution environment before old nodes are formatted.
- `[ ]` The acceptance path does not require decrypting or printing SOPS/Secret
  values in runbooks.

Acceptable endpoint-survival answers include:

- The production restic endpoint is already LAN-reachable independently of the
  old cluster.
- A temporary external MinIO/S3 front door is stood up against copied/exported
  repository data.
- The cutover starts with a mechanics-only restore against a copied repository,
  and production restore waits until the target cluster's S3 front door is up.

Abort if:

- Backup objects exist but the only S3 API endpoint disappears with the old
  cluster and no substitute endpoint is prepared.
- The plan depends on changing restic retention or pruning old repositories.

## 6. Real-Node Storage Gate

MUST PASS:

- `[ ]` Every real node has a disk inventory with stable identifiers recorded:
  model, serial, size, by-id path where available, and intended role.
- `[ ]` The Talos install disk is explicitly identified per node.
- `[ ]` The Rook-Ceph OSD candidate disks are explicitly identified per node.
- `[ ]` The plan avoids `useAllDevices` unless Jason approves it after reviewing
  the real disk inventory.
- `[ ]` Any disks to wipe are listed by stable identifier, not only by
  `/dev/sdX`-style names.
- `[ ]` The expected Rook-Ceph topology is clear for three real nodes.
- `[ ]` The known Talos-lab limitation is understood: the loop-backed single-node
  RBD test proves mechanics, not real-disk parity, quorum behavior, or
  performance.

Abort if:

- The install disk or OSD disks are ambiguous.
- Any disk may contain data that has not been deliberately backed up or
  declared disposable.
- The runbook could accidentally wipe Synology/NFS/media data or the wrong local
  disk.

## 7. Talos Bootstrap Gate

MUST PASS:

- `[ ]` Talos version and Kubernetes version are chosen and recorded.
- `[ ]` Node IPs, API VIP, gateway, DNS, and hostnames are chosen and recorded.
- `[ ]` Talos machine configs are generated and validated before application to
  real nodes.
- `[ ]` Cilium mode and kube-proxy replacement posture are explicit.
- `[ ]` Bootstrap order is documented: first control plane, remaining control
  planes, kubeconfig export, Cilium, core controllers, Flux.
- `[ ]` Kubeconfig and Talosconfig handling avoids printing credentials into
  notes or chat.
- `[ ]` The Hyper-V Talos lab is used only for concrete remaining questions, not
  as an assumed full rehearsal.

Suggested pre-apply validation shape:

```bash
talosctl validate --mode metal --strict --config <generated-controlplane.yaml>
```

Do not apply Talos configs to real nodes until the point-of-no-return gate is
approved.

## 8. Network And Ingress Gate

MUST PASS:

- `[ ]` Current flat LAN model remains in place for cutover.
- `[ ]` VLAN migration remains explicitly deferred.
- `[ ]` Gateway API / Envoy Gateway migration remains explicitly deferred.
- `[ ]` VIP/LB behavior is documented for the Talos control plane and any service
  load balancer path.
- `[ ]` Internal and external ingress-nginx paths are preserved or replaced by an
  explicitly reviewed equivalent.
- `[ ]` Cloudflare tunnel behavior is documented.
- `[ ]` k8s-gateway and external-dns behavior is documented.
- `[ ]` cert-manager issuer/certificate behavior is documented.
- `[ ]` A post-restore DNS/ingress smoke-test list exists.

Minimum smoke-test targets after rebuild:

- Kubernetes API VIP reachable.
- Internal dashboard/homepage route reachable.
- External Cloudflare-tunneled service reachable.
- k8s-gateway local DNS resolves expected records.
- cert-manager issues or reuses expected certificates without manual secret
  exposure.

## 9. Workload Restore And Acceptance Gate

MUST PASS:

- `[ ]` Restore order is documented.
- `[ ]` Acceptance criteria are written before the outage starts.
- `[ ]` Each critical app has a minimum viable verification step.
- `[ ]` Noncritical/disposable apps are explicitly allowed to wait.

Recommended restore order:

1. Talos control plane and kubeconfig access.
2. Cilium and core networking.
3. Flux and repositories.
4. Storage: Rook-Ceph, StorageClasses, VolumeSnapshot components, VolSync.
5. Media namespace PVC restores and workloads.
6. Plex metadata verification.
7. MMIA production, including `/app/images` NFS access.
8. Default dashboard/homepage equivalent.
9. Observability and maintenance automation.
10. Deferred apps and cleanup.

Minimum rebuilt-cluster acceptance criteria:

- `[ ]` Flux Kustomizations and HelmReleases are green, or exceptions are listed
  and accepted.
- `[ ]` Rook-Ceph is healthy enough for intended workloads.
- `[ ]` VolSync backups run after restore.
- `[ ]` Plex library and metadata are intact.
- `[ ]` Core media workflows work end to end.
- `[ ]` MMIA production bot runs and can access `/app/images`.
- `[ ]` Homepage or equivalent dashboard exists.
- `[ ]` Internal and external ingress paths work.
- `[ ]` Cloudflare tunnel works.
- `[ ]` Local DNS through k8s-gateway works.
- `[ ]` Renovate is active but rebuild-safe until Jason re-enables normal
  automerge.

## 10. Point-Of-No-Return Gate

This is the final human checkpoint before formatting real nodes.

MUST PASS immediately before destructive action:

- `[ ]` Jason explicitly approves proceeding past the point of no return.
- `[ ]` The exact nodes and disks to format are named.
- `[ ]` Final backup status is captured.
- `[ ]` Final inventory export is captured and stored outside the cluster.
- `[ ]` Backup endpoint survival is proven or a substitute endpoint is ready.
- `[ ]` Target Talos/GitOps branch and commit are recorded.
- `[ ]` The runbook is open locally and accessible if the old cluster is down.
- `[ ]` Required credentials are available to Jason without being pasted into
  chat, docs, tickets, or logs.
- `[ ]` Abort conditions are understood and accepted.

Abort if any of these are true:

- Disk identity is ambiguous.
- Backup or restore status is unknown for critical state.
- The only backup endpoint would disappear with the old cluster.
- Talos configs are unvalidated.
- The runbook requires an unreviewed live mutation.
- Jason is not available to make point-of-no-return decisions.

After this gate is crossed, do not assume same-hardware rollback. If the rebuild
fails, the recovery path is to continue restoring into the target environment or
into a deliberately prepared alternate, using preserved backups and exports.

## 11. Post-Cutover Hold

MUST PASS before declaring the rebuild complete:

- `[ ]` Old backup history is still intact.
- `[ ]` New backups have succeeded for restored critical apps.
- `[ ]` Acceptance criteria are checked off.
- `[ ]` Known exceptions are documented.
- `[ ]` Renovate normal automerge is not re-enabled until the rebuilt cluster is
  stable.
- `[ ]` Any temporary credentials, scratch manifests, or emergency access paths
  are cleaned up or intentionally retained with documented scope.
- `[ ]` The cutover runbook is updated with actual commands, timing, failures,
  and fixes.

## Evidence Log Template

Use this template in the final cutover runbook or issue. Keep secrets out.

```text
Cutover branch/commit:
Approved outage window:
Point-of-no-return approval time:
Final inventory export path:
Final backup status evidence path:
Backup endpoint survival evidence:
Talos config validation evidence:
Real-node disk inventory evidence:
Acceptance criteria evidence:
Known exceptions:
Post-cutover backup evidence:
```
