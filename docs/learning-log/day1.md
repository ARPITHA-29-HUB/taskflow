# Learning Log — Day 1: Git & GitHub Foundations

- **Date**: 2026-10-21
- **Focus Area**: Git Architecture, Branching Strategy, Conventional Commits, Pull Requests, CI Automation, Code Review, and Conflict Resolution

---

## 1. What You Need to Learn Today (Curriculum Breakdown)

### A. The Git Mental Model: 4 Key Zones
Understanding where code lives at any moment:
1. **Working Directory**: The actual files on your hard drive you are currently editing.
2. **Staging Area (Index)**: The "preparation room" where you choose which specific changes will go into the next snapshot via `git add`.
3. **Local Repository (`.git`)**: The permanent history of committed snapshots saved locally on your computer via `git commit`.
4. **Remote Repository (GitHub)**: The cloud-hosted copy of the repository accessible to collaborators and CI runners via `git push` and `git pull`.

---

### B. Essential Commands & Their Purposes

| Command | What it does | Real-world Analogy |
| :--- | :--- | :--- |
| `git status` | Shows which files are modified, untracked, or staged | Checking what items are in your cart before checkout |
| `git diff` | Shows line-by-line differences before staging | Proofreading changes before saving |
| `git checkout -b <branch>` | Creates and immediately switches to a new branch | Creating a safe scratchpad so you don't touch the original document |
| `git add <file>` | Moves changes from working directory to staging | Putting approved items into the delivery box |
| `git commit -m "msg"` | Packages staged changes into a permanent recorded commit | Sealing the box with an official tracking label |
| `git remote -v` | Shows which cloud repository your machine is connected to | Checking the destination delivery address |
| `git log --oneline -5` | Lists the most recent 5 commits concisely | Reviewing your recent transaction receipt history |
| `git push -u origin <branch>` | Uploads the local branch to GitHub and links it for future pushes | Sending the package to the central warehouse |

---

### C. Conventional Commits Standard
Writing commit messages that machines and humans can easily understand:
- `feat:` A new feature or capability for the user
- `fix:` A bug fix
- `chore:` Maintenance, setup, configuration, or dependency updates (e.g. `chore(setup): add TaskFlow project foundation`)
- `docs:` Documentation-only changes
- `test:` Adding or refactoring automated tests
- `refactor:` Code change that neither fixes a bug nor adds a feature

---

### D. Pull Request (PR) Mechanics
1. **Base branch (`main`)**: The stable branch that receives tested, approved code.
2. **Head branch (`chore/day-0-foundation`)**: The feature branch where you made your new changes.
3. **PR Template (`.github/pull_request_template.md`)**: A structured checklist ensuring developers explain the *why*, *what*, and *testing steps* before requesting a merge.
4. **Code Review**: Peer inspection of code before it gets added to the main branch. Reviewers can request changes, comment on specific lines, or approve.

---

### E. Continuous Integration (CI) with GitHub Actions
- Whenever a branch is pushed or a PR is opened, `.github/workflows/ci.yml` runs automatically on a clean Linux virtual machine in the cloud.
- **Backend Job**: Automatically sets up Python 3.12, installs dependencies, verifies Alembic, and runs `pytest`.
- **Frontend Job**: Automatically sets up Node 22, runs `npm run lint` and `npm run build`.
- If either job fails, the PR shows a red ❌ and merging is blocked until fixed.

---

### F. Git Merge Conflicts: Causes & Resolution
- **What causes a conflict?** When two branches change the exact same line of a file, Git cannot know which version is the correct one.
- **How Git marks it**:
  ```text
  <<<<<<< HEAD (Current branch code)
  Welcome to TaskFlow v1.0
  =======
  Welcome to TaskFlow Cloud Edition
  >>>>>>> incoming-branch (Incoming code)
  ```
- **How to resolve**:
  1. Open the file in your editor.
  2. Decide which code to keep (or combine both).
  3. Delete the `<<<<<<<`, `=======`, and `>>>>>>>` marker lines.
  4. Save the file, run `git add <file>`, and complete the commit.

---

### G. Security & Secrets Hygiene
- **Rule #1**: **Never commit secrets** (passwords, JWT secret keys, API credentials, SQLite database files) to Git.
- **`.gitignore`**: Tells Git which files to intentionally ignore and never track (e.g. `.env`, `.venv/`, `node_modules/`, `*.db`).
- **`.env.example`**: A safe template that shows what environment variables the app expects, using placeholder values only.

---

## 2. Practical Commands Practiced Today

```bash
# 1. Inspect repository state
git rev-parse --show-toplevel
git status
git branch --show-current
git remote -v
git log -5 --oneline

# 2. Safe branching
git checkout -b chore/day-0-foundation

# 3. Review diff and stage clean files
git diff README.md
git add .

# 4. Create structured conventional commit
git commit -m "chore(setup): add TaskFlow project foundation"

# 5. Push to GitHub (Next step)
git push -u origin chore/day-0-foundation
```

---

## 3. Key Takeaways
- Always develop on a feature or chore branch, never directly on `main`.
- Clean commit hygiene makes debugging with `git bisect` and team collaboration seamless.
- CI automated testing catches regressions before code ever touches production.
