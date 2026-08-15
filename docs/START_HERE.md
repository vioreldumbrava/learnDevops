# Start here — DevOps Dojo

Start from the repository root in PowerShell:

```powershell
Set-Location C:\git_projects\learnDevops
```

Docker Desktop is already configured. Your `.env` file is the first local prerequisite.

## First session

1. Open [Lab 00 — Prerequisites](../labs/00-prerequisites/README.md).

2. Create and edit your environment file:

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

   Change `POSTGRES_PASSWORD`. This repository is already initialized and committed, so
   skip Lab 00's `git init` and initial-import commit.

3. Start the application:

   ```powershell
   docker compose `
     -f deploy/compose/compose.yaml `
     -f deploy/compose/compose.dev.yaml `
     up --build
   ```

4. Verify the running system:

   - Dashboard: <http://localhost:5173>
   - API health: <http://localhost:8080/healthz>
   - API metrics: <http://localhost:8080/metrics>

   In the dashboard, mark a lab complete, reload, and confirm it remains completed.

5. Stop the application without deleting your progress:

   ```powershell
   docker compose `
     -f deploy/compose/compose.yaml `
     -f deploy/compose/compose.dev.yaml `
     down
   ```

   Avoid `down -v` unless you intentionally want to erase the database.

## Learning order

Begin with:

> `00 → selected Git basics from 38 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08`

Then follow the generated common-core order in [CURRICULUM.md](CURRICULUM.md).

For now, use [Lab 38](../labs/38-git-workflows/README.md) to practise branches, conflicts,
rebase, and bisect. Defer its GitHub branch-protection and CI portions until Lab 15.

## How to complete each lab

For every lab:

1. Read the **Concept** section.
2. Follow the guided **Steps**.
3. Complete the **Exercise** yourself.
4. Pass every **Checkpoint**.
5. Produce a commit, runbook, ADR, script, or troubleshooting note.
6. About seven days later, attempt its timed exercise from [DRILLS.md](DRILLS.md) without
   the walkthrough.

Mark a lab `completed` after its checkpoint. Mark it `drilled` only after passing the delayed
timed drill.

## Weekly rhythm

Follow [WEEKLY.md](WEEKLY.md):

- 90 minutes: guided build.
- 90 minutes: exercise and portfolio artifact.
- 60 minutes: delayed drill.
- 60 minutes: CV, GitHub, applications, or interview practice.

Start your CV and GitHub profile in week 1. Begin two targeted applications per week from
week 3. Do not wait to finish all 57 labs before applying.
