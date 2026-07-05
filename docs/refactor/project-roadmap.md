# Project Roadmap

Captured: 2026-05-12
Updated: 2026-07-05

## Goals

1. Minimize downtime and avoid critical data loss.
2. Automate routine care and maintenance wherever it is sane and safe.
3. Align with Home Operations community best practices where practical.
4. Rebuild/refactor in a way future maintenance can survive limited owner time
   and attention.

## Guiding Principles

- Do not change every major subsystem at once.
- Keep the current network model stable during the rebuild.
- Treat storage and restore paths as the highest-risk part of the project.
- Prefer GitOps and PR-driven changes over live mutation.
- Automate guardrails and validation before automating remediation.
- Use the community defaults as a decision-narrowing tool, not as a substitute
  for local judgment.

## Recommended Strategy

This should be treated as a v3 cluster project.

The current strategic bias is:

- Talos is the target Kubernetes node OS for the v3 rebuild.
- Keep Cilium, Flux, Renovate, SOPS-age, VolSync, and the existing network
  model.
- Keep Rook-Ceph for the first Talos rebuild unless real-node disk planning or
  restore validation exposes a concrete blocker, then evaluate replacing it
  later.
- Do not migrate to VLANs or Gateway API during the same cutover.
- Temporarily reduce Renovate automerge while the rebuild is underway.
- Treat downtime as a sliding tradeoff. The preferred target is a planned
  maintenance window of hours if that can be achieved with reasonable
  preparation, while avoiding plans that casually risk multiple days offline.
- Use restore drills to reduce risk, but do not require a full parallel
  rehearsal cluster before the migration shape is clear. Plex VolSync restore
  has already validated expected restored files, so further Plex validation
  should stay lightweight unless a new risk appears.

## Phase 0: Planning And Inventory

Purpose: make sure the project has a clear map before any risky changes.

Deliverables:

- Workload criticality matrix.
- PVC/state inventory and restore priority.
- Explicit downtime target.
- Decision on temporary hardware or VM rehearsal.
- Restore acceptance checklist, especially for Plex and MMIA.

Decision gates and current answers:

- What downtime window is acceptable? A planned window measured in hours is the
  working target if preparation makes that realistic.
- Can temporary hardware or VMs be used? Yes: a disposable Hyper-V Talos VM is
  already in use as a narrow lab.
- Is Rook retained for the first Talos rebuild? Yes. The 2026-07-04 disposable
  Talos lab proved basic single-node Rook-Ceph/RBD mechanics; real-node disk
  planning and restore validation remain separate gates.
- Is Plex metadata the top restore validation target? Yes, and the Plex VolSync
  restore drill has already validated expected restored files.

Current owner posture:

- Zero downtime would be ideal, but not at unlimited cost or complexity.
- A few days of downtime should be avoided if reasonably possible.
- A few hours of downtime is worth spending some planning and setup effort to
  achieve.
- No spare hardware is currently available. The Hyper-V Talos VM is the narrow
  Talos/restore lab and should be retained during the rebuild, not turned into a
  full homelab clone.

## Phase 1: Pre-Rebuild Hardening

Purpose: improve recovery confidence while the current cluster still exists.

Candidate work:

- Do not require a separate small-app restore drill unless a new risk calls for
  it. Plex VolSync restore has already provided the stronger validation signal.
- Keep any additional Plex validation lightweight. Do not replace the live PVC
  or start a duplicate production Plex instance against restored state.
- Use the 2026-07-04 Talos-lab Rook-Ceph/RBD result as the baseline storage
  mechanics check. The remaining storage gates are real-node disk planning,
  VolSync restore behavior through the target storage path, and backup endpoint
  survival if the old cluster-hosted S3/MinIO front door is unavailable.
- Add LimeSurvey backups only in the final pre-cutover hardening pass if
  LimeSurvey will remain.
- Treat `open-webui-pipelines` as discard-for-now.
- Put Renovate into rebuild-safe mode.
- Fix currently broken Flux reconciliation items before cutover if they block
  clean bootstrap.

Renovate rebuild-safe mode should disable automerge for:

- Kubernetes/k3s/Talos
- Cilium
- Flux
- Rook-Ceph
- OpenEBS/storage
- VolSync
- ingress-nginx/external-dns/cloudflared
- cert-manager
- GitHub Actions that affect validation

Low-risk application updates can still be opened as PRs, but avoid silent churn.

## Phase 2: Community Alignment Pass

Purpose: align the target architecture with current Home Operations patterns
before rebuilding.

Likely alignment targets:

