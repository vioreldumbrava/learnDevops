#!/usr/bin/env python3
"""Report EC2 instances and EBS volumes that are missing required tags. Lab 37.

Untagged resources are how AWS bills surprise you: nobody knows what they are, so
nobody dares delete them (ties into labs 16/40). Run it after any Terraform work.
Exit codes: 0 = all tagged, 1 = offenders found (usable as a CI gate), 2 = bad usage.

Usage:
    python scripts/aws_untagged_report.py
    python scripts/aws_untagged_report.py --region eu-central-1 --required Name project owner
"""

import argparse
import sys

try:
    import boto3
except ImportError:
    sys.exit("boto3 is required: pip install boto3")


def missing_tags(tags: list | None, required: set[str]) -> set[str]:
    present = {t["Key"] for t in (tags or [])}
    return required - present


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default=None, help="AWS region (default: your profile's)")
    parser.add_argument(
        "--required", nargs="+", default=["Name", "project"],
        help="tag keys every resource must carry (default: Name project)",
    )
    args = parser.parse_args()
    required = set(args.required)

    ec2 = boto3.client("ec2", region_name=args.region)
    offenders: list[tuple[str, str, str]] = []  # (type, id, missing keys)

    # paginators handle >1000 resources; .describe_* alone silently truncates
    for page in ec2.get_paginator("describe_instances").paginate(
        Filters=[{"Name": "instance-state-name",
                  "Values": ["pending", "running", "stopping", "stopped"]}]
    ):
        for reservation in page["Reservations"]:
            for inst in reservation["Instances"]:
                gap = missing_tags(inst.get("Tags"), required)
                if gap:
                    offenders.append(("instance", inst["InstanceId"], ", ".join(sorted(gap))))

    for page in ec2.get_paginator("describe_volumes").paginate():
        for vol in page["Volumes"]:
            gap = missing_tags(vol.get("Tags"), required)
            if gap:
                offenders.append(("volume", vol["VolumeId"], ", ".join(sorted(gap))))

    if not offenders:
        print(f"OK: every instance/volume carries {sorted(required)}")
        return 0

    print(f"{len(offenders)} resource(s) missing required tags {sorted(required)}:\n")
    print(f"{'TYPE':<10} {'ID':<22} MISSING")
    for rtype, rid, gap in offenders:
        print(f"{rtype:<10} {rid:<22} {gap}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
