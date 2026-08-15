#!/usr/bin/env python3
"""Validate and deterministically generate curriculum-derived artifacts.

The JSON manifest is the source of truth.  The database migration and the marked
roadmap table in docs/CURRICULUM.md must be generated from it; CI runs this file
with ``--check`` and rejects drift.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "curriculum" / "manifest.json"
CURRICULUM_PATH = ROOT / "docs" / "CURRICULUM.md"
DRILLS_PATH = ROOT / "docs" / "DRILLS.md"
MIGRATION_UP_PATH = ROOT / "db" / "migrations" / "000005_curriculum_metadata.up.sql"
MIGRATION_DOWN_PATH = ROOT / "db" / "migrations" / "000005_curriculum_metadata.down.sql"

ROADMAP_BEGIN = "<!-- BEGIN GENERATED CURRICULUM ROADMAP -->"
ROADMAP_END = "<!-- END GENERATED CURRICULUM ROADMAP -->"

PUBLIC_METADATA_FIELDS = {
    "tier",
    "tracks",
    "requires",
    "effort_minutes",
    "cost_class",
    "drill_required",
}
REQUIRED_FIELDS = {
    "id",
    "lab_no",
    "title",
    "topic",
    "maps_to",
    "milestone",
    "doc_path",
    "summary",
    "sort_order",
    *PUBLIC_METADATA_FIELDS,
    "shell",
    "tools",
    "account",
    "teardown_required",
    "teardown",
}
DB_FIELDS = (
    "id",
    "lab_no",
    "title",
    "topic",
    "maps_to",
    "milestone",
    "doc_path",
    "summary",
    "sort_order",
    "tier",
    "tracks",
    "requires",
    "effort_minutes",
    "cost_class",
    "drill_required",
)
TIERS = {"core", "specialization", "elective"}
TRACKS = {"common-core", "platform-cka", "sre", "elective"}
COST_CLASSES = {"free", "local", "cloud-low", "cloud-high"}

COMMON_CORE = [
    "00-prerequisites",
    "38-git-workflows",
    "01-docker-basics",
    "02-containerize-api",
    "03-containerize-frontend",
    "04-docker-compose",
    "05-dev-prod-compose",
    "06-database-migrations",
    "07-backup-restore",
    "08-health-checks",
    "37-scripting-automation",
    "54-linux-server-ops",
    "10-monitoring",
    "13-image-registry",
    "15-cicd",
    "16-terraform",
    "39-terraform-state-and-modules",
    "40-aws-core-services",
    "17-ansible",
    "18-deploy-https",
    "22-kubernetes",
    "23-helm",
    "26-secrets-management",
    "35-incident-response",
    "25-capstone-eks-gitops",
]
PLATFORM_BRANCH = [
    "27-k8s-rbac",
    "28-k8s-network-policies",
    "52-k8s-storage",
    "53-k8s-scheduling",
    "48-cka-exam-readiness",
]
SRE_BRANCH = [
    "11-logging",
    "12-tracing-and-alerting",
    "55-postgres-operations",
    "56-slo-and-error-budgets",
]


class CurriculumError(ValueError):
    """A manifest or generated-artifact integrity error."""


def load_manifest() -> dict[str, Any]:
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CurriculumError(f"cannot read {MANIFEST_PATH.relative_to(ROOT)}: {exc}") from exc
    if data.get("schema_version") != 1:
        raise CurriculumError("manifest schema_version must be 1")
    if not isinstance(data.get("steps"), list):
        raise CurriculumError("manifest steps must be an array")
    return data


def validate_manifest(data: dict[str, Any]) -> list[dict[str, Any]]:
    steps = data["steps"]
    errors: list[str] = []
    ids: list[str] = []
    lab_numbers: list[int] = []
    sort_orders: list[int] = []

    for index, step in enumerate(steps):
        where = f"steps[{index}]"
        if not isinstance(step, dict):
            errors.append(f"{where} must be an object")
            continue
        missing = sorted(REQUIRED_FIELDS - step.keys())
        if missing:
            errors.append(f"{where} is missing: {', '.join(missing)}")
            continue

        step_id = step["id"]
        lab_no = step["lab_no"]
        order = step["sort_order"]
        ids.append(step_id)
        lab_numbers.append(lab_no)
        sort_orders.append(order)

        if not isinstance(step_id, str) or not re.fullmatch(r"\d{2}-[a-z0-9-]+", step_id):
            errors.append(f"{where}.id must match NN-kebab-case")
        if not isinstance(lab_no, int) or not 0 <= lab_no <= 56:
            errors.append(f"{where}.lab_no must be an integer from 0 through 56")
        elif isinstance(step_id, str) and step_id[:2] != f"{lab_no:02d}":
            errors.append(f"{where}.id prefix does not match lab_no")
        if step["doc_path"] != f"labs/{step_id}/":
            errors.append(f"{where}.doc_path must be labs/{step_id}/")
        if step["tier"] not in TIERS:
            errors.append(f"{where}.tier must be one of {sorted(TIERS)}")
        if not isinstance(step["tracks"], list) or not step["tracks"]:
            errors.append(f"{where}.tracks must be a non-empty array")
        elif any(track not in TRACKS for track in step["tracks"]):
            errors.append(f"{where}.tracks contains an unknown track")
        if not isinstance(step["requires"], list) or any(
            not isinstance(item, str) for item in step["requires"]
        ):
            errors.append(f"{where}.requires must be an array of step IDs")
        if not isinstance(step["effort_minutes"], int) or step["effort_minutes"] <= 0:
            errors.append(f"{where}.effort_minutes must be a positive integer")
        if step["cost_class"] not in COST_CLASSES:
            errors.append(f"{where}.cost_class must be one of {sorted(COST_CLASSES)}")
        if not isinstance(step["drill_required"], bool):
            errors.append(f"{where}.drill_required must be boolean")
        if step["drill_required"]:
            if not re.fullmatch(r"\d{2}(?:/\d{2})?", str(step.get("drill_ref", ""))):
                errors.append(f"{where} requires a drill_ref such as 06 or 01/02")
            if not isinstance(step.get("drill_minutes"), int) or step["drill_minutes"] <= 0:
                errors.append(f"{where} requires positive drill_minutes")
        if not isinstance(step["tools"], list) or not step["tools"]:
            errors.append(f"{where}.tools must be a non-empty array")
        if not isinstance(step["teardown_required"], bool):
            errors.append(f"{where}.teardown_required must be boolean")
        if step["teardown_required"] and step["teardown"] == "none":
            errors.append(f"{where} requires teardown instructions")

    if len(steps) != 57:
        errors.append(f"manifest must contain 57 labs; found {len(steps)}")
    if len(set(ids)) != len(ids):
        errors.append("step IDs must be unique")
    if sorted(lab_numbers) != list(range(57)):
        errors.append("lab_no values must cover exactly 00 through 56")
    if sorted(sort_orders) != list(range(57)):
        errors.append("sort_order values must cover exactly 0 through 56")

    lab_dirs = {
        path.name
        for path in (ROOT / "labs").iterdir()
        if path.is_dir() and re.fullmatch(r"\d{2}-[a-z0-9-]+", path.name)
    }
    if set(ids) != lab_dirs:
        missing = sorted(lab_dirs - set(ids))
        extra = sorted(set(ids) - lab_dirs)
        errors.append(f"manifest/labs mismatch; missing={missing}, extra={extra}")

    by_id = {step["id"]: step for step in steps if isinstance(step, dict) and "id" in step}
    for step in steps:
        if not isinstance(step, dict) or "id" not in step or "requires" not in step:
            continue
        for requirement in step["requires"]:
            if requirement not in by_id:
                errors.append(f"{step['id']} requires unknown step {requirement}")
            elif by_id[requirement]["sort_order"] >= step["sort_order"]:
                errors.append(f"{step['id']} requirement {requirement} must come earlier")

    ordered = [step["id"] for step in sorted(steps, key=lambda item: item["sort_order"])]
    if ordered[: len(COMMON_CORE)] != COMMON_CORE:
        errors.append("common-core job-first sort order has drifted")
    platform_start = len(COMMON_CORE)
    if ordered[platform_start : platform_start + len(PLATFORM_BRANCH)] != PLATFORM_BRANCH:
        errors.append("Platform/CKA branch sort order has drifted")
    sre_start = platform_start + len(PLATFORM_BRANCH)
    if ordered[sre_start : sre_start + len(SRE_BRANCH)] != SRE_BRANCH:
        errors.append("SRE branch sort order has drifted")

    core_ids = [step["id"] for step in steps if step.get("tier") == "core"]
    if core_ids != COMMON_CORE:
        errors.append("tier=core must match the common-core route exactly")
    for step in steps:
        expected_track = {
            "core": "common-core",
            "elective": "elective",
        }.get(step.get("tier"))
        if expected_track and step.get("tracks") != [expected_track]:
            errors.append(f"{step.get('id')} must use tracks=[{expected_track!r}]")
        if step.get("tier") == "core" and not step.get("drill_required"):
            errors.append(f"core step {step.get('id')} must require a timed drill")
        if step.get("tier") == "specialization":
            selected = step.get("id") in PLATFORM_BRANCH or step.get("id") in SRE_BRANCH
            if bool(step.get("drill_required")) != selected:
                errors.append(
                    f"specialization step {step.get('id')} drill_required must be {str(selected).lower()}"
                )
        if step.get("tier") == "elective" and step.get("drill_required"):
            errors.append(f"elective step {step.get('id')} must not require a timed drill")

    migration_numbers: dict[int, list[Path]] = {}
    for path in (ROOT / "db" / "migrations").glob("*.sql"):
        match = re.match(r"(\d{6})_[^.]+\.(?:up|down)\.sql$", path.name)
        if match:
            migration_numbers.setdefault(int(match.group(1)), []).append(path)
    for number, paths in migration_numbers.items():
        names = [path.name for path in paths]
        stems = {name.rsplit(".", 2)[0] for name in names}
        directions = {name.rsplit(".", 2)[1] for name in names}
        if len(stems) != 1 or directions != {"up", "down"} or len(paths) != 2:
            errors.append(f"migration {number:06d} must have one matching up/down pair; found {names}")
    if sorted(migration_numbers) != list(range(1, max(migration_numbers, default=0) + 1)):
        errors.append("migration versions must be unique and contiguous from 000001")
    curriculum_pair = set(migration_numbers.get(5, []))
    if curriculum_pair != {MIGRATION_UP_PATH, MIGRATION_DOWN_PATH}:
        errors.append("curriculum metadata must remain the matching 000005 up/down pair")

    migration_seed_ids: set[str] = set()
    for path in (ROOT / "db" / "migrations").glob("*.up.sql"):
        if path == MIGRATION_UP_PATH:
            continue
        migration_seed_ids.update(
            re.findall(r"\('([0-9]{2}-[a-z0-9-]+)'\s*,", path.read_text(encoding="utf-8"))
        )
    if migration_seed_ids != set(ids):
        errors.append(
            "baseline seed IDs must match the manifest exactly; "
            f"missing={sorted(set(ids) - migration_seed_ids)}, "
            f"extra={sorted(migration_seed_ids - set(ids))}"
        )

    if errors:
        raise CurriculumError("\n- ".join(["manifest validation failed:", *errors]))
    return sorted(steps, key=lambda item: item["sort_order"])


def _md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_roadmap(steps: list[dict[str, Any]]) -> str:
    tier_labels = {
        "core": "Common core",
        "specialization": "Specialization",
        "elective": "Elective",
    }
    track_labels = {
        "common-core": "Common core",
        "platform-cka": "Platform/CKA",
        "sre": "SRE",
        "elective": "Electives",
    }
    lines = [
        ROADMAP_BEGIN,
        "| Order | Lab | Tier | Track | Requires | Guided time | Shell | Account and tools | Cost | Teardown |",
        "|---:|---|---|---|---|---:|---|---|---|---|",
    ]
    for position, step in enumerate(steps, start=1):
        requirements = ", ".join(item[:2] for item in step["requires"]) or "—"
        tracks = ", ".join(track_labels[item] for item in step["tracks"])
        account_tools = f"{step['account']}; {', '.join(step['tools'])}"
        teardown = step["teardown"] if step["teardown_required"] else "—"
        lab_link = f"[{step['lab_no']:02d} — {_md(step['title'])}](../{step['doc_path']})"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(position),
                    lab_link,
                    tier_labels[step["tier"]],
                    tracks,
                    requirements,
                    f"{step['effort_minutes']} min",
                    _md(step["shell"]),
                    _md(account_tools),
                    step["cost_class"],
                    _md(teardown),
                ]
            )
            + " |"
        )
    lines.append(ROADMAP_END)
    return "\n".join(lines)


def render_migration_up(steps: list[dict[str, Any]]) -> str:
    # PostgreSQL's jsonb_to_recordset does not coerce a JSON array directly to
    # TEXT[], so encode arrays as PostgreSQL array literals for deterministic,
    # dependency-free migration generation.
    records = []
    for step in steps:
        record = {key: step[key] for key in DB_FIELDS}
        record["tracks"] = _pg_array(step["tracks"])
        record["requires"] = _pg_array(step["requires"])
        records.append(record)
    payload = json.dumps(records, ensure_ascii=False, indent=2)
    return f"""-- Generated by scripts/ci/check_curriculum.py from curriculum/manifest.json.
