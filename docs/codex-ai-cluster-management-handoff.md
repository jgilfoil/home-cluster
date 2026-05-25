# Codex Handoff: AI-Assisted Cluster Management for `jgilfoil/home-cluster`

Generated: 2026-05-12

This document is intended to be pasted or uploaded into a Codex session after loading the `jgilfoil/home-cluster` repository. It carries forward the research, repo-specific findings, recommended architecture, implementation sequence, and safety guardrails from the ChatGPT analysis.

## Goal

Improve autonomy for a k3s + Flux homelab cluster without undermining GitOps. The target outcome is not an unrestricted AI cluster admin. The target outcome is a safe, mostly PR-driven system that can:

- Watch Alertmanager notifications.
- Enrich alerts with logs, events, metrics, Flux status, and recent Git/Renovate context.
- Produce root-cause analysis.
- Perform only narrow deterministic remediation where explicitly allowlisted.
- Prefer GitHub PRs for actual configuration changes so Flux remains the source of truth.

Recommended operating model:

```text
Alertmanager
  -> Robusta OSS for alert intake, enrichment, routing, deterministic playbooks
  -> HolmesGPT for AI RCA and proposed fixes
  -> Discord / GitHub issue / GitHub PR
  -> human review and merge
  -> Flux applies changes
```

Parallel diagnostic layer:

```text
K8sGPT Operator
  -> continuous read-only cluster diagnostics
  -> Result CRs / optional notification sink
  -> no auto-remediation
```

Interactive SRE/dev layer:

```text
Codex / Claude Code / Cursor
  -> repo edits and PRs
  -> Flux-aware investigation
  -> Kubernetes read-only investigation
  -> no secret decryption or live destructive changes
```

## Current repository context verified from GitHub connector

Repository: `jgilfoil/home-cluster`
Default branch: `main`
Repo style: public GitOps homelab repository derived from an older `onedr0p/cluster-template` generation.

Verified facts from repo inspection:

- `README.md` describes a home Kubernetes cluster running k3s and based on `onedr0p/cluster-template`.
- README badge indicates k3s `v1.30.1+k3s1`.
- README lists GitOps tooling as Flux and Renovate.
- README lists networking components: Cilium, ingress-nginx, k8s-gateway, kube-vip, cloudflared, pod-gateway/VPN, cert-manager.
- README lists storage components: Rook-Ceph, VolSync, OpenEBS, MinIO backed by NFS, Synology NFS/media/backups.
- README lists observability components: kube-prometheus-stack, Grafana, metrics-server, Hubble.
- README lists maintenance/optimization components: system-upgrade-controller, kured, reloader, descheduler, node-feature-discovery, Intel GPU plugin.
- `.cursor/rules/repo-context.mdc` already exists and says this repo is GitOps-managed with k3s, Flux, Renovate, Kubernetes YAML under `kubernetes/`, provisioning under `ansible/` and `bootstrap/`, and app directories following `kubernetes/apps/<namespace>/<app>/`.
- `kubernetes/flux/apps.yaml` uses Flux `Kustomization` API `kustomize.toolkit.fluxcd.io/v1`, path `./kubernetes/apps`, `prune: true`, SOPS decryption, and cluster variable substitution.
- `kubernetes/apps/observability/kube-prometheus-stack/app/helmrelease.yaml` uses Flux `HelmRelease` API `helm.toolkit.fluxcd.io/v2`.
- kube-prometheus-stack has Alertmanager enabled and configured with 3 replicas.
- Alertmanager values are pulled from a SOPS-encrypted Secret named `alertmanager-config` via `valuesFrom`.
- `kubernetes/apps/observability/kube-prometheus-stack/app/secret.sops.yaml` is an encrypted Secret and cannot be inspected without the private age key.
- `.sops.yaml` uses `age`, not GPG. The uploaded external report’s “SOPS-GPG -> age” recommendation is stale for the current repo.
- Renovate config exists at `.github/renovate.json5` and already scans Flux, Helm values, Kubernetes YAML, Kustomize files, Ansible Galaxy, pip requirements, and custom regex-managed dependencies.
- There is a current Renovate backlog with major/minor PRs for kube-prometheus-stack, snapshot-controller, reloader, pod-gateway, open-webui, external-dns, grafana, GitHub Actions, ingress-nginx, Radarr, Prowlarr, Homepage, cloudflared, VolSync, node-feature-discovery, kured, etc.
- No current repo references were found for K8sGPT, HolmesGPT, Robusta, kagent, MCP servers, `AGENTS.md`, or `CLAUDE.md`.

