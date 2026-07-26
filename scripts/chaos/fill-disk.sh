#!/usr/bin/env bash
# fill-disk.sh — lab 54 drill: fill the disk in the way that is actually hard to find.
#
# It writes a large file and then DELETES it while a process still holds it open. The
# space stays allocated (the inode is only freed when the last file descriptor closes),
# so `df` reports the disk as full while `du` finds nothing. That gap is the whole drill:
# you need `lsof +L1` (or /proc/*/fd) to see it.
#
# Recover: ./heal.sh, or kill the holder PID this script prints.
#
# Run on a THROWAWAY box (the lab 16/18 EC2 instance) or in the lab's container — not on
# your workstation.
set -euo pipefail

TARGET_DIR="${TARGET_DIR:-/var/tmp}"
SIZE_MB="${SIZE_MB:-2048}"
HOLD_SECONDS="${HOLD_SECONDS:-1800}"

command -v fallocate >/dev/null || { echo "needs fallocate (util-linux)" >&2; exit 1; }

avail_mb=$(df -Pm "$TARGET_DIR" | awk 'NR==2 {print $4}')
if (( avail_mb < SIZE_MB + 512 )); then
    echo "Only ${avail_mb}MB free in $TARGET_DIR; shrinking the hog to leave 512MB headroom." >&2
    SIZE_MB=$(( avail_mb - 512 ))
    (( SIZE_MB > 0 )) || { echo "Not enough space to run the drill safely." >&2; exit 1; }
fi

hog="$TARGET_DIR/.dojo-chaos-hog.$$"
fallocate -l "${SIZE_MB}M" "$hog"

# Open the file, unlink it, then sit on the descriptor — all inside the background
# subshell so there is no window where the file exists unopened. Space stays allocated;
# the name does not.
( exec 9<"$hog"; rm -f "$hog"; sleep "$HOLD_SECONDS" ) &
holder=$!

cat <<EOF
Injected: ${SIZE_MB}MB is allocated to a deleted-but-open file.
Holder PID: $holder  (dies on its own after ${HOLD_SECONDS}s)

Start diagnosing. Expect 'df -h' and 'du -xh' to disagree — that disagreement is the clue.
Recover: kill $holder     (or ./heal.sh)
EOF