-- Do not edit this file directly; update the manifest and regenerate it.

ALTER TABLE steps
    ADD COLUMN tier TEXT NOT NULL DEFAULT 'elective'
        CONSTRAINT steps_tier_check CHECK (tier IN ('core', 'specialization', 'elective')),
    ADD COLUMN tracks TEXT[] NOT NULL DEFAULT ARRAY['elective']::TEXT[],
    ADD COLUMN \"requires\" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    ADD COLUMN effort_minutes INTEGER NOT NULL DEFAULT 60
        CONSTRAINT steps_effort_minutes_check CHECK (effort_minutes > 0),
    ADD COLUMN cost_class TEXT NOT NULL DEFAULT 'free'
        CONSTRAINT steps_cost_class_check CHECK (cost_class IN ('free', 'local', 'cloud-low', 'cloud-high')),
    ADD COLUMN drill_required BOOLEAN NOT NULL DEFAULT FALSE;

WITH curriculum AS (
    SELECT *
      FROM jsonb_to_recordset($curriculum$
{payload}
$curriculum$::JSONB) AS item(
        id TEXT,
        lab_no INTEGER,
        title TEXT,
        topic TEXT,
        maps_to TEXT,
        milestone INTEGER,
        doc_path TEXT,
        summary TEXT,
        sort_order INTEGER,
        tier TEXT,
        tracks TEXT[],
        \"requires\" TEXT[],
        effort_minutes INTEGER,
        cost_class TEXT,
        drill_required BOOLEAN
    )
), removed AS (
    DELETE FROM steps
     WHERE id NOT IN (SELECT id FROM curriculum)
    RETURNING id
)
INSERT INTO steps (
    id, lab_no, title, topic, maps_to, milestone, doc_path, summary, sort_order,
    tier, tracks, \"requires\", effort_minutes, cost_class, drill_required
)
SELECT
    id, lab_no, title, topic, maps_to, milestone, doc_path, summary, sort_order,
    tier, tracks, \"requires\", effort_minutes, cost_class, drill_required