## Corrections to the earlier external report

The uploaded report was useful directionally, but several details should be handled carefully in Codex work:

1. **SOPS correction**

   The report says the repo uses SOPS-GPG and recommends migration to age. The current repo already uses SOPS with age. Do not create a SOPS-GPG migration task unless new evidence contradicts `.sops.yaml`.

2. **Flux API correction**

   The report warns about Flux beta API removals. That warning is valid in general, but inspected current files already use:

   ```text
   helm.toolkit.fluxcd.io/v2
   kustomize.toolkit.fluxcd.io/v1
   ```

   Codex should still grep for old APIs before making a conclusion:

   ```bash
   rg 'v1beta|v2beta|helm.toolkit.fluxcd.io/v2beta|kustomize.toolkit.fluxcd.io/v1beta' kubernetes bootstrap ansible
   ```

3. **Release/version/pricing caution**

   The earlier report includes many 2026 release numbers, pricing claims, and CNCF dates. Treat those as useful research notes, not guaranteed facts. Pin chart versions only after checking current chart metadata in the repo/Codex environment.

4. **Upstream template framing**

   The report says upstream `onedr0p/cluster-template` has moved toward Talos/Gateway API. This is plausible and useful as strategic context, but do not assume this repo is ready for Talos or Gateway API without a dedicated migration plan.

5. **Core architecture still stands**

   The main recommendation remains valid: deterministic automation first, AI diagnosis second, PR-based remediation third, highly constrained live actions only as a later phase.

## Recommended stack for this repo

| Component | Recommendation | Role | Autonomy posture |
|---|---|---|---|
| Renovate | Keep and tune | Deterministic dependency updates | Existing PR automation |
| Robusta OSS | Add first | Alertmanager receiver, enrichment, routing, deterministic playbooks | Start read-only/enrichment only |
| HolmesGPT | Add after Robusta | AI RCA, runbook-guided diagnosis, optional GitHub PRs | Read-only first; PR creation later |
| K8sGPT Operator | Add as passive layer | Continuous cluster diagnostic scanner | `autoRemediation: false` |
| Flux MCP server | Add for workstation/Codex/Claude workflow if feasible | Flux-aware investigation and GitOps context | Read-only by default |
| Kubernetes MCP server | Optional workstation tool | Read-only cluster events/logs/resources | Read-only; no Secrets |
| kagent | Later only | Custom in-cluster agents | Human approval gates required |
| kubectl-ai / Headlamp AI | Optional | Ad hoc troubleshooting UI/CLI | Manual approval only |
| Enterprise AIOps | Skip initially | Komodor/Kubiya/Causely/etc. are likely wrong economics for homelab | N/A |

## Architecture to implement

```text
                         kube-prometheus-stack
                              Alertmanager
                                   |
                                   | webhook
                                   v
                              Robusta OSS
                    alert enrichment / playbooks / sinks
                                   |
                     +-------------+-------------+
                     |                           |
                     v                           v
                HolmesGPT                  Discord / alert sink
        RCA, runbooks, proposed fixes
                     |
                     | optional GitHub PR
                     v
              GitHub repository
              jgilfoil/home-cluster
                     |
                     | merge
                     v
                  Flux applies
```

K8sGPT should run separately:

```text
K8sGPT Operator
  -> analyzes cluster state
  -> writes Result CRs
  -> optional notifications
  -> no live remediation
```

## Autonomy levels

### Level 0: Observe and explain

Safe immediately.

Allowed:

- Summarize active alerts.
- Inspect Flux Kustomization and HelmRelease readiness.
- Inspect Kubernetes events.
- Read pod logs, preferably bounded with `--tail`.
- Explain likely root cause.
- Point to likely repo paths.

### Level 1: Deterministic allowlisted live actions

Only after testing and explicit opt-in.

Candidate actions:

- `flux reconcile kustomization <name> -n flux-system`
- `flux reconcile helmrelease <name> -n <namespace>`
- Delete Evicted Pods.
- Restart a specifically allowlisted Deployment.
- Rerun a specifically allowlisted Job.

Do not include this on the first implementation pass unless requested.

### Level 2: AI-generated PRs

Primary desired remediation pattern.

Allowed:

