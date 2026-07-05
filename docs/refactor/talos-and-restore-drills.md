# Talos And Restore Drills

Captured: 2026-05-25
Updated: 2026-07-05

This note refines the earlier rehearsal recommendation. Full spare hardware is
not currently available, and a complete production-like rehearsal cluster would
add a lot of setup complexity. A narrower Hyper-V Talos VM now exists and should
be kept during the rebuild while remaining focused on specific migration-risk
questions rather than becoming a parallel homelab.

## Current Talos Lab Status

Rook-Ceph/RBD smoke testing on 2026-07-04 showed:

- Single-node Hyper-V Talos lab ran Rook `v1.20.1` and Ceph `v20.2.1` /
  Tentacle after the VM was resized to 12 GiB RAM and 4 vCPU.
- One explicitly targeted loop-backed OSD was used; this is not real-disk
  parity.
- `CephCluster/rook-ceph` reached `Ready` with `HEALTH_OK`.
- `CephBlockPool/ceph-blockpool` reached `Ready` with replication size `1`.
- Ceph reported one mon, one mgr, and one OSD `up`/`in` with all PGs
  `active+clean`.
- RBD CSI provisioned a scratch `ceph-block` PVC.
- A writer job wrote a marker and checksum, the PVC detached, a reader job
  reattached it, and `sha256sum -c` verified the data.
- Scratch test namespaces were deleted after the smoke tests.

## Downtime Framing

Downtime should be treated as a sliding tradeoff:

- Zero downtime is preferred, but not at unlimited cost or complexity.
- A few hours of downtime is worth spending some preparation effort to reach.
- A few days of downtime should be avoided if there is a practical lower-risk
  path.
- Near-zero downtime likely requires parallel hardware or major architecture
  changes and should not be assumed for the same-hardware rebuild.

The working target is a planned maintenance window that can fit into hours if
the restore path and bootstrap sequence are well understood.

## Talos VM Scope

The Hyper-V Talos VM is useful as a focused spike and should be kept for now,
but it should not start as a full GitOps clone of the homelab.

Useful questions for a VM:

- Can a single-node Talos cluster be brought up without excessive friction?
- Can CNI, basic storage, VolSync/restic, and Rook-Ceph be installed and
  reinstalled cleanly enough on Talos to support the first rebuild path?
- Can the VM reach the backup endpoint that VolSync uses?
- Can a small restic backup be restored into a scratch PVC if a new risk calls
  for that check?

Questions a VM probably will not answer well:

- Real Odroid disk layout and device naming.
- Three-node Rook-Ceph behavior.
- Intel GPU behavior for Plex.
- Real ingress, DNS, Cloudflare tunnel, and LAN routing behavior.
- Full production cutover timing.

The VM should remain replaceable. It is useful enough to retain during the
rebuild, but the artifact worth preserving is the runbook and any repo changes
needed for the future real cluster, not irreplaceable VM state.

## Talos Rook-Ceph Lab Findings

Captured: 2026-07-04

After the Hyper-V Talos VM was resized to 12 GiB RAM and 4 vCPU, the disposable
single-node Talos lab successfully ran a basic Rook-Ceph/RBD smoke test. The lab
used Rook `v1.20.1`, Ceph `v20.2.1` / Tentacle, one explicitly targeted
loop-backed OSD, the `ceph-block` StorageClass, and the RBD CSI driver.

Final validated state:

- `CephCluster/rook-ceph` reached `Ready` with `HEALTH_OK`.
- `CephBlockPool/ceph-blockpool` reached `Ready` with replication size `1`.
- Ceph reported one mon, one mgr, and one OSD `up`/`in` with all PGs
  `active+clean`.
- RBD CSI controller and node plugin were both ready.
- A scratch `ceph-block` PVC was provisioned, mounted by a writer job, detached,
  reattached by a reader job, and verified with `sha256sum -c`.
- Scratch namespaces and workloads were deleted after the smoke tests.

What this proves:

- Talos can run the Rook-Ceph control plane and a minimal RBD data path in the
  lab VM when given enough CPU/memory.
- Rook-Ceph remains viable for the first Talos rebuild unless real-node testing
  exposes a concrete blocker.
- Rook `v1.20.x` with the Ceph CSI operator path can provision RBD PVCs when the
  CSI driver chart/resources are installed.

What this does not prove:

- Three-node Rook-Ceph quorum, failure-domain, or recovery behavior.
- Real Odroid disk layout, device naming, SMART/firmware behavior, or wipe
  safety.
- Production Ceph performance or capacity.
- VolSync restore behavior through Rook on Talos.
- Backup endpoint survival if the old cluster-hosted S3/MinIO front door is
  unavailable.
- Full GitOps bootstrap of the future cluster.

Lab runbook notes to preserve:

- Keep the Talos lab replaceable and use ignored `.private/` artifacts for
  kubeconfig, Talos config, Helm values, and scratch manifests.
- Do not use `useAllDevices` against the VM. Target only the intended lab device.
- The loop-backed OSD target was `/dev/loop1`; it did not survive a VM reboot and
  had to be recreated before rerunning OSD prepare. Treat this as a lab-only
  workaround, not real-disk parity.
- If an OSD prepare job ran before the target loop device existed, delete only
  the completed stale prepare job after recreating the loop device so Rook can
  rediscover the intended lab disk.
