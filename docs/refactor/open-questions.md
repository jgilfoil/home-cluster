# Open Questions

Captured: 2026-05-12

These are the main questions to pick up in the next planning session.

## Downtime And Migration

1. What downtime target should the final runbook optimize for after restore and
   bootstrap risk are better understood?
2. Is a Hyper-V Talos VM worth the setup effort as a narrow smoke/restore lab?
3. Is the owner willing to do a same-hardware outage if restore testing is
   strong enough?
4. What is the explicit rollback point after nodes are reformatted?

Current posture:

- Downtime is a tradeoff rather than a fixed requirement. Zero downtime is
  preferred but not at unlimited cost or complexity.
- A few hours is a reasonable target if preparation can make that realistic.
- A few days should be avoided if there is a practical lower-risk path.
- No spare hardware exists today; full rehearsal should be optional, not a hard
  prerequisite.
- If a Hyper-V Talos VM is built, use
  `D:\Hyper-V\Virtual Machine Configurations\` for VM configuration and
  `D:\Hyper-V\Virtual Hard Disks\` for VHD/VHDX files.

## Storage

1. Should Rook-Ceph be retained for the first Talos rebuild to lower migration
   risk?
2. If replacing Rook, what should be evaluated: Mayastor/OpenEBS, Longhorn,
   Synology/NFS-backed dynamic provisioning, or another option?
3. Is the convenience of dynamic PVC provisioning more important than reducing
   storage overhead?
4. Which small app should be used for the first alternate-PVC restore drill?
5. How much Plex validation is enough before destructive work, given that a
   full production-like Plex restore is not practical without major lab
   architecture?

Current posture:

- Keeping Rook for the first Talos rebuild depends on whether Talos + Rook +
  VolSync restore can be made boring enough.
- If that restore path looks painful, simpler storage options should be
  evaluated before committing to Rook again.
- Restore drills should target alternate PVCs and must avoid corrupting or
  rewriting existing backup history.

## Workloads

1. Should `open-webui-pipelines` be backed up or treated as disposable? It has
   a live PVC and StatefulSet, but no Git-defined backup coverage has been
   identified.
2. Should LimeSurvey get VolSync coverage before the rebuild? It has separate
   uploads and MariaDB PVCs, so the backup plan needs to account for both
   filesystem uploads and database consistency.
3. Should `financial-planner` be removed before the rebuild or after?
4. Should CloudNativePG manifests be removed, archived, or kept as a future
   template?
5. Is MMIA dev intentionally scaled to zero, or should that be revisited?

## Architecture

1. Should Talos be adopted on the existing Odroid-H2 nodes?
2. Should Ansible/k3s bootstrap files be retained as historical reference after
   Talos migration?
3. Should the old Makejinja/bootstrap template flow be retired?
4. Should spegel be included in the first stable Talos build or later?
5. Should Gateway API/Envoy Gateway be deferred until after the cluster is
   stable?
6. If a Talos VM is built, should it remain a manual smoke/restore lab instead
   of being fully bootstrapped through this repo?

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
