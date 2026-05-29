# Plex VolSync Restore Drill

Captured: 2026-05-29

This runbook verifies that Plex metadata can be restored from the existing
VolSync/restic backup into a scratch PVC without touching the live Plex
environment. The manual manifest lives at
`tests/manual/plex-volsync-restore-drill.yaml`, outside `kubernetes/`, so Flux
will not reconcile it unless a human intentionally applies it.

## Scope

The drill creates only:

- `ReplicationDestination/media/plex-restore-drill-20260529`
- `PersistentVolumeClaim/media/plex-restore-drill-20260529`
- `Pod/media/plex-restore-drill-20260529-inspect`

It must not create or modify a Plex `HelmRelease`, `Deployment`, `Service`,
`Ingress`, `LoadBalancer`, or the live `PersistentVolumeClaim/media/plex`.

## Guardrails

- Do not replace, patch, rename, or bind the live `plex` PVC.
- Do not create a `ReplicationSource` for the scratch PVC.
- Do not run restic `prune`, `forget`, `unlock`, or retention-changing
  operations.
- Do not print Secret values, restic environment variables, kubeconfigs, or
  SOPS content.
- Do not list sensitive media, library, or user filenames in notes or tickets.
- Do not start Plex against the restored data.
- Clean up only resources created by this drill.

## Apply The Drill

Run this only from a workstation that already has deliberate cluster access.
This repository change does not require live access.

```bash
kubectl apply -f tests/manual/plex-volsync-restore-drill.yaml
```

Watch the destination and scratch PVC without printing any Secret values:

```bash
kubectl -n media get replicationdestination plex-restore-drill-20260529
kubectl -n media describe replicationdestination plex-restore-drill-20260529
kubectl -n media get pvc plex-restore-drill-20260529
kubectl -n media get pod plex-restore-drill-20260529-inspect
```

Wait for the restore to complete and the inspection pod to be `Running` before
validation. If the restore fails, collect only non-secret status and event
output.

## Validate Without Starting Plex

Set the Plex metadata root in the inspection pod:

```bash
export POD=plex-restore-drill-20260529-inspect
export ROOT='/restore/Library/Application Support/Plex Media Server'
```

Check expected Plex metadata paths without dumping filenames:

```bash
kubectl -n media exec "$POD" -- sh -c '
set -eu
ROOT="/restore/Library/Application Support/Plex Media Server"
test -d "$ROOT"
test -d "$ROOT/Plug-in Support/Databases"
test -d "$ROOT/Metadata"
test -d "$ROOT/Media"
test -f "$ROOT/Plug-in Support/Databases/com.plexapp.plugins.library.db"
'
```

Count important database and metadata objects without printing names:

```bash
kubectl -n media exec "$POD" -- sh -c '
set -eu
ROOT="/restore/Library/Application Support/Plex Media Server"
printf "database_files="
find "$ROOT/Plug-in Support/Databases" -maxdepth 1 -type f -name "*.db*" | wc -l
printf "metadata_dirs="
find "$ROOT/Metadata" -mindepth 1 -maxdepth 2 -type d | wc -l
printf "media_dirs="
find "$ROOT/Media" -mindepth 1 -maxdepth 2 -type d | wc -l
'
```

If `sqlite3` is available in the inspection image or added manually to a
temporary debug image, run read-only database checks:

```bash
kubectl -n media exec "$POD" -- sh -c '
set -eu
DB="/restore/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$DB" "PRAGMA quick_check;"
  sqlite3 "$DB" "PRAGMA integrity_check;"
else
  echo "sqlite3 not available in inspection pod; skipped database check"
fi
'
```

Optional read-only inspection shell:

```bash
kubectl -n media exec -it plex-restore-drill-20260529-inspect -- sh
```

Inside the shell, keep inspection read-only and avoid commands that print
library or media filenames. Prefer `test`, `du -sh`, and bounded `find ... |
wc -l` checks.

## Cleanup

After recording the validation result, delete only the drill-created resources.
Delete the inspection pod before deleting the scratch PVC so Kubernetes does not
have to tear down a mounted volume out from under the pod:

```bash
kubectl -n media delete pod plex-restore-drill-20260529-inspect --ignore-not-found
kubectl -n media delete replicationdestination plex-restore-drill-20260529 --ignore-not-found
kubectl -n media delete pvc plex-restore-drill-20260529 --ignore-not-found
kubectl -n media get pvc,pod,replicationdestination \
  -l home-cluster.jgilfoil.dev/manual-only=true
```

Do not delete the live Plex PVC or any VolSync backup history.
