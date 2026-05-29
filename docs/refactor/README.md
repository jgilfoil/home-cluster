# Refactor And Rebuild Planning

Captured: 2026-05-12

This directory preserves the planning context for the next major refactor/rebuild
of the home cluster. The goal is to continue in a clean session without losing
the reasoning, constraints, owner priorities, or risk posture from the initial
discussion.

## Read Order

1. [Current State](./current-state.md)
2. [Project Roadmap](./project-roadmap.md)
3. [Automation And AI](./automation-and-ai.md)
4. [Talos And Restore Drills](./talos-and-restore-drills.md)
5. [Plex VolSync Restore Drill](./plex-volsync-restore-drill.md)
6. [Open Questions](./open-questions.md)

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
- Talos is likely the desired target, but should be validated with a migration
  plan before touching real nodes.
- Prefer a staged rebuild over a large, multi-axis migration.
- Avoid combining the future VLAN migration with the cluster rebuild unless
  there is no practical alternative.
- Treat downtime as a budget and tradeoff, not a binary target. Near-zero
  downtime is desirable but not at unlimited cost or complexity.
- Full rehearsal hardware is not currently available. A Hyper-V Talos VM may be
  useful as a narrow smoke/restore lab, but should not become a parallel GitOps
  clone of the whole homelab.

## Related Docs

- [Cluster Orientation](../Cluster-Orientation.md)
- [AI cluster management handoff](../codex-ai-cluster-management-handoff.md)
- [VolSync stale lock runbook](../VolSync-Restic-Locks.md)
- [Rook-Ceph notes](../Rook-Ceph.md)
