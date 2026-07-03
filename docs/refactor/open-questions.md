# Open Questions

Captured: 2026-05-12
Updated: 2026-07-02

These are the main questions to pick up in the next planning session.

## Resolved Or Current Decisions

- Hyper-V Talos VM: yes, already exists and is the narrow smoke/restore lab.
- Rook-Ceph: retain for the first Talos rebuild unless lab testing exposes a
  concrete blocker.
- Small restore drill: no separate small-app drill is required by default. Plex
  VolSync restore has already validated expected restored files.
- Plex validation: keep additional validation lightweight unless a new risk
  appears.
- `open-webui-pipelines`: discard-for-now.
- LimeSurvey VolSync coverage: defer until the last pre-cutover hardening pass.
- Old k3s/Ansible/bootstrap scaffolding: archive as historical reference; do
  not maintain it as the v3 build path once Talos docs/runbooks replace it.
- Gateway API/Envoy Gateway and VLAN migration remain deferred until after the
  rebuilt cluster is stable.

## Downtime And Migration

1. What downtime target should the final runbook optimize for after restore and
   bootstrap risk are better understood?
2. Is the owner willing to do a same-hardware outage if restore testing is
   strong enough?
3. What is the explicit point-of-no-return gate before nodes are reformatted?

Current posture:

- Downtime is a tradeoff rather than a fixed requirement. Zero downtime is
  preferred but not at unlimited cost or complexity.
- A few hours is a reasonable target if preparation can make that realistic.
- A few days should be avoided if there is a practical lower-risk path.
- No spare hardware exists today; full rehearsal should be optional, not a hard
  prerequisite.
- A true same-hardware rollback after formatting nodes may not exist. The
  practical mitigation is a cutover gate with final backups, exports, restore
  confidence, acceptance criteria, and old backup history left untouched.

## Storage

1. What is the current Talos-lab Rook-Ceph status, and what blocker, if any,
   would change the current keep-Rook decision?
2. If Rook does prove unacceptable, what should be evaluated: Mayastor/OpenEBS,
   Longhorn, Synology/NFS-backed dynamic provisioning, or another option?
3. Is the convenience of dynamic PVC provisioning more important than reducing
   storage overhead?

Current posture:

- The current decision is to keep Rook for the first Talos rebuild unless a
  concrete blocker appears.
- Read-only Talos lab verification on 2026-07-02 showed the single-node Talos
  lab is up with local-path storage and VolSync, but Rook-Ceph has not been
  installed yet: no `rook-ceph` namespace and no Rook/Ceph CRDs.
- If the Rook path looks painful, simpler storage options should be evaluated
  before committing to Rook again.
- Restore drills should target alternate PVCs and must avoid corrupting or
  rewriting existing backup history.

## Workloads

1. Should LimeSurvey get VolSync coverage before the rebuild? It has separate
   uploads and MariaDB PVCs, so the backup plan needs to account for both
   filesystem uploads and database consistency.
2. Should `financial-planner` be removed before the rebuild or after?
3. Should CloudNativePG manifests be removed, archived, or kept as a future
   template?
4. Is MMIA dev intentionally scaled to zero, or should that be revisited?

## Architecture

1. Should Talos be adopted on the existing Odroid-H2 nodes?
2. What exact archival shape should be used for old Ansible/k3s/bootstrap
   material after Talos replacement runbooks are durable?
3. Should spegel be included in the first stable Talos build or later?
4. If the Talos VM continues to be useful, when, if ever, should it move beyond
   a manual smoke/restore lab into a GitOps-managed test environment?

## Automation

1. How conservative should Renovate be during the rebuild?
2. Which updates, if any, should continue to automerge during the project?
3. Should Robusta be added before the rebuild for better alert context, or after
   the rebuilt cluster is stable?
4. Should K8sGPT be tried as passive diagnostics after rebuild?
5. What narrow live remediation actions would the owner actually trust?

## Acceptance Criteria

Draft acceptance criteria for the rebuilt cluster:

- Plex library and metadata are intact.
- Core media workflows work end to end.
- MMIA production Discord bot runs and can access `/app/images`.
- Homepage or equivalent dashboard exists.
- Internal and external ingress work.
- Cloudflare tunnel works.
- Local DNS through k8s-gateway works.
- VolSync backups run after restore.
- Flux Kustomizations and HelmReleases are green.
- Renovate is active but not reckless.
- There is a documented restore/runbook path for critical apps.