- Propose Helm values changes.
- Patch resource requests/limits.
- Fix Ingress/Service references.
- Fix image tags.
- Add missing Kustomization/HelmRepository/namespace resources.
- Adjust alert routing.
- Review Renovate PRs and generate follow-up migration patches.

### Level 3: Unrestricted live mutation

Do not implement.

Never allow:

- AI cluster-admin.
- AI auto-merging its own PRs.
- AI editing live Flux-managed resources instead of Git.
- AI mutating Rook-Ceph/PVC/node/networking resources without human approval.

## Hard safety guardrails for Codex

When working in this repo:

1. Prefer Git changes over live cluster changes.
2. Do not decrypt, print, summarize, or exfiltrate SOPS secrets.
3. Do not ask for or expose age private keys, kubeconfigs, GitHub tokens, Cloudflare tokens, API keys, Plex tokens, or application credentials.
4. Do not add workflows or agents that require cluster-admin unless explicitly justified and reviewed.
5. Do not enable K8sGPT auto-remediation.
6. Do not enable autonomous destructive Robusta playbooks on first pass.
7. Do not create AI automation that auto-merges PRs.
8. Do not let AI modify live Rook-Ceph, PVCs, nodes, Cilium, kube-vip, cert-manager ClusterIssuers, StorageClasses, or SOPS files.
9. Mask Secrets in all MCP/agent tooling where supported.
10. Use namespace-scoped or least-privilege RBAC wherever possible.
11. For AI PR creation, use a GitHub App or scoped token with only required repo permissions.
12. Validate generated YAML before finalizing PRs.

## Resources that should be protected from live AI mutation

Block autonomous mutation for these resource families:

```text
- Rook-Ceph resources: CephCluster, CephBlockPool, CephFilesystem, CephObjectStore
- PersistentVolume
- PersistentVolumeClaim
- VolumeSnapshot
- VolumeSnapshotClass
- StorageClass
- Node
- Cilium resources
- kube-vip resources
- cert-manager ClusterIssuer / Issuer unless a human reviews
- SOPS-encrypted files
- Kubernetes Secrets
- Flux root Kustomizations unless a human reviews
```

## Suggested first PR: add `AGENTS.md`

Codex should consider adding a repo-root `AGENTS.md` to make future AI behavior explicit.

Suggested content:

```markdown
# Agent Instructions

This repository is the source of truth for the home Kubernetes cluster.

Prefer Git changes and pull requests over live cluster mutation. The cluster is managed by Flux, so live changes to Flux-managed resources may be reverted.

Do not request, decrypt, print, summarize, or exfiltrate secret values from SOPS files, Kubernetes Secrets, age keys, kubeconfigs, API tokens, private keys, or application credentials.

When investigating incidents, inspect Flux Kustomization and HelmRelease status before suggesting `kubectl patch` or direct live edits.

Live remediation is limited to explicitly documented, allowlisted runbooks. Never perform destructive changes to Rook-Ceph, PVCs, PVs, nodes, Cilium, kube-vip, cert-manager issuers, StorageClasses, or SOPS-encrypted resources without human approval.

For manifest changes, validate YAML and Flux resources before proposing a PR. Keep changes consistent with the existing `kubernetes/apps/<namespace>/<app>/` structure.

For dependency updates, prefer Renovate. AI should review, explain, and patch around Renovate PRs, not replace Renovate.
```

## Suggested second PR: add project documentation

Add a project doc such as:

```text
docs/ai-cluster-management.md
```

It should document:

- Goal and architecture.
- Tool choices.
- Guardrails.
- Robusta/Holmes/K8sGPT rollout plan.
- Alert runbooks.
- How to disable AI tooling quickly.
- How to rotate/revoke credentials.

## Suggested third PR: add Robusta as alert enrichment layer

Candidate path:

```text
kubernetes/apps/observability/robusta/
  ks.yaml
  app/
    kustomization.yaml
    helmrelease.yaml
    secret.sops.yaml       # only if needed
```

Before implementing, inspect existing repo conventions for:

- Namespace naming.
- HelmRepository placement under `kubernetes/flux/repositories/helm/`.
- How this repo defines `ks.yaml` dependencies.
- Existing observability app patterns.
- Whether Discord/webhook secrets are already in the encrypted Alertmanager config.

Potential chart source to verify before use:

```text
Robusta chart repository: https://robusta-charts.storage.googleapis.com
```

Initial Robusta posture:

