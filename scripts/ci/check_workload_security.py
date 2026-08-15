#!/usr/bin/env python3
"""Gate high-risk Kubernetes workload settings in rendered Helm manifests."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Iterable

import yaml


WORKLOAD_PATHS: dict[str, tuple[str, ...]] = {
    "Pod": ("spec",),
    "Deployment": ("spec", "template", "spec"),
    "StatefulSet": ("spec", "template", "spec"),
    "DaemonSet": ("spec", "template", "spec"),
    "Job": ("spec", "template", "spec"),
    "CronJob": ("spec", "jobTemplate", "spec", "template", "spec"),
    "ReplicaSet": ("spec", "template", "spec"),
    "Rollout": ("spec", "template", "spec"),
}


def nested(document: dict[str, Any], path: Iterable[str]) -> dict[str, Any]:
    value: Any = document
    for key in path:
        if not isinstance(value, dict):
            return {}
        value = value.get(key, {})
    return value if isinstance(value, dict) else {}


def inspect_document(document: Any, source: Path) -> list[str]:
    if not isinstance(document, dict) or document.get("kind") not in WORKLOAD_PATHS:
        return []

    kind = str(document["kind"])
    name = str(document.get("metadata", {}).get("name", "<unnamed>"))
    identity = f"{source}:{kind}/{name}"
    pod = nested(document, WORKLOAD_PATHS[kind])
    failures: list[str] = []

    for field in ("hostNetwork", "hostPID", "hostIPC"):
        if pod.get(field) is True:
            failures.append(f"{identity}: {field}: true is forbidden")

    pod_context = pod.get("securityContext", {}) or {}
    if pod_context.get("runAsNonRoot") is not True:
        failures.append(f"{identity}: pod securityContext.runAsNonRoot must be true")
    if nested(pod_context, ("seccompProfile",)).get("type") != "RuntimeDefault":
        failures.append(
            f"{identity}: pod securityContext.seccompProfile.type must be RuntimeDefault"
        )

    for volume in pod.get("volumes", []) or []:
        if isinstance(volume, dict) and "hostPath" in volume:
            failures.append(f"{identity}: hostPath volume {volume.get('name', '<unnamed>')} is forbidden")

    containers = [*(pod.get("initContainers", []) or []), *(pod.get("containers", []) or [])]
    for container in containers:
        if not isinstance(container, dict):
            continue
        container_name = container.get("name", "<unnamed>")
        context = container.get("securityContext", {}) or {}
        effective_user = context.get("runAsUser", pod_context.get("runAsUser"))
        if (
            isinstance(effective_user, bool)
            or not isinstance(effective_user, int)
            or effective_user <= 0
        ):
            failures.append(
                f"{identity}:{container_name}: runAsUser must resolve to a positive numeric UID"
            )
        effective_group = context.get("runAsGroup", pod_context.get("runAsGroup"))
        if (
            isinstance(effective_group, bool)
            or not isinstance(effective_group, int)
            or effective_group <= 0
        ):
            failures.append(
                f"{identity}:{container_name}: runAsGroup must resolve to a positive numeric GID"
            )
        if context.get("privileged") is True:
            failures.append(f"{identity}:{container_name}: privileged containers are forbidden")
        if context.get("allowPrivilegeEscalation") is not False:
            failures.append(
                f"{identity}:{container_name}: allowPrivilegeEscalation must be false"
            )
        if context.get("readOnlyRootFilesystem") is not True:
            failures.append(
                f"{identity}:{container_name}: readOnlyRootFilesystem must be true"
            )

        capabilities = context.get("capabilities", {}) or {}
        dropped = {str(item).upper() for item in capabilities.get("drop", []) or []}
        if "ALL" not in dropped:
            failures.append(f"{identity}:{container_name}: capabilities.drop must include ALL")
        added = {str(item).upper() for item in capabilities.get("add", []) or []}
        dangerous = added.intersection({"ALL", "SYS_ADMIN", "NET_ADMIN", "SYS_PTRACE"})
        if dangerous:
            failures.append(f"{identity}:{container_name}: dangerous capabilities: {sorted(dangerous)}")

        image = str(container.get("image", ""))
        final_component = image.rsplit("/", 1)[-1]
        if not image or "@sha256:" not in image and (":" not in final_component or image.endswith(":latest")):
            failures.append(f"{identity}:{container_name}: image must use an explicit non-latest tag or digest")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifests", nargs="+", type=Path)
    args = parser.parse_args()

    failures: list[str] = []
    for manifest in args.manifests:
        with manifest.open(encoding="utf-8") as handle:
            for document in yaml.safe_load_all(handle):
                failures.extend(inspect_document(document, manifest))

    if failures:
        print("High-risk Kubernetes workload settings found:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1

    print(f"Checked {len(args.manifests)} rendered manifest set(s) for high-risk workload settings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
