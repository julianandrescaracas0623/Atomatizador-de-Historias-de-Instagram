---
name: setting-up-ci
description: Set up GitHub Actions CI for this FastAPI + React repo with Python lint/test and Node lint/typecheck/build. Use when the user asks for CI, a build pipeline, or GitHub Actions.
---

# Setup CI (GitHub Actions)

Python backend + Node frontend. Do not generate a Node-only workflow.

## Steps

1. Confirm `backend/` has `requirements.txt` or `pyproject.toml`, and `frontend/` has `package.json`.

2. Create `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -r requirements.txt
      - run: ruff check .
      - run: pytest

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm run build
```

3. If scripts are missing, add them:

- Backend: `ruff` and `pytest` in `requirements-dev.txt` (or extras)
- Frontend `package.json`: `"typecheck": "tsc --noEmit"`

4. Deploy job is optional and only if the user asks. Gate it on both jobs. This app needs a long-running API + worker + Postgres + HTTPS; do not add a Vercel deploy for the backend.

5. Optional README badge:

```markdown
![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)
```

## Notes

- `npm ci`, not `npm install`
- Secrets only in GitHub Settings, never in the workflow file
- Skip pytest/ruff steps until those tools exist in the repo; do not invent a green pipeline that calls missing commands