- Alert enrichment only.
- Notifications routed to the existing sink if available.
- No broad delete/restart/scale actions.
- No arbitrary command execution.
- No AI mutation.

Recommended default enrichers/playbooks:

- logs enricher
- CrashLoopBackOff reporter
- ImagePullBackOff reporter
- OOMKilled context
- Kubernetes warning event context

## Suggested fourth PR: route Alertmanager to Robusta

Current Alertmanager config is encrypted in:

```text
kubernetes/apps/observability/kube-prometheus-stack/app/secret.sops.yaml
```

Codex must not decrypt or inspect secret values unless explicitly given safe local access by the repo owner. The implementation may need to be described as manual steps if Codex cannot edit encrypted content.

Conceptual Alertmanager route:

```yaml
receivers:
  - name: robusta
    webhook_configs:
      - url: http://robusta-runner.observability.svc.cluster.local/api/alerts
        send_resolved: true

route:
  routes:
    - receiver: robusta
      matchers:
        - severity=~"warning|critical"
```

Service name, namespace, and port must be verified against the actual Robusta Helm chart manifests/values.

## Suggested fifth PR: add HolmesGPT read-only RCA

Candidate path:

```text
kubernetes/apps/observability/holmesgpt/
  ks.yaml
  app/
    kustomization.yaml
    helmrelease.yaml
    secret.sops.yaml       # model/API/GitHub credentials, if required
    configmap.yaml         # runbooks, if appropriate
```

Potential chart source to verify before use:

```text
HolmesGPT is commonly deployed via Robusta/Holmes charts; verify current chart repo and chart name before pinning.
```

Initial posture:

- Kubernetes read-only access.
- Prometheus/Alertmanager read-only access.
- GitHub read-only or no GitHub access at first.
- No live write tools.
- No PR creation until output quality is validated.

Second phase:

- GitHub PR creation using a scoped token or GitHub App.
- Runbook-guided investigations.
- PRs only; no live mutation.

Recommended Holmes runbooks to create:

```text
HelmReleaseNotReady
KustomizationNotReady
CrashLoopBackOff
OOMKilled
ImagePullBackOff
PVCBlocked
RookCephHealth
CertManagerFailure
IngressRouteFailure
NodePressureOrNotReady
PlexGpuIssue
```

## Suggested sixth PR: add K8sGPT Operator read-only

Candidate path:

```text
kubernetes/apps/observability/k8sgpt/
  ks.yaml
  app/
    kustomization.yaml
    helmrelease.yaml
    secret.sops.yaml       # model provider secret, if required
```

Potential chart source to verify before use:

```text
K8sGPT chart repository: https://charts.k8sgpt.ai/
```

Hard requirement:

```yaml
autoRemediation: false
```

Use K8sGPT for passive continuous diagnostics only. It should not mutate live cluster state because that conflicts with Flux.

## Suggested workstation/Codex MCP setup

Prefer MCP tools in read-only mode by default.

Candidate tools:

- Flux MCP server / flux-operator MCP server, read-only, mask secrets.
- Kubernetes MCP server, read-only, no Secret access.
- Prometheus MCP or Holmes Prometheus tooling, read-only.
- GitHub access for PR creation only when authorized.

Desired agent flow:

```text
AI sees alert
  -> checks Alertmanager/Prometheus context
  -> checks Flux resources
  -> checks Kubernetes events/logs
  -> maps issue to repo path
  -> proposes PR or issue
  -> human reviews
  -> merge
  -> Flux reconciles
```

## Recommended runbooks

### `FluxHelmReleaseNotReady`

Trigger:

- Flux alert for HelmRelease not ready.
- Prometheus alert indicating helm-controller/Flux issue.

Investigation:

```bash
flux get hr -A
flux get sources helm -A
kubectl get helmrelease -A
kubectl describe helmrelease <name> -n <namespace>
kubectl logs -n flux-system deploy/helm-controller --tail=100
kubectl logs -n flux-system deploy/source-controller --tail=100
```

Behavior:

- Diagnose source/chart/values/CRD failure.
- Identify repo path.
- Propose PR.
- Do not patch live HelmRelease.

### `FluxKustomizationNotReady`

Investigation:

```bash
flux get ks -A
kubectl describe kustomization <name> -n flux-system
kubectl logs -n flux-system deploy/kustomize-controller --tail=100
```

Check:

- Dependency chain.
- SOPS decryption error.
- Missing CRD.
- Invalid YAML.
- Failed health check.