FROM curriculum
ON CONFLICT (id) DO UPDATE SET
    lab_no = EXCLUDED.lab_no,
    title = EXCLUDED.title,
    topic = EXCLUDED.topic,
    maps_to = EXCLUDED.maps_to,
    milestone = EXCLUDED.milestone,
    doc_path = EXCLUDED.doc_path,
    summary = EXCLUDED.summary,
    sort_order = EXCLUDED.sort_order,
    tier = EXCLUDED.tier,
    tracks = EXCLUDED.tracks,
    \"requires\" = EXCLUDED.\"requires\",
    effort_minutes = EXCLUDED.effort_minutes,
    cost_class = EXCLUDED.cost_class,
    drill_required = EXCLUDED.drill_required;
"""


def _pg_array(values: list[str]) -> str:
    if not values:
        return "{}"
    escaped = [value.replace("\\", "\\\\").replace('"', '\\"') for value in values]
    return "{" + ",".join(f'"{value}"' for value in escaped) + "}"


def render_migration_down() -> str:
    return """ALTER TABLE steps
    DROP COLUMN IF EXISTS drill_required,
    DROP COLUMN IF EXISTS cost_class,
    DROP COLUMN IF EXISTS effort_minutes,
    DROP COLUMN IF EXISTS \"requires\",
    DROP COLUMN IF EXISTS tracks,
    DROP COLUMN IF EXISTS tier;
