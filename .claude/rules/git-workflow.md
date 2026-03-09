# Git Workflow

## Branches

- `main` — stable, release-ready. Never commit directly.
- `dev` — integration branch. Features merge here first.
- `feat/<short-description>` — new features, branch from `dev`
- `fix/<short-description>` — bug fixes, branch from `dev`
- `hotfix/<short-description>` — critical production fixes, branch from `main`

**Flow:** `feat/xxx` → PR to `dev` → when stable, `dev` → PR to `main`

## Commits

- Follow [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): imperative summary`
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `ci`, `style`, `build`
- Scope is optional but recommended
- Breaking changes: append `!` after type/scope — `feat(api)!: remove v1 endpoint`
- Atomic: one logical change per commit
- Every commit must include:
  ```
  Co-Authored-By: spidecode-bot <263227865+spicode-bot@users.noreply.github.com>
  ```
- Run `ruff check` and `ruff format --check` before committing
- Never commit: `.env`, `auth.json`, `cookies.json`, tokens, `__pycache__`

## Pull Requests

- Always from feature/fix branch → `dev` (or `dev` → `main`)
- PR title follows same `type(scope): summary` convention
- PR must include: summary (what + why), test plan
- Author: **spicode-bot** — Reviewer: **spideystreet**
- Squash merge preferred for feature branches
- Delete branch after merge

## Tags & Releases

- Semantic versioning: `vMAJOR.MINOR.PATCH`
- Tag on `main` only, after merge from `dev`
- Create GitHub release with changelog