- Talos-based bootstrap.
- Flux-managed cluster state.
- Cilium as CNI.
- Renovate as the primary deterministic updater.
- `ghcr.io/home-operations/*` images where applicable.
- Digest-pinned images where practical.
- bjw-s `app-template`, updated to current conventions.
- spegel after the rebuild for registry resilience.
- Archive old k3s/Ansible/bootstrap scaffolding as historical reference once the
  Talos-focused runbooks/manifests are durable. Do not maintain that scaffolding
  as the v3 build path.

Not recommended during the initial cutover:

- VLAN migration.
- Gateway API / Envoy Gateway migration.
- Secret management migration away from SOPS-age.
- Replacing every app chart at once.

References:

- [Home Operations docs](https://onedr0p.github.io/home-ops/introduction.html)
- [onedr0p/cluster-template](https://github.com/onedr0p/cluster-template)
- [home-operations/containers](https://github.com/home-operations/containers)
- [home-operations/charts-mirror](https://github.com/home-operations/charts-mirror)

## Phase 3: Target Architecture Decision

Purpose: choose the rebuild shape before implementation.

Main storage options:

- Talos + Rook-Ceph + VolSync first, then optimize storage later.
- Talos + alternative storage such as Mayastor/OpenEBS or Longhorn.
- Hybrid approach using Synology/NFS for some state and block storage for apps
  that benefit from dynamic RWO PVCs.

Current recommendation:

Use the lower-risk path first unless testing proves Rook is unacceptable:
Talos + Rook-Ceph + proven VolSync restore. Replacing Rook can be a second
project once the cluster OS and bootstrap are modernized.

The 2026-07-04 disposable Talos lab did not find a Rook-Ceph blocker: a
single-node Rook `v1.20.1` / Ceph `v20.2.1` lab reached `HEALTH_OK`, provisioned
an RBD PVC through CSI, and passed a detach/reattach write-read checksum smoke
test. This supports keeping Rook-Ceph for the first Talos rebuild while still
requiring real-node disk planning and VolSync restore validation.

Reasons:

- The most painful failure mode is data loss, not an imperfect storage backend.
- Plex and media app state already depend on Ceph PVCs and VolSync.
- Changing OS and storage in the same cutover increases the debugging surface.

Storage references:

- [Sidero Talos storage guidance](https://docs.siderolabs.com/kubernetes-guides/csi/storage)
- [OpenEBS Mayastor on Talos](https://openebs.io/docs/Solutioning/openebs-on-kubernetes-platforms/talos)

## Phase 4: Rebuild Rehearsal

Purpose: make the destructive cutover boring.

Candidate work:

- Keep the existing Hyper-V Talos VM as the focused lab; it may come in handy
  during the rebuild.
- Generate/update Talos configs without applying them to real nodes.
- Render Flux manifests locally.
- Validate with kubeconform and flux-local where possible.
- Reuse or rebuild the successful Rook-Ceph lab only when it answers a concrete
  remaining cutover question.
- Use additional VolSync restore checks only where they answer a concrete
  remaining risk. The goal is to prove restore mechanics without mutating live
  PVCs or backup retention.
- Write the exact cutover runbook.
- Define the point-of-no-return gate. There may be no practical same-hardware
  rollback after real nodes are reformatted, so the safety model is final
  backups, exports, acceptance criteria, and untouched backup history rather
  than assuming rollback is available.

If no temporary hardware is available, this phase becomes even more important
because the real cutover is an outage.

## Phase 5: Cutover

High-level order:

1. Freeze changes.
2. Pause or restrict Renovate.
3. Run final VolSync backups.
4. Export final live inventory.
5. Reformat/bootstrap Talos.
6. Bring up Cilium, DNS, ingress, cert-manager, Flux, and repositories.
7. Bring up storage and VolSync.
8. Restore media apps.
9. Restore/verify Plex metadata.
10. Bring up MMIA.
11. Bring up default apps.
12. Bring up observability and maintenance automation.
13. Keep old backups untouched until acceptance criteria are met.

Acceptance criteria:

- Plex library and metadata are intact.
- Core media workflows work.
- MMIA prod bot is running and can access its image volume.
- Homepage or equivalent dashboard exists.
- External and internal ingress paths work.
- VolSync backups are running after restore.
- Flux is green.

## Phase 6: Post-Rebuild Automation

Purpose: reduce future neglect without granting unsafe autonomy.

Candidate work:

- Re-enable Renovate with tuned automerge rules.
- Add richer runbooks.
- Add alert enrichment.
- Add passive diagnostics.
- Add AI-assisted PR generation and review.
- Later, add narrow deterministic live remediation.

See [Automation And AI](./automation-and-ai.md).