Behavior:

- Propose Git fix.
- Do not live patch.

### `CrashLoopBackOff`

Investigation:

```bash
kubectl get pod <pod> -n <namespace> -o wide
kubectl describe pod <pod> -n <namespace>
kubectl logs <pod> -n <namespace> --tail=100
kubectl logs <pod> -n <namespace> --previous --tail=100
```

Check:

- Recent Renovate PRs.
- ConfigMap/Secret refs, without reading Secret values.
- PVC mounts.
- Probes.
- Image tag changes.

Behavior:

- Propose PR or rollback.
- Only restart allowlisted deployments if explicitly enabled.

### `OOMKilled`

Investigation:

- Pod events.
- Container restart reason.
- Prometheus memory metrics.
- Current resource requests/limits in Helm values or manifests.

Behavior:

- Propose resource request/limit change PR.
- Avoid live patching.

### `ImagePullBackOff`

Investigation:

- Pod events.
- Image tag and registry.
- Renovate PR history.
- ImagePullSecrets refs, without reading secrets.

Behavior:

- Propose image tag fix or rollback PR.

### `PVCBlocked`

Investigation:

- PVC status.
- StorageClass.
- Rook/OpenEBS status.
- Events.

Behavior:

- Notify and suggest human action.
- Do not automatically modify PV/PVC/storage resources.

### `RookCephHealth`

Investigation:

- Rook-Ceph health status.
- OSD/MON/MGR health.
- Relevant events and logs.

Behavior:

- Notify only.
- No automatic repair.

### `CertManagerFailure`

Investigation:

- Certificate, CertificateRequest, Order, Challenge.
- cert-manager logs.
- DNS/HTTP challenge routing.
- Ingress/k8s-gateway context.

Behavior:

- Propose repo fix if routing/config issue.
- Do not mutate ClusterIssuer automatically.

### `IngressRouteFailure`

Investigation:

- Ingress resource.
- ingress-nginx controller logs.
- Service endpoints.
- k8s-gateway/DNS path.
- cert-manager certificate status.

Behavior:

- Propose repo fix.

### `NodePressureOrNotReady`

Investigation:

- Node conditions.
- Disk/memory pressure.
- kured/system-upgrade-controller activity.
- Recent events.

Behavior:

- Notify only by default.
- No autonomous reboots.

### `PlexGpuIssue`

Investigation:

- Plex pod scheduling.
- Intel GPU device plugin state.
- Node-feature-discovery labels.
- Device plugin logs.
- Plex pod mounts and env.

Behavior:

- Propose scheduling/resource/config PR if relevant.

## Renovate + AI workflow

Keep Renovate as the deterministic update system.

AI should help with:

- Reviewing Renovate PRs.
- Rendering/diffing Flux output where possible.
- Identifying chart breaking changes.
- Writing follow-up migration patches.
- Summarizing risk.

Desired workflow:

```text
Renovate opens PR
  -> CI validates YAML/schema/Flux if available
  -> AI reviews rendered diff and release notes
  -> AI comments or opens follow-up PR
  -> human merges
  -> Flux reconciles
```

High-value Renovate backlog areas to review with AI:

- kube-prometheus-stack major upgrade
- grafana major upgrade
- reloader major upgrade
- pod-gateway major upgrade
- ingress-nginx upgrade
- cloudflared upgrade
- VolSync upgrade
- node-feature-discovery upgrade
- kured upgrade
- Servarr major upgrades for Radarr/Prowlarr/etc.

## Suggested validation commands for Codex-generated changes

Codex should inspect the repo for existing task targets before inventing commands.

Likely useful commands to search for:

```bash
ls
find . -maxdepth 3 -iname '*taskfile*' -o -iname 'Taskfile.yaml'
rg 'flux-local|kubeconform|yamllint|helm template|sops|task ' .github .taskfiles scripts Makefile Taskfile.yaml
```

Possible validation commands, if available:

```bash
task --list
task flux:validate
task kubernetes:validate
flux diff kustomization cluster-apps --path ./kubernetes/apps
kubeconform -summary -strict <rendered manifests>
yamllint kubernetes
```

Do not assume these exact targets exist. Inspect first.

## Initial implementation sequence

Recommended order for Codex:

