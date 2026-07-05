# Talos Codex MCP Access Bootstrap

This runbook creates the limited Kubernetes access that a remote Codex/MCP-style
agent can use against the disposable Talos lab cluster. It is intentionally a
manual bootstrap step, not a Flux-managed production change.

Companion manifest:

```text
tests/manual/talos-codex-mcp-access.yaml
```

## What the manifest creates

- `default/codex-mcp` ServiceAccount.
- `codex-mcp-read` ClusterRole and ClusterRoleBinding.
- A durable ServiceAccount token Secret named `default/codex-mcp-token`.
- Narrow `pods/exec` access in the `default` namespace only.

It does **not** grant access to Kubernetes Secrets, SOPS data, node mutation,
PVC mutation, Flux mutation, Rook mutation, or cluster-admin.

The ClusterRole includes read access for common core resources plus optional CRD
families used during the rebuild/restore investigation: Flux, cert-manager,
Rook/Ceph, Cilium, VolSync, and VolumeSnapshot resources. RBAC can safely refer
to API groups that are not installed yet; those rules become useful once the
corresponding CRDs exist.

## Where the Talos kubeconfig comes from

There are two different config files involved:

- `talosconfig`: Talos API client config, generated when the Talos machine
  configs are generated. This talks to the Talos API on the node.
- `kubeconfig`: Kubernetes API client config, exported from Talos **after** the
  control plane has been bootstrapped. This is what `kubectl apply` uses.

The Kubernetes kubeconfig does not come from the Talos ISO and should not be
copied from the current k3s cluster. Generate/export it with `talosctl` from the
Talos lab control plane.

From the repo root, for the existing disposable Hyper-V lab convention:

```bash
VM_IP=192.168.1.142
TALOSCONFIG=.private/talos-vm-lab/talosconfig
ADMIN_KUBECONFIG=.private/talos-vm-lab/kubeconfig

talosctl --talosconfig "$TALOSCONFIG" \
  --nodes "$VM_IP" \
  --endpoints "$VM_IP" \
  kubeconfig "$ADMIN_KUBECONFIG" --force

chmod 600 "$ADMIN_KUBECONFIG"
KUBECONFIG="$ADMIN_KUBECONFIG" kubectl get nodes -o wide
```

If the cluster has not been bootstrapped yet, export the kubeconfig only after:

```bash
talosctl --talosconfig "$TALOSCONFIG" \
  --nodes "$VM_IP" \
  --endpoints "$VM_IP" \
  bootstrap

talosctl --talosconfig "$TALOSCONFIG" \
  --nodes "$VM_IP" \
  --endpoints "$VM_IP" \
  health --wait-timeout 10m
```

If this is a different Talos lab, replace `VM_IP` and the local paths with the
Talos endpoint and talosconfig path for that lab.

## Apply the access manifest

From the repo root:

```bash
ADMIN_KUBECONFIG=.private/talos-vm-lab/kubeconfig

KUBECONFIG="$ADMIN_KUBECONFIG" \
  kubectl apply -f tests/manual/talos-codex-mcp-access.yaml
```

Verify the ServiceAccount and RBAC boundary with the admin kubeconfig:

```bash
KUBECONFIG="$ADMIN_KUBECONFIG" kubectl -n default get sa codex-mcp
KUBECONFIG="$ADMIN_KUBECONFIG" kubectl auth can-i get pods -A \
  --as=system:serviceaccount:default:codex-mcp
KUBECONFIG="$ADMIN_KUBECONFIG" kubectl auth can-i get secrets -A \
  --as=system:serviceaccount:default:codex-mcp
KUBECONFIG="$ADMIN_KUBECONFIG" kubectl auth can-i create pods \
  --subresource=exec -n default \
  --as=system:serviceaccount:default:codex-mcp
```

Expected shape:

```text
get pods -A: yes
get secrets -A: no
create pods/exec in default: yes
```

## Create the restricted kubeconfig for the agent VM

Use the admin kubeconfig once to copy the durable ServiceAccount token into a
local ignored kubeconfig. The command below does not print the token.

```bash
export ADMIN_KUBECONFIG=.private/talos-vm-lab/kubeconfig
export MCP_KUBECONFIG=.private/talos-vm-lab/codex-mcp.kubeconfig

mkdir -p "$(dirname "$MCP_KUBECONFIG")"
python3 - <<'PY'
import base64
import json
import os
import pathlib
import stat
import subprocess

admin = os.environ.get("ADMIN_KUBECONFIG", ".private/talos-vm-lab/kubeconfig")
out = pathlib.Path(os.environ.get("MCP_KUBECONFIG", ".private/talos-vm-lab/codex-mcp.kubeconfig"))

cfg_raw = subprocess.check_output([
    "kubectl", "--kubeconfig", admin,
    "config", "view", "--raw", "--minify", "-o", "json",
], text=True)
cfg = json.loads(cfg_raw)
cluster = cfg["clusters"][0]["cluster"]
server = cluster["server"]
ca_data = cluster["certificate-authority-data"]

secret_raw = subprocess.check_output([
    "kubectl", "--kubeconfig", admin,
    "-n", "default", "get", "secret", "codex-mcp-token", "-o", "json",
], text=True)
secret = json.loads(secret_raw)
token = base64.b64decode(secret["data"]["token"]).decode()

out.write_text(f"""apiVersion: v1
kind: Config
clusters:
  - name: talos-lab
    cluster:
      server: {json.dumps(server)}
      certificate-authority-data: {json.dumps(ca_data)}
users:
  - name: codex-mcp
    user:
      token: {json.dumps(token)}
contexts:
  - name: codex-mcp@talos-lab
    context:
      cluster: talos-lab
      user: codex-mcp
      namespace: default
current-context: codex-mcp@talos-lab
""")
out.chmod(stat.S_IRUSR | stat.S_IWUSR)
print(f"wrote {out}")
PY
```

Verify the restricted kubeconfig directly:

```bash
KUBECONFIG="$MCP_KUBECONFIG" kubectl auth can-i get pods -A
KUBECONFIG="$MCP_KUBECONFIG" kubectl auth can-i get secrets -A
KUBECONFIG="$MCP_KUBECONFIG" kubectl auth can-i create pods --subresource=exec -n default
```

Expected:

```text
yes
no
yes
```

Once the restricted kubeconfig is copied to the remote agent VM and verified,
remove the admin kubeconfig from places where the agent can read it.

## Short-lived alternative

If you want a temporary token instead of the durable Secret, do not read
`codex-mcp-token`. Mint a bounded token and write the same kubeconfig shape:

```bash
ADMIN_KUBECONFIG=.private/talos-vm-lab/kubeconfig
KUBECONFIG="$ADMIN_KUBECONFIG" \
  kubectl -n default create token codex-mcp --duration=24h
```

Use that token only in a local ignored kubeconfig, and rotate it by creating a
new token when needed.

## Cleanup

For a disposable lab cluster:

```bash
KUBECONFIG=.private/talos-vm-lab/kubeconfig \
  kubectl delete -f tests/manual/talos-codex-mcp-access.yaml --ignore-not-found

rm -f .private/talos-vm-lab/codex-mcp.kubeconfig
```
