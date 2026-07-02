# Lab 38 — Git workflows: branches, rebase, bisect, protection

**Maps to:** extra · **Milestone:** 4 — Operate & Automate · **do anytime**

## Concept

Every interview assumes Git fluency beyond `add/commit/push`: feature-branch + PR flow,
cleaning history with **interactive rebase**, resolving **conflicts** calmly, hunting a
regression with **bisect**, and knowing the trunk-based vs GitFlow trade-off. None of it
needs a team to practice — your own repo is enough, and everything below happens on scratch
branches you'll delete afterwards.

Safety net first: in Git, almost nothing is lost — `git reflog` records every position HEAD
has had. If any drill goes sideways: `git reflog`, find the state before the mess,
`git reset --hard <that-sha>`.

## What you'll do

Five drills, each self-contained. Run them from the repo root on a scratch branch.

## Steps

### Drill 1 — Feature branch + PR flow (the daily loop)

```powershell
git switch -c lab38/feature-drill
# make a small real change (e.g. a line in this README), then:
git add -A; git commit -m "docs: practice change for lab 38"
git push -u origin lab38/feature-drill
```

Open the PR on GitHub, watch CI from lab 15 run against it (PRs build + scan but don't
publish — that's the point of the trigger design), then **squash-merge** and delete the
branch. Why teams work this way: `main` stays releasable, every change is reviewed and
CI-gated, and a squash keeps one commit per change.

### Drill 2 — Interactive rebase (clean history before review)

Fabricate the classic messy series, then squash it:

```powershell
git switch -c lab38/rebase-drill
"one" | Out-File drill.txt;  git add drill.txt; git commit -m "add drill file"
"two" | Add-Content drill.txt; git commit -am "wip"
"three" | Add-Content drill.txt; git commit -am "fix typo"
git rebase -i HEAD~3
```

In the editor, keep the first as `pick`, mark the other two `fixup` (or `squash` to merge
messages). Result: one reviewable commit. Rule that interviewers listen for: **rebase your
own unpushed branches freely; never rewrite shared history** — if it's already pushed and
others may have it, you're into `git push --force-with-lease` territory and a conversation.

### Drill 3 — Merge conflict, resolved calmly

Manufacture a guaranteed conflict:

```powershell
git switch -c lab38/conflict-a
"line from A" | Out-File conflict.txt; git add conflict.txt; git commit -m "A's version"
git switch -c lab38/conflict-b HEAD~1
"line from B" | Out-File conflict.txt; git add conflict.txt; git commit -m "B's version"
git merge lab38/conflict-a
```

Git stops with `CONFLICT (add/add)`. The method (not panic): `git status` lists conflicted
files; open the file, pick/combine between the `<<<<<<<`/`>>>>>>>` markers; `git add` the
file; `git commit` (or `git merge --abort` to walk away). Say the method out loud — that's
the interview answer.

### Drill 4 — `git bisect` (find the breaking commit by binary search)

Plant a regression somewhere in 10 commits, then let bisect find it:

```powershell
git switch -c lab38/bisect-drill
foreach ($i in 1..10) {
  if ($i -eq 7) { "BUG" | Add-Content bisect.txt } else { "ok $i" | Add-Content bisect.txt }
  git add bisect.txt; git commit -m "change $i" | Out-Null
}
git bisect start HEAD HEAD~10
git bisect run sh -c '! grep -q BUG bisect.txt'
git bisect reset
```

`bisect run` re-runs your test at each step and lands on "change 7" in ~3 steps instead of
10. The real-world version replaces the `grep` with your actual test (`go test ./...`, a curl
against a symptom) — that's how you find *which deploy broke it* when nobody knows.

### Drill 5 — Branch protection (make the workflow mandatory)

On GitHub: **Settings → Branches → Add branch ruleset** for `main`/`master`: require a pull
request, require the lab 15 CI check to pass, block force pushes. Then try
`git push origin main` with a direct commit and watch it bounce. This is what turns "we
should review changes" from a promise into a property of the system — the same idea as
GitOps (lab 25) and admission policies (lab 29): enforce, don't intend.

Cleanup:

```powershell
git switch master
git branch -D lab38/feature-drill lab38/rebase-drill lab38/conflict-a lab38/conflict-b lab38/bisect-drill
Remove-Item drill.txt, conflict.txt, bisect.txt -ErrorAction SilentlyContinue
```

## How it works

- **Merge vs rebase:** merge preserves what happened (extra merge commits); rebase replays
  your commits on a new base for linear history. Teams usually rebase feature branches,
  merge (or squash) into trunk.
- **Trunk-based vs GitFlow (the talk track):** trunk-based = short-lived branches into
  `main`, deploy from trunk, feature flags for unfinished work — fits CD (labs 15/25).
  GitFlow = long-lived `develop`/`release`/`hotfix` branches — fits versioned, scheduled
  releases (boxed software, mobile). Wrong answer: dogma either way. Right answer: "how often
  do you release?"
- **Why `--force-with-lease` not `--force`:** it refuses to overwrite work someone pushed
  after your last fetch — force with a seatbelt.
- **Reflog:** branches are pointers; commits are content-addressed and stay reachable via
  reflog for weeks even when "deleted". This is why confident rebasing is safe.

## Exercise

1. Adopt **conventional commits** (`feat:`, `fix:`, `docs:`, `chore:`) for the rest of
   Milestone 4 and skim how tools derive changelogs/semver from them.
2. "Disaster" recovery: delete a branch with unmerged commits (`git branch -D`), then get the
   commits back via `git reflog` + `git branch <name> <sha>`.
3. Read `.github/workflows/ci.yml` and answer: which trigger runs on PRs, and why does
   publishing only happen on non-PR events? (You configured protection around exactly this.)

## Checkpoint

- ✅ You squashed three messy commits into one with interactive rebase — and can recover via
  reflog if it goes wrong.
- ✅ You resolved an add/add conflict without `--abort` and can narrate the method.
- ✅ `git bisect run` found the planted "change 7" commit for you.
- ✅ Direct pushes to your default branch bounce off branch protection.

## Common failures

- Rebase editor is vim and you're stuck → `Esc :q!` aborts; set
  `git config core.editor "code --wait"` to use VS Code.
- `bisect run` "finds" the wrong commit → your test command's exit code is inverted;
  remember it must **fail on bad** (hence the `!` in the drill).
- Push rejected after a rebase → expected: history changed. On your own branch,
  `git push --force-with-lease`.
- Conflict markers committed by accident → CI/lint should catch `<<<<<<<`; fix, amend,
  re-push (pre-commit's merge-conflict hook does this — see `.pre-commit-config.yaml`).

➡️ Next: [Lab 39 — Terraform remote state, modules & CI](../39-terraform-state-and-modules/)