"""


def replace_roadmap(document: str, generated: str) -> str:
    if document.count(ROADMAP_BEGIN) != 1 or document.count(ROADMAP_END) != 1:
        raise CurriculumError(
            f"{CURRICULUM_PATH.relative_to(ROOT)} must contain exactly one generated roadmap marker pair"
        )
    pattern = re.compile(re.escape(ROADMAP_BEGIN) + r".*?" + re.escape(ROADMAP_END), re.DOTALL)
    return pattern.sub(generated, document)


def validate_drills(steps: list[dict[str, Any]]) -> None:
    text = DRILLS_PATH.read_text(encoding="utf-8")
    heading = re.compile(
        r"^###\s+Lab\s+(\d{2}(?:/\d{2})?)(?=\s|—|–|-)[^\n]*?\btarget\s+(\d+)\s+min\b[^\n]*$",
        re.IGNORECASE | re.MULTILINE,
    )
    matches = list(heading.finditer(text))
    drills: dict[tuple[str, int], list[str]] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        drills.setdefault((match.group(1), int(match.group(2))), []).append(text[match.end() : end])

    errors: list[str] = []
    checked: set[tuple[str, int]] = set()
    for step in steps:
        if not step["drill_required"]:
            continue
        key = (step["drill_ref"], step["drill_minutes"])
        if key in checked:
            continue
        checked.add(key)
        chunks = drills.get(key, [])
        if not chunks:
            errors.append(f"missing timed drill heading for Lab {key[0]} target {key[1]} min")
        elif not any(re.search(r"^\*\*Pass:\*\*", chunk, re.MULTILINE) for chunk in chunks):
            errors.append(f"Lab {key[0]} target {key[1]} min has no **Pass:** rule")

    full_cka = drills.get(("48", 120), [])
    if not full_cka:
        errors.append("missing Lab 48 full simulation heading with target 120 min")
    elif not any(re.search(r"^\*\*Pass:\*\*", chunk, re.MULTILINE) for chunk in full_cka):
        errors.append("Lab 48 full simulation has no **Pass:** rule")
    if not re.search(r"8/10.*twice.*different weeks", text, re.IGNORECASE | re.DOTALL):
        errors.append("Lab 48 internal mock must require 8/10 twice on different weeks")
    if not re.search(r"120.min[\s\S]{0,800}simulator[\s\S]{0,200}scor", text, re.IGNORECASE):
        errors.append("Lab 48 full simulation must use the simulator scoring rule")

    if errors:
        raise CurriculumError("\n- ".join(["drill validation failed:", *errors]))


def write_migrations(steps: list[dict[str, Any]]) -> None:
    MIGRATION_UP_PATH.write_text(render_migration_up(steps), encoding="utf-8", newline="\n")
    MIGRATION_DOWN_PATH.write_text(render_migration_down(), encoding="utf-8", newline="\n")


def write_roadmap(steps: list[dict[str, Any]]) -> None:
    current = CURRICULUM_PATH.read_text(encoding="utf-8")
    updated = replace_roadmap(current, render_roadmap(steps))
    CURRICULUM_PATH.write_text(updated, encoding="utf-8", newline="\n")


def check_generated(steps: list[dict[str, Any]]) -> None:
    errors: list[str] = []
    expected_files = {
        MIGRATION_UP_PATH: render_migration_up(steps),
        MIGRATION_DOWN_PATH: render_migration_down(),
    }
    for path, expected in expected_files.items():
        try:
            actual = path.read_text(encoding="utf-8")
        except OSError:
            errors.append(f"missing generated file {path.relative_to(ROOT)}")
            continue
        if actual != expected:
            errors.append(
                f"{path.relative_to(ROOT)} is stale; run "
                "python scripts/ci/check_curriculum.py --write-migration"
            )

    try:
        document = CURRICULUM_PATH.read_text(encoding="utf-8")
        expected_document = replace_roadmap(document, render_roadmap(steps))
        if document != expected_document:
            errors.append(
                f"{CURRICULUM_PATH.relative_to(ROOT)} roadmap is stale; run "
                "python scripts/ci/check_curriculum.py --write-roadmap"
            )
    except (OSError, CurriculumError) as exc:
        errors.append(str(exc))

    try:
        validate_drills(steps)
    except (OSError, CurriculumError) as exc:
        errors.append(str(exc))

    if errors:
        raise CurriculumError("\n- ".join(["generated curriculum check failed:", *errors]))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="validate the manifest and generated artifacts")
    action.add_argument("--generate", action="store_true", help="regenerate the migration and roadmap table")
    action.add_argument("--write-migration", action="store_true", help="regenerate only migration 000005")
    action.add_argument("--write-roadmap", action="store_true", help="regenerate only the marked roadmap table")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        steps = validate_manifest(load_manifest())
        if args.generate:
            write_migrations(steps)
            write_roadmap(steps)
            print("generated curriculum migration and roadmap")
        elif args.write_migration:
            write_migrations(steps)
            print("generated curriculum migration")
        elif args.write_roadmap:
            write_roadmap(steps)
            print("generated curriculum roadmap")
        else:
            check_generated(steps)
            print(f"curriculum integrity OK: {len(steps)} labs")
        return 0
    except CurriculumError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
