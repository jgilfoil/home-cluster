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
repo changes needed for the future real cluster, not the VM state itself.

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
