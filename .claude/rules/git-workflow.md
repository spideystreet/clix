# Git Workflow

## Branches

- `main` — stable, release-ready. Never commit directly.
- `feat/<short-description>` — new features, branch from `main`
- `fix/<short-description>` — bug fixes, branch from `main`

**Flow:** `feat/xxx` or `fix/xxx` → PR to `main` → tag on `main`

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

- Always from feature/fix branch → `main`
- PR title follows same `type(scope): summary` convention
- PR must include: summary (what + why), test plan
- Author: **spicode-bot** — Reviewer: **spideystreet**
- Squash merge preferred for feature branches
- Delete branch after merge

## Tags & Releases

- Semantic versioning: `vMAJOR.MINOR.PATCH`
- Tag on `main` only, after merge
- Create GitHub release with changelog
