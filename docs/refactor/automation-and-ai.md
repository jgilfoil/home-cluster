# Automation And AI

Captured: 2026-05-12

## Owner Preference

The owner prefers automation over leaving routine care to future manual effort.
The cluster fell into disrepair when there was less automation, and even the
current automation has not been enough to prevent drift and unsupported
components.

The default stance should be:

- Automate deterministic maintenance where the blast radius is understood.
- Prefer PRs and GitOps for configuration changes.
- Avoid autonomous destructive live changes.
- Use AI for diagnosis, summarization, and patch proposals before live
  remediation.

## Renovate

Renovate remains the primary deterministic updater.

Recommended during rebuild:

- Temporarily reduce automerge.
- Keep dependency dashboard and PR generation active.
- Avoid surprise changes to CNI, storage, ingress, Flux, Kubernetes, Talos,
  cert-manager, and validation workflows.
- Use AI/Codex to review Renovate PRs, identify breaking changes, and generate
  follow-up patches.

Recommended after rebuild:

- Restore selective automerge for low-risk patch/minor updates.
- Keep high-risk infrastructure changes as PRs requiring review.
- Consider grouping related infrastructure changes by blast radius.

## Home Operations Alignment

The current Home Operations direction is relevant because it narrows decisions
and improves maintainability.

Observed alignment targets:

- Talos-based cluster bootstrap.
- Flux-managed GitOps.
- Cilium.
- Renovate-heavy maintenance.
- `home-operations/containers` for images that do not have strong upstream
  support or conventions.
- `home-operations/charts-mirror` as a bridge for charts without OCI support.
- Digest-pinned images and supply-chain metadata where practical.

References:

- [Home Operations docs](https://onedr0p.github.io/home-ops/introduction.html)
- [home-operations/containers](https://github.com/home-operations/containers)
- [home-operations/charts-mirror](https://github.com/home-operations/charts-mirror)
- [Sigstore/cosign introduction](https://edu.chainguard.dev/open-source/sigstore/cosign/an-introduction-to-cosign/)
- [SBOM overview](https://edu.chainguard.dev/open-source/sbom/what-is-an-sbom/)

## AI Tooling Roadmap

The existing handoff doc recommends this operating model:

```text
Alertmanager
  -> Robusta OSS
  -> HolmesGPT
  -> Discord / GitHub issue / GitHub PR
  -> human review and merge
  -> Flux applies changes
```

And a passive diagnostic layer:

```text
K8sGPT Operator
  -> continuous read-only cluster diagnostics
  -> Result CRs / optional notification sink
  -> no auto-remediation
```

## Recommended Timing

Before rebuild:

- Keep AI mostly out of live cluster control.
- Use Codex locally for repo analysis, planning docs, Renovate review, and
  manifest patches.
- Optionally add documentation/runbooks that future tools can consume.

During rebuild:

- Use AI as an interactive assistant, not an autonomous operator.
- Allow read-only cluster inspection where useful.
- Keep all changes PR/file based unless an explicit runbook says otherwise.

After stable rebuild:

- Add Robusta first for alert enrichment and deterministic context gathering.
- Add K8sGPT as passive diagnostics only, with auto-remediation disabled.
- Add HolmesGPT after alert quality and runbooks are good enough.
- Consider GitHub PR generation later, using scoped credentials.

## Autonomy Levels

Level 0: Observe and explain.

Allowed:

- Summarize alerts.
- Inspect Flux and HelmRelease readiness.
- Inspect Kubernetes events.
- Read bounded pod logs.
- Point to likely repo paths.

Level 1: Deterministic allowlisted live actions.

Only after explicit opt-in:

- Reconcile a Flux Kustomization.
- Reconcile a HelmRelease.
- Delete evicted pods.
- Restart a specifically allowlisted Deployment.
- Rerun a specifically allowlisted Job.

Level 2: AI-generated PRs.

Preferred remediation mode:

- Propose Helm values changes.
- Patch resource requests/limits.
- Fix Ingress/Service references.
- Fix image tags.
- Add missing Kustomization/HelmRepository/namespace resources.
- Review Renovate PRs and generate follow-up migration patches.

Level 3: Unrestricted live mutation.

Do not implement.

## Hard Guardrails

Do not allow autonomous mutation of:

- SOPS-encrypted files or Kubernetes Secret values.
- Rook-Ceph resources.
- PVs, PVCs, VolumeSnapshots, VolumeSnapshotClasses, or StorageClasses.
- Nodes.
- Cilium.
- kube-vip.
- cert-manager issuers.
- Flux root Kustomizations.
- Any destructive disk, reset, reboot, or wipe operation.

Do not create systems that:

- Auto-merge AI-generated PRs.
- Give AI broad cluster-admin write access.
- Edit live Flux-managed resources instead of Git.
- Read or transmit secret values to model providers.

## Candidate Runbooks

Useful runbooks to create before or shortly after rebuild:

- Flux HelmRelease not ready.
- Flux Kustomization not ready.
- CrashLoopBackOff.
- OOMKilled.
- ImagePullBackOff.
- PVC blocked.
- Rook-Ceph health.
- VolSync restore.
- Cert-manager failure.
- Ingress failure.
- Node pressure/not ready.
- Plex GPU issue.
- Renovate PR review.
