# VolSync / Restic Locks (Stale Lock Cleanup)

This cluster uses **VolSync** with **restic** for backups. Occasionally backups can fail because the restic repository is left with a **stale lock** (e.g., a mover pod crashed or was deleted mid-operation).

## When to use this

Use this procedure when a VolSync restic job is failing with log output like:

```text
repo already locked, waiting up to 0s for the lock
unable to create lock in backend: repository is already locked by PID 32 on volsync-src-plex-nzlv6 by root (UID 0, GID 0)
lock was created at 2025-12-13 10:24:46 (189h37m14.500688624s ago)
the `unlock` command can be used to remove stale locks
```

**Before unlocking**, make sure there is no currently-running restic/VolSync job legitimately using the repository. If another mover pod is actively backing up/restoring, do not remove its lock.

## How to clear a stale lock

We use the `tests/storage/restic-cli.yaml` pod as a simple “restic shell” with the correct repository credentials injected from a Kubernetes Secret.

### 1) Point the restic shell at the right Secret

Edit the Secret reference in `tests/storage/restic-cli.yaml`:

- Set `metadata.namespace` to the namespace that holds the Secret.
- Set `spec.containers[0].envFrom[0].secretRef.name` to the correct restic secret (for VolSync, this is typically `${APP}-restic-secret`).

### 2) Apply the manifest

```bash
kubectl apply -f tests/storage/restic-cli.yaml
```

### 3) Exec into the pod and unlock

```bash
kubectl -n <namespace> exec -it restic-shell -- sh
```

Inside the shell:

```bash
restic unlock
```

If `restic unlock` does not clear the issue and you are **certain** no other job is using the repo, you can force-remove all locks:

```bash
restic unlock --remove-all
```

### 4) Cleanup

```bash
kubectl -n <namespace> delete pod restic-shell
```

## Notes

- `restic unlock` is the safe/default choice: it removes **stale** locks.
- `restic unlock --remove-all` is more aggressive: use it only when you’ve confirmed no other restic process is running against that repository.