1. Add `AGENTS.md` safety instructions.
2. Add `docs/ai-cluster-management.md` describing architecture and rollout.
3. Add Robusta manifests, enrichment-only.
4. Document manual SOPS change needed to route Alertmanager to Robusta, or prepare a template/example without decrypting secrets.
5. Add HolmesGPT manifests in read-only mode.
6. Add K8sGPT Operator manifests with auto-remediation disabled.
7. Add runbook ConfigMaps or documentation for Holmes/Robusta.
8. Add optional workstation MCP documentation.
9. Add CI/validation if missing.
10. Later: enable GitHub PR creation for HolmesGPT after output quality is validated.

## Things not to do in first pass

- Do not enable K8sGPT auto-remediation.
- Do not add cluster-admin for HolmesGPT, Robusta, or K8sGPT.
- Do not add arbitrary command execution playbooks.
- Do not route every low-severity alert to expensive LLM calls.
- Do not mutate live cluster state from an AI agent.
- Do not migrate ingress-nginx to Gateway API as part of this initial AI management project.
- Do not migrate k3s to Talos as part of this initial AI management project.
- Do not alter SOPS encryption keys unless explicitly requested.
- Do not assume external report release numbers are current.

## Alert routing cost and noise control

Only route high-signal alerts to HolmesGPT initially.

Start with:

```text
severity=critical
```

Then optionally include:

```text
severity=warning AND alertname in allowlist
```

Avoid sending noisy, low-value alerts to LLMs. Robusta can enrich and route many alerts without invoking HolmesGPT.

Suggested LLM routing:

```text
Robusta enrichment for most alerts
HolmesGPT RCA for critical alerts or manually-triggered investigations
K8sGPT passive scan on interval with local/Ollama backend if desired
```

## Model/privacy guidance

Cloud LLMs may receive:

- Pod names.
- Namespace names.
- Internal hostnames/domains.
- Internal IPs.
- Image names and tags.
- Logs.
- Alert labels.

Mitigations:

- Mask Secrets everywhere supported.
- Do not send decrypted SOPS content.
- Bound log reads with `--tail=100` or similar.
- Prefer local/Ollama for passive K8sGPT scans if privacy is a concern.
- Use a cheaper/faster model for routine alert triage and a stronger model for manual deep RCA.

## Suggested “done” criteria for initial phase

Initial phase is complete when:

- `AGENTS.md` exists and codifies safe AI behavior.
- Robusta is deployed or manifests are ready, with enrichment-only posture.
- Alertmanager routing to Robusta is documented or implemented through SOPS safely.
- HolmesGPT is deployed or manifests are ready, read-only.
- K8sGPT is deployed or manifests are ready, with auto-remediation disabled.
- At least three runbooks exist or are documented: Flux failure, CrashLoopBackOff, OOMKilled.
- No AI tool has cluster-admin.
- No AI tool can read Kubernetes Secret values by default.
- No AI tool can mutate storage, nodes, Cilium, kube-vip, cert-manager issuers, or SOPS resources.
- The repo has a documented kill-switch / disable procedure for the AI tooling.

## Kill-switch / disable procedure to document

Codex should add a documented rollback path such as:

```text
1. Disable Alertmanager route to Robusta.
2. Suspend or remove HolmesGPT Kustomization.
3. Suspend or remove K8sGPT Kustomization.
4. Revoke model API token / GitHub token.
5. Reconcile Flux.
```

Example commands should be adapted to actual resource names:

```bash
flux suspend kustomization robusta -n flux-system
flux suspend kustomization holmesgpt -n flux-system
flux suspend kustomization k8sgpt -n flux-system
flux reconcile kustomization cluster-apps -n flux-system
```

## Codex prompt starter

Use this as the first message to Codex after loading the repo:

```text
You are working in the `jgilfoil/home-cluster` GitOps repository. This is a k3s homelab managed by Flux and Renovate. The goal is to add safe AI-assisted cluster management around Alertmanager notifications, RCA, and PR-based remediation.

Follow the attached handoff document. Important constraints:

- Git is the source of truth; prefer PRs over live cluster mutation.
- Do not decrypt, print, or request SOPS secrets or age private keys.
- Do not grant cluster-admin to AI tooling.
- Do not enable K8sGPT auto-remediation.
- Do not add destructive Robusta/Holmes playbooks in the first pass.
- Start by adding repo-level AI safety instructions and docs, then propose manifests for Robusta, HolmesGPT, and K8sGPT in read-only/enrichment-only mode.

First inspect the repository structure and existing Flux app conventions. Then propose a minimal PR plan before editing files.
```
