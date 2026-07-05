# Refactor And Rebuild Planning

Captured: 2026-05-12
Updated: 2026-07-05

This directory preserves the planning context for the next major refactor/rebuild
of the home cluster. The goal is to continue in a clean session without losing
the reasoning, constraints, owner priorities, or risk posture from the initial
discussion.

## Read Order

1. [Current State](./current-state.md)
2. [Project Roadmap](./project-roadmap.md)
3. [Automation And AI](./automation-and-ai.md)
4. [Pre-Cutover Safety Checklist](./pre-cutover-safety-checklist.md)
5. [Talos And Restore Drills](./talos-and-restore-drills.md)
6. [Talos Codex MCP Access Bootstrap](./talos-codex-mcp-access.md)
7. [Plex VolSync Restore Drill](./plex-volsync-restore-drill.md)
8. [Open Questions](./open-questions.md)

## Major Goals

1. Limit downtime and avoid critical data loss, especially Plex/media state and
   MMIA business tooling.
2. Automate as much routine care, feeding, updating, and diagnosis as can be
   done safely.
3. Align with current Home Operations community patterns where practical, so the
   cluster is easier to maintain and easier to reason about.
4. Use AI-backed operations tooling thoughtfully: read-only and PR-driven first,
   deterministic remediation only after explicit allowlisting.

## Current Strategic Bias

- Preserve the current network model during the rebuild.
- Treat storage as the highest-risk design area.
- Talos is the desired target for the v3 rebuild, but real-node changes still
  require a concrete migration/cutover plan.
- Prefer a staged rebuild over a large, multi-axis migration.
- Avoid combining the future VLAN migration with the cluster rebuild unless
  there is no practical alternative.
- Treat downtime as a budget and tradeoff, not a binary target. Near-zero
  downtime is desirable but not at unlimited cost or complexity.
- Full rehearsal hardware is not currently available. A Hyper-V Talos VM now
  exists as a narrow smoke/restore lab and should be retained during the rebuild,
  but should not become a parallel GitOps clone of the whole homelab.
- Keep Rook-Ceph for the first Talos rebuild unless real-node storage planning
  or restore validation exposes a concrete blocker. Replacing storage can be a
  later project.
- Plex VolSync restore has been tested far enough to validate expected restored
  files. Do not overbuild additional Plex validation unless a new risk appears.
- `open-webui-pipelines` is discard-for-now. LimeSurvey backup coverage is
  deferred until the last pre-cutover hardening pass.
- Old k3s/Ansible/bootstrap scaffolding should be archived as historical
  reference, not maintained as the v3 build path.
- Before any real-node formatting, use the
  [Pre-Cutover Safety Checklist](./pre-cutover-safety-checklist.md) as the
  hard gate for backup/export confidence, endpoint survival, restore acceptance,
  and point-of-no-return approval.

## Current Lab Status

The Hyper-V Talos lab should be kept for now because it may remain useful during
the rebuild. The important validated state from 2026-07-04 is:

- Single-node Hyper-V Talos lab ran Rook `v1.20.1` / Ceph `v20.2.1` with one
  explicitly targeted loop-backed OSD.
- `CephCluster/rook-ceph` reached `Ready` with `HEALTH_OK`.
- `CephBlockPool/ceph-blockpool` reached `Ready` with replication size `1`.
- RBD CSI provisioned a scratch `ceph-block` PVC.
- A detach/reattach write-read checksum smoke test passed.
- The result proves basic Talos + Rook-Ceph + RBD mechanics only; real-node disk
  planning, three-node behavior, performance, and VolSync restore behavior still
  require separate gates.

## Related Docs

- [Cluster Orientation](../Cluster-Orientation.md)
- [AI cluster management handoff](../codex-ai-cluster-management-handoff.md)
- [VolSync stale lock runbook](../VolSync-Restic-Locks.md)
- [Rook-Ceph notes](../Rook-Ceph.md)
