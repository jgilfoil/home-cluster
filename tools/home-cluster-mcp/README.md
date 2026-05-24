# Home Cluster MCP

Local stdio MCP server for Codex-assisted troubleshooting of this GitOps
cluster. It exposes read-focused Kubernetes and Flux tools, optional Prometheus
queries, and tightly constrained non-interactive pod exec for app namespaces.

## Install

```bash
task mcp:install
```

## Configure

1. Apply the GitOps RBAC in `kubernetes/apps/default/codex-mcp-access`.
2. Mint a short-lived kubeconfig:

   ```bash
   task mcp:kubeconfig
   ```

3. Copy `.codex/config.toml.example` into your Codex config and adjust absolute
   paths if needed.

## Run

```bash
task mcp:run
```

Codex should point at the repo venv entrypoint:

```toml
command = "/home/jason/repos/home-cluster/.venv/bin/home-cluster-mcp"
```

The server uses stdio for MCP protocol traffic. Audit details for `pod_exec`
are returned in the tool result and also logged on stderr so stdout remains
valid JSON-RPC for the MCP transport.
