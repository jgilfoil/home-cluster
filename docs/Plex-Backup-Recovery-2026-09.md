# Plex backup recovery — September 2026

Plex backups are being resumed after the node outage. Other suspended backup
jobs and monitoring are outside this change and remain paused.

## Protect existing backups

The Plex app overlays the shared VolSync template with `retain.last: unlimited`
and `pruneIntervalDays: 36500`. The daily `0 10 * * *` schedule is unchanged
(04:00 MDT / 03:00 MST). No other app inherits this overlay.

Restic's `--keep-last unlimited` preserves every snapshot. VolSync 0.12.1
defaults to `--keep-last 1` if retention is omitted or empty, so removing the
policy is **not** safe. This version has no prune-disable switch: 36,500 days
defers pruning for approximately 100 years from the last prune, within Go's
duration range. Neither zero nor a negative interval disables pruning.

This is a recovery hold, not a storage-bounded long-term policy. Repository
storage can grow. Changing back to a finite retention policy or allowing pruning
requires a separate owner-approved decision; do not automatically revert this
overlay as part of cleanup.

References: [VolSync 0.12.1 controller](https://github.com/backube/volsync/blob/v0.12.1/controllers/mover/restic/mover.go)
and [Restic retention documentation](https://restic.readthedocs.io/en/stable/060_forget.html).
The installed mover image's `restic forget --help` also confirms `unlimited`.

## Recovery checks

Before reconciliation, the Plex repository contained ten snapshots, newest
`727bed6e` from September 9. The suspended `media/volsync-src-plex` job contained
the old finite retention options and `backup prune` actions. Do not simply
unsuspend that old job.

VolSync replaces its Job when a pod-template update encounters immutable fields.
The Plex source, cache, and staging PVCs are not owned by the Job. Allow the
controller to replace the idle suspended Job with the protected settings, and
verify the replacement uses `backup` only and `--keep-last unlimited`.

The pending synchronization uses a September 10 volume snapshot. Completing it
preserves that recovery point, but does not protect current Plex data. After it
finishes, request a one-off manual synchronization through the Plex
ReplicationSource, verify that it captures a new volume snapshot, then remove
the one-off manual trigger so the Git-managed daily schedule continues.

Verify the successful VolSync status and new Restic snapshot, that all ten
pre-recovery Restic snapshot IDs remain present, and that the repository lock is
released. Preserve the application PVCs, existing backup snapshots, and the
owner's `restic-shell` troubleshooting pod. VolSync may clean up its own
temporary per-run staging clone/snapshot after a successful backup as part of
its normal lifecycle; do not manually delete storage resources.
