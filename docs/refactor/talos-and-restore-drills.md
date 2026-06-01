# Talos And Restore Drills

Captured: 2026-05-25

This note refines the earlier rehearsal recommendation. Full spare hardware is
not currently available, and a complete production-like rehearsal cluster would
add a lot of setup complexity. A narrower Talos VM or restore drill may still be
worthwhile if it answers specific migration-risk questions.

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

A Hyper-V Talos VM can be useful as a focused spike, but it should not start as
a full GitOps clone of the homelab.

On the Hyper-V host, use the existing dedicated Hyper-V storage locations rather
than defaulting to the user profile or `C:\ProgramData` paths:

- VM configuration path: `D:\Hyper-V\Virtual Machine Configurations\`
- VHD/VHDX path: `D:\Hyper-V\Virtual Hard Disks\`

Any PowerShell runbook or generated commands should make those paths explicit,
for example by passing `-Path "D:\Hyper-V\Virtual Machine Configurations"` to
`New-VM` and writing the Talos OS disk under
`D:\Hyper-V\Virtual Hard Disks\`.

## Cluster Template North Star

Use the current `onedr0p/cluster-template` as the north star for Talos-era
decisions, but not as a mandate to run its full task list or adopt every default
during the first rebuild.

Template basics that matter for the VM/rebuild test:

- Talos is the node OS baseline, with rendered Talos config treated as a
  committed artifact/runbook input rather than hand-edited node state.
- The Kubernetes API VIP, node IPs, and gateway/load-balancer IPs should be
  explicit and non-overlapping inside the current LAN range.
- Cilium should be the CNI, with Talos' built-in CNI and kube-proxy disabled for
  the Talos target. Keep the current Cilium/L2 mental model unless a deliberate
  BGP decision is made.
- Flux, SOPS-age, Renovate, cert-manager, external-dns, cloudflared, and
  k8s-gateway remain part of the desired operating model.
- The template's Gateway API/Envoy path is useful strategic context, but the
  first rebuild should not combine Talos/storage recovery with an ingress-nginx
  to Gateway API migration unless testing proves that migration is necessary.
- The template's current version pins are not automatically accepted. Choose the
  Talos and Kubernetes versions deliberately after checking Cilium, Rook-Ceph,
  VolSync, snapshot-controller, and hardware compatibility.
- The template's storage guidance reinforces the existing project bias: if using
  replicated storage, use dedicated disks and prove restore behavior before
  trusting it. The VM can validate mechanics, not three-node Rook behavior.

Decision points to preserve from the template when building the VM:

1. Hyper-V VM configuration and VHD/VHDX paths. Use
   `D:\Hyper-V\Virtual Machine Configurations\` and
   `D:\Hyper-V\Virtual Hard Disks\` unless the host layout changes.
2. VM node IP, API VIP, gateway/LB test IPs, DNS, and NTP values.
3. Talos Image Factory schematic/extensions. Start minimal; add only extensions
   needed for the VM test.
4. Install disk identifier and primary NIC MAC address from Talos maintenance
   mode, not guesses.
5. Cilium load-balancer mode: use the current/simple L2 posture for testing;
   only choose DSR/BGP if the LAN/router path is deliberately validated.
6. GitOps scope: do not run a full template-style app bootstrap for the whole
   homelab in the VM. Install only the bootstrap components needed to answer the
   current risk question, then record what should become the real rebuild
   runbook.

Useful questions for a VM:

- Can a single-node Talos cluster be brought up without excessive friction?
- Can CNI, basic storage, and VolSync/restic run correctly on Talos?
- Can the VM reach the backup endpoint that VolSync uses?
- Can a small restic backup be restored into a scratch PVC?

Questions a VM probably will not answer well:

- Real Odroid disk layout and device naming.
- Three-node Rook-Ceph behavior.
- Intel GPU behavior for Plex.
- Real ingress, DNS, Cloudflare tunnel, and LAN routing behavior.
- Full production cutover timing.

The VM should be disposable. The artifact worth keeping is the runbook and any
repo changes needed for the future real cluster, not the VM state itself. The
single-node initialization steps and first successful smoke-test result are
recorded in [Talos VM Cluster Initialization](./talos-vm-cluster-initialization.md).

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

1. Pick a small VolSync-backed app first.
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

For Plex, a full production-like validation is not practical without a larger
lab architecture. A useful compromise is to restore Plex metadata into an
alternate PVC, inspect it read-only, and validate that expected database and
metadata files are present.

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

The Rook decision should depend on restore complexity, not preference alone.

Current working heuristic:

- If Talos + Rook + VolSync restore can be made boring enough, keep Rook for the
  first rebuild and evaluate storage simplification later.
- If restore on Talos through Rook looks painful or fragile, evaluate simpler
  options before committing to Rook again.
