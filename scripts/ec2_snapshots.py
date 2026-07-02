#!/usr/bin/env python3
"""EBS snapshot lifecycle — backup, list, cleanup, restore. Lab 45.

The three scripts AWS on-call actually runs, in one file: snapshot the project's
volumes, prune old snapshots to a retention count, and rebuild a volume from a
snapshot. Only snapshots carrying our CreatedBy tag are ever touched, so the
cleanup can't eat snapshots made by other tools (ties into labs 07/33/40).

Usage:
    python scripts/ec2_snapshots.py backup                    # every volume tagged Project=devops-dojo
    python scripts/ec2_snapshots.py list
    python scripts/ec2_snapshots.py cleanup --retain 2        # keep 2 newest per volume
    python scripts/ec2_snapshots.py restore --snapshot-id snap-0abc... [--attach-to i-0def... --device /dev/sdf]

Exit codes: 0 = ok, 1 = nothing matched / AWS error, 2 = bad usage.
"""

import argparse
import sys

try:
    import boto3
except ImportError:
    sys.exit("boto3 is required: pip install boto3")

MARKER_TAG = "CreatedBy"
MARKER_VALUE = "ec2_snapshots.py"


def tag_filter(tag: str) -> dict:
    """'Project=devops-dojo' -> EC2 API filter dict."""
    key, _, value = tag.partition("=")
    if not value:
        sys.exit(f"--tag must look like Key=Value, got: {tag}")
    return {"Name": f"tag:{key}", "Values": [value]}


def name_of(resource: dict) -> str:
    return next((t["Value"] for t in resource.get("Tags", []) if t["Key"] == "Name"),
                resource.get("VolumeId", resource.get("SnapshotId", "?")))


def find_volumes(ec2, tag: str) -> list[dict]:
    vols: list[dict] = []
    for page in ec2.get_paginator("describe_volumes").paginate(Filters=[tag_filter(tag)]):
        vols.extend(page["Volumes"])
    return vols


def our_snapshots(ec2) -> list[dict]:
    """Only snapshots this script created (marker tag), only in our account."""
    snaps: list[dict] = []
    for page in ec2.get_paginator("describe_snapshots").paginate(
        OwnerIds=["self"],
        Filters=[{"Name": f"tag:{MARKER_TAG}", "Values": [MARKER_VALUE]}],
    ):
        snaps.extend(page["Snapshots"])
    return snaps


def cmd_backup(ec2, args) -> int:
    volumes = find_volumes(ec2, args.tag)
    if not volumes:
        print(f"no volumes match {args.tag} — is the lab-16 instance up?")
        return 1
    for vol in volumes:
        snap = ec2.create_snapshot(
            VolumeId=vol["VolumeId"],
            Description=f"{MARKER_VALUE} backup of {name_of(vol)}",
            TagSpecifications=[{
                "ResourceType": "snapshot",
                "Tags": [
                    {"Key": "Name", "Value": f"{name_of(vol)}-backup"},
                    {"Key": MARKER_TAG, "Value": MARKER_VALUE},
                ],
            }],
        )
        print(f"snapshot {snap['SnapshotId']} started for {vol['VolumeId']} ({name_of(vol)})")
    return 0


def cmd_list(ec2, _args) -> int:
    snaps = sorted(our_snapshots(ec2), key=lambda s: s["StartTime"], reverse=True)
    if not snaps:
        print("no snapshots created by this script")
        return 0
    print(f"{'SNAPSHOT':<24} {'VOLUME':<24} {'STARTED (UTC)':<20} {'STATE':<10} PROGRESS")
    for s in snaps:
        print(f"{s['SnapshotId']:<24} {s['VolumeId']:<24} "
              f"{s['StartTime']:%Y-%m-%d %H:%M:%S}  {s['State']:<10} {s.get('Progress', '')}")
    return 0


def cmd_cleanup(ec2, args) -> int:
    by_volume: dict[str, list[dict]] = {}
    for snap in our_snapshots(ec2):
        by_volume.setdefault(snap["VolumeId"], []).append(snap)

    deleted = 0
    for volume_id, snaps in by_volume.items():
        snaps.sort(key=lambda s: s["StartTime"], reverse=True)  # newest first
        for snap in snaps[args.retain:]:
            ec2.delete_snapshot(SnapshotId=snap["SnapshotId"])
            print(f"deleted {snap['SnapshotId']} of {volume_id} ({snap['StartTime']:%Y-%m-%d %H:%M})")
            deleted += 1
    print(f"kept {args.retain} newest per volume, deleted {deleted}")
    return 0


def cmd_restore(ec2, args) -> int:
    snap = ec2.describe_snapshots(SnapshotIds=[args.snapshot_id])["Snapshots"][0]

    az = args.az
    if not az and args.attach_to:
        # a volume can only attach within the instance's AZ
        inst = ec2.describe_instances(InstanceIds=[args.attach_to])
        az = inst["Reservations"][0]["Instances"][0]["Placement"]["AvailabilityZone"]
    if not az:
        sys.exit("--az is required (or --attach-to, to take the instance's AZ)")

    vol = ec2.create_volume(
        SnapshotId=args.snapshot_id,
        AvailabilityZone=az,
        VolumeType="gp3",
        TagSpecifications=[{
            "ResourceType": "volume",
            "Tags": [
                {"Key": "Name", "Value": f"restored-{args.snapshot_id}"},
                {"Key": MARKER_TAG, "Value": MARKER_VALUE},
            ],
        }],
    )
    volume_id = vol["VolumeId"]
    print(f"volume {volume_id} creating in {az} from {args.snapshot_id} "
          f"(snapshot of {snap['VolumeId']})")

    if args.attach_to:
        ec2.get_waiter("volume_available").wait(VolumeIds=[volume_id])
        ec2.attach_volume(VolumeId=volume_id, InstanceId=args.attach_to, Device=args.device)
        print(f"attached to {args.attach_to} as {args.device} — on the box: lsblk, then mount")
    else:
        print(f"attach it yourself: aws ec2 attach-volume --volume-id {volume_id} "
              f"--instance-id i-... --device /dev/sdf")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--region", default=None, help="AWS region (default: your profile's)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_backup = sub.add_parser("backup", help="snapshot every volume matching --tag")
    p_backup.add_argument("--tag", default="Project=devops-dojo", help="Key=Value volume filter")
    p_backup.set_defaults(func=cmd_backup)

    p_list = sub.add_parser("list", help="list snapshots created by this script")
    p_list.set_defaults(func=cmd_list)

    p_clean = sub.add_parser("cleanup", help="keep the N newest snapshots per volume")
    p_clean.add_argument("--retain", type=int, default=2, help="snapshots to keep per volume")
    p_clean.set_defaults(func=cmd_cleanup)

    p_restore = sub.add_parser("restore", help="create (and optionally attach) a volume from a snapshot")
    p_restore.add_argument("--snapshot-id", required=True)
    p_restore.add_argument("--az", default=None, help="AZ for the new volume, e.g. eu-north-1a")
    p_restore.add_argument("--attach-to", default=None, help="instance id to attach the volume to")
    p_restore.add_argument("--device", default="/dev/sdf", help="device name when attaching")
    p_restore.set_defaults(func=cmd_restore)

    args = parser.parse_args()
    ec2 = boto3.client("ec2", region_name=args.region)
    return args.func(ec2, args)


if __name__ == "__main__":
    sys.exit(main())
