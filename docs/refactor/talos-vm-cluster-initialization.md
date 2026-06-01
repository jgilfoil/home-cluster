# Talos VM Cluster Initialization

Captured: 2026-06-01

This runbook records the minimal initialization path for the disposable Hyper-V
Talos VM lab. It is intentionally scoped to proving that a single-node Talos
cluster can come up cleanly; it is not the target production bootstrap plan.

## Scope And Guardrails

Use this only for the disposable Talos VM lab.

- Keep generated Talos configs and kubeconfigs under `.private/talos-vm-lab/`.
- Do not commit Talos secrets, talosconfig, kubeconfig, or machine configs.
- Do not point Flux at the full production GitOps tree from this VM during the
  first smoke test.
- Do not treat the default Talos CNI as the production design. The generated
  smoke-test config used kube-flannel and kube-proxy; the target homelab design
  still expects a deliberate Cilium decision.

## Prerequisites

- Talos VM is reachable on the LAN in either maintenance mode or configured mode.
- `talosctl` is installed locally and matches the VM Talos version closely.
- `.private/talos-vm-lab/controlplane.yaml` validates successfully.
- `.private/talos-vm-lab/talosconfig` exists after config generation.

Validate the generated control-plane config without printing secrets:

```bash
talosctl validate \
  --config .private/talos-vm-lab/controlplane.yaml \
  --mode metal \
  --strict
```

Expected result:

```text
.private/talos-vm-lab/controlplane.yaml is valid for metal mode
```

## If The VM Is Still In Maintenance Mode

Maintenance-mode discovery is safe and should be done before applying config:

```bash
VM_IP=192.168.1.142

talosctl --nodes "$VM_IP" --endpoints "$VM_IP" version --insecure
talosctl --nodes "$VM_IP" --endpoints "$VM_IP" get links --insecure
talosctl --nodes "$VM_IP" --endpoints "$VM_IP" get addresses --insecure
talosctl --nodes "$VM_IP" --endpoints "$VM_IP" get disks --insecure
```

Only apply config after confirming the VM IP, primary NIC, and install disk are
correct for the disposable VM:

```bash
VM_IP=192.168.1.142

talosctl apply-config --insecure \
  --nodes "$VM_IP" \
  --file .private/talos-vm-lab/controlplane.yaml
```

This installs/configures Talos on the VM disk referenced by the machine config.
Do not run it against real cluster nodes from this lab runbook.

## Bootstrap The Single-Node Control Plane

Once the secure Talos API is available with the generated `talosconfig`,
initialize etcd and the control plane:

```bash
VM_IP=192.168.1.142

talosctl --talosconfig .private/talos-vm-lab/talosconfig \
  --nodes "$VM_IP" \
  --endpoints "$VM_IP" \
  bootstrap
```

Then wait for Talos and Kubernetes health:

```bash
talosctl --talosconfig .private/talos-vm-lab/talosconfig \
  --nodes "$VM_IP" \
  --endpoints "$VM_IP" \
  health --wait-timeout 10m
```

A small-memory VM may briefly report a memory requirement warning. If it clears
and the remaining health checks pass, the cluster is usable for a smoke test.
For future repeatability, size the VM comfortably above the minimum rather than
running near the lower bound.

## Export A Lab Kubeconfig

Write the Kubernetes kubeconfig under `.private/`, never over the production
repo-root kubeconfig:

```bash
VM_IP=192.168.1.142

talosctl --talosconfig .private/talos-vm-lab/talosconfig \
  --nodes "$VM_IP" \
  --endpoints "$VM_IP" \
  kubeconfig .private/talos-vm-lab/kubeconfig --force

chmod 600 .private/talos-vm-lab/kubeconfig
```

Verify the lab cluster:

```bash
KUBECONFIG=.private/talos-vm-lab/kubeconfig kubectl get nodes -o wide
KUBECONFIG=.private/talos-vm-lab/kubeconfig kubectl get pods -A -o wide
```

Observed successful smoke-test shape:

```text
Talos: v1.13.3
Kubernetes: v1.36.1
Node: talos-j1y-a90 Ready control-plane 192.168.1.142
Core pods: coredns, kube-apiserver, kube-controller-manager, kube-scheduler,
           kube-flannel, and kube-proxy Running
```

## Interpretation

This proves that the disposable Hyper-V VM can initialize as a single-node Talos
cluster. It does not prove the production rebuild design yet.

Still unresolved for the real rebuild:

- Cilium configuration with the intended kube-proxy replacement posture.
- Rook/Ceph behavior on real multi-node hardware.
- VolSync restore behavior against the actual backup endpoint.
- Production ingress, DNS, Cloudflare tunnel, and LAN routing behavior.
- Version selection for the real Talos/Kubernetes target.

The next useful lab step is either a minimal Cilium install smoke test or a
small VolSync/restic restore-path test, depending on which risk we want to retire
first.
