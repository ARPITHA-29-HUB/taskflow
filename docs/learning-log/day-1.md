# Learning Log — Day 1: Git & GitHub Foundations

- **Date**: 2026-10-21
- **Author**: Battineedi Charan
- **Milestone**: Day 1 — Version Control, GitHub Workflows & Collaboration
- **Status**: Completed & Verified

---

## 1. Objectives & Goals
- [x] Inspect Git repository foundations and verify no nested folders
- [x] Master the 4-zone Git mental model (Working Directory, Staging Area, Local Repo, GitHub Remote)
- [x] Practice safe feature branching (`chore/day-0-foundation`)
- [x] Push branch to remote with upstream tracking (`git push -u origin <branch>`)
- [x] Open Pull Request #1 on GitHub using `.github/pull_request_template.md`
- [x] Verify CI pipeline automation via GitHub Actions (Backend pytest & Frontend build)
- [x] Practice responding to a simulated code review comment with follow-up commits
- [x] Conduct a hands-on merge conflict exercise and manual resolution
- [x] Learn and execute commit squashing (combining messy draft commits into one clean commit)
- [x] Answer the 3 "Explain-It-Back" foundational questions

---

## 2. Practical Exercises & Execution Log

### Exercise 1: Repository Inspection
Ran five foundational inspection commands from project root:
- `git rev-parse --show-toplevel` -> Verified root at `C:/Users/91630/OneDrive/Desktop/taskflow`
- `git status` -> Identified clean working tree with `.gitignore` protecting `.venv`, `.env`, and `node_modules`
- `git branch --show-current` -> Confirmed initial branch `main`
- `git remote -v` -> Confirmed `origin` pointing to `https://github.com/ARPITHA-29-HUB/taskflow.git`
- `git log -5 --oneline` -> Confirmed initial commit `a6d940b`

### Exercise 2: Branching & Baseline Commit
- Switched to feature branch: `git checkout -b chore/day-0-foundation`
- Staged all Day 0 setup files: `git add .`
- Created baseline commit: `git commit -m "chore(setup): add TaskFlow project foundation"` (`8e4ce8f`)

### Exercise 3: Remote Push & Pull Request #1
- Pushed branch to remote: `git push -u origin chore/day-0-foundation`
- Opened Pull Request #1: [chore(setup): add TaskFlow project foundation](https://github.com/ARPITHA-29-HUB/taskflow/pull/1)
  - **Base**: `main`
  - **Head**: `chore/day-0-foundation`
  - Used standardized template from `.github/pull_request_template.md`

### Exercise 4: CI Automation Inspection
- GitHub Actions triggered automatically on PR #1:
  - **Workflow**: `CI Pipeline`
  - **Job 1 (Backend Tests & Quality)**: Python 3.12, dependencies installed, Alembic validated, `pytest` passed (3/3 tests in 0.81s)
  - **Job 2 (Frontend Build & Lint)**: Node 22, `oxlint` (0 errors), `vite build` completed (814ms)
  - **Total Duration**: Completed in **17 seconds** with green status 🟢

### Exercise 5: Simulated Code Review & Follow-up Commit
- **Reviewer Comment**: Requested a troubleshooting guide for port conflicts (ports 8000 & 5173).
- **Golden Rule Practiced**: Never close the PR. Made edit to `README.md` on the same branch.
- **Commit & Push**:
  ```bash
  git add README.md
  git commit -m "docs(readme): add troubleshooting section for port conflicts"
  git push
  ```
- Commit `5c3c475` appeared automatically in PR #1, triggering a fresh CI check.

### Exercise 6: Merge Conflict Simulation & Resolution
- Created two divergent branches: `practice/alice` and `practice/bob`.
- Both branches modified line 2 of `docs/conflict-demo.txt` simultaneously.
- When running `git merge practice/bob`, Git stopped with:
  ```text
  CONFLICT (content): Merge conflict in docs/conflict-demo.txt
  Automatic merge failed; fix conflicts and then commit the result.
  ```
- **Conflict Markers Inspected**:
  - `<<<<<<< HEAD`: Alice's changes
  - `=======`: Collision boundary
  - `>>>>>>> practice/bob`: Bob's changes
- **Resolution**: Replaced conflict block with unified line:
  `Line 2: Unified: Built with FastAPI, SQLite, React 19, Python 3.12, and Vite 8.`
- Removed markers, staged, and committed merge commit `1a3eee3`.
- Verified merged topology using `git log --graph --oneline`.

### Exercise 7: Commit Squashing
- Created 3 micro-commits on `practice/squash-demo`:
  1. `7d8243b docs: draft task priorities list`
  2. `42c6309 docs: add medium priority line`
  3. `af6c27d docs: add high priority line`
- Squashed all 3 micro-commits into a single clean commit:
  `c3959f0 docs: define complete task priority guide`
- Verified history was condensed and cleaned up before deleting practice branches.

---

## 3. The 3 Explain-It-Back Answers

### Q1: What is the difference between `git add`, `git commit`, and `git push`?
- **`git add`**: Prepares changes by placing them in the **Staging Area** (like packing items into a shipping box).
- **`git commit`**: Takes the staged changes and records a permanent, labeled snapshot in the **Local Repository** (like sealing the box and printing an official tracking number).
- **`git push`**: Uploads local commits from your machine to the **Remote Repository on GitHub** (like handing the package to the courier for delivery to the central warehouse).

### Q2: What causes a merge conflict, and how do you resolve it?
- **Cause**: Occurs when two branches modify the **exact same lines of the same file** in different ways. Because Git does not guess developer intent, it pauses the merge.
- **Resolution Process**:
  1. Open the conflicted file and locate `<<<<<<< HEAD`, `=======`, and `>>>>>>>`.
  2. Choose the correct code (Alice's, Bob's, or combine both).
  3. Delete the `<<<<<<<`, `=======`, and `>>>>>>>` marker lines.
  4. Run `git add <file>` to mark the conflict resolved.
  5. Run `git commit` to finalize the merge commit.

### Q3: Why do professional teams use Pull Requests and CI instead of pushing directly to `main`?
- **`main` is Production**: Direct commits to `main` risk breaking the live build for all users.
- **Code Review**: PRs allow team members to review code, spot security flaws, ensure architectural alignment, and share context before merging.
- **Automated Quality Gates (CI)**: GitHub Actions automatically executes unit tests (`pytest`), linters (`oxlint`), and production compilation (`vite build`) on clean cloud runners, guaranteeing broken code never gets merged.

---

## 4. Key Learnings & Takeaways
1. **Branch Hygiene**: Always create a feature branch (`feat/`, `chore/`) for new tasks; keep `main` pristine.
2. **Review Resilience**: Review feedback does not require a new PR—simply push commits to the existing branch.
3. **Conflict Confidence**: Merge conflicts are routine collaboration events, not disasters. Carefully reading the conflict markers makes resolution straightforward.
4. **Clean History**: Squashing work-in-progress commits keeps commit logs legible and bisectable.

---

## 5. Next Steps (Day 2 Preview)
- Merge Pull Request #1 into `main` using GitHub's interface.
- Pull updated `main` locally: `git checkout main && git pull origin main`.
- Begin Day 2: Implement User data models, SQLAlchemy schema, and Alembic database migrations.