- Ceph Tentacle rejected `osd_memory_target: "536870912"` because it is below
  the observed minimum of `939524096` bytes. Use at least `1073741824` for the
  lab value.
- A 1 GiB OSD memory limit was too low in this lab and caused an OSD crash-loop
  in Ceph config/environment parsing. The successful lab setting was roughly
  `2Gi` memory limit and `1Gi` memory request for OSDs.
- Rook `v1.20.x` can install the Ceph CSI operator, but RBD PVC provisioning
  still needs the `ceph-csi-drivers` chart/resources for ServiceAccounts, RBAC,
  `Driver` CRs, and `OperatorConfig`.
- For a single-node tainted Talos control-plane lab, put control-plane
  tolerations on the RBD CSI driver and on scratch smoke-test jobs. In the
  `ceph-csi-drivers` values, per-driver tolerations belong under
  `drivers.rbd.controllerPlugin.tolerations` and
  `drivers.rbd.nodePlugin.tolerations`; putting them only under
  `operatorConfig.driverSpecDefaults` did not update the generated RBD `Driver`.
- Disable unused CSI drivers such as CephFS in this minimal RBD lab unless they
  are part of the test objective.

Before running any future RBD PVC smoke test, verify the data path first:

```bash
export KUBECONFIG="$PWD/.private/talos-vm-lab/kubeconfig"

kubectl -n rook-ceph exec deploy/rook-ceph-tools -- ceph status
kubectl -n rook-ceph get cephcluster,cephblockpool -o wide
kubectl -n rook-ceph get deploy/rook-ceph.rbd.csi.ceph.com-ctrlplugin \
  ds/rook-ceph.rbd.csi.ceph.com-nodeplugin -o wide
```

The useful smoke-test shape is:

1. Create a scratch namespace and `ceph-block` PVC.
2. Wait for the PVC to bind.
3. Mount it in a writer job that writes a marker and checksum.
4. Delete the writer job to force detach.
5. Mount the same PVC in a reader job and verify the checksum.
6. Delete the scratch namespace.

## GitOps Scope

Do not start by bootstrapping the entire repository into the Talos VM through
Flux.

Preferred VM approach:

- Bring up Talos manually or with minimal generated config.
- Install only the components required for the test.
- Use manual `kubectl`/Helm steps for the lab.
- Record the steps that should become part of the real rebuild runbook.

Full GitOps can be introduced later if the VM becomes a meaningful long-lived
test environment, but that is not the first goal.

## Restore Drill Scope

The safest useful restore drill is an alternate-PVC restore:

1. Pick a target that answers a concrete remaining risk.
2. Create a separate restore destination and PVC name.
3. Point the restore at the existing restic repository credentials.
4. Restore into the scratch PVC.
5. Mount the scratch PVC in an inspection pod.
6. Validate expected files exist.
7. Delete the scratch workload and PVC when done.

Guardrails:

- Do not replace the live PVC.
- Do not create a `ReplicationSource` for the scratch PVC.
- Do not run prune, forget, unlock, or retention-changing operations as part of
  the drill.
- Do not start a duplicate production Plex instance against restored Plex state.
- Avoid running the drill during scheduled backup windows if possible.

Plex VolSync restore has already been tested far enough to validate expected
restored files. From here, additional Plex validation should stay lightweight
unless a new risk appears. A full production-like validation is not practical
without a larger lab architecture and should not be required by default.

A separate small-app restore drill is no longer required as a default next step.
Use one only if it answers a concrete remaining question that the Plex restore
did not answer.

The concrete manual runbook is
[Plex VolSync Restore Drill](./plex-volsync-restore-drill.md). Its companion
manifest is intentionally stored under `tests/manual/` so Flux will not apply it
as part of normal reconciliation.

## Synology And Backup Endpoint Notes

The VM may or may not need direct Synology NFS access.

NFS access matters for:

- Media mounts.
- MMIA image volumes.
- MinIO backing storage if trying to run a separate MinIO instance.

VolSync restore access may only require the restic/S3 endpoint, depending on the
value of `RESTIC_REPOSITORY_URL`. If that endpoint is only available inside the
current cluster, the VM will need a reachable route, ingress, temporary endpoint,
or a copied test repository.

Before any VM restore drill, identify whether the restic endpoint is:

- Internal cluster DNS.
- A LAN-reachable MinIO/S3 URL.
- A Synology-hosted path or service.
- Something else hidden behind the current SOPS-substituted configuration.

Do not decrypt or print secret values into planning notes.

## Storage Decision Link

The Rook decision should depend on restore complexity and Talos-lab friction,
not preference alone.

Current working heuristic:

- Keep Rook for the first rebuild unless real-node disk planning or restore
  validation exposes a concrete blocker. Evaluate storage simplification later,
  after the cluster OS and bootstrap path are modernized.
- If restore on Talos through Rook looks painful or fragile, evaluate simpler
  options before committing to Rook again.

As of 2026-07-04, the Talos lab has tested enough Rook-Ceph to keep it as the
working default: single-node Rook/Ceph reached `HEALTH_OK`, RBD CSI provisioned a
PVC, and a detach/reattach checksum test passed. This is still not a substitute
for real-node disk planning, three-node behavior, or VolSync restore validation.
