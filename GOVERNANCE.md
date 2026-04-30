# Governance

VeggieAI is an individual academic MLOps project. Governance focuses on traceability, safe change control, and reproducible evidence.

## Roles

- Owner: Goh Kun Ming
- Academic reviewer: Lecturer Ryan Chia Xueyi, Singapore Polytechnic
- Maintainers: owner and approved academic reviewers

## Branching

- `main`: release-ready branch.
- `develop`: integration branch when active development is split from releases.
- Feature branches: `feat/*`.
- Fix branches: `fix/*`.
- Documentation branches: `docs/*`.
- Maintenance branches: `chore/*`.

## Pull Requests

- Use the GitHub pull request template.
- Link to an issue, task, or coursework requirement when applicable.
- Keep changes scoped.
- Require passing CI gates before merge.
- Include screenshots or report artifacts for UI, deployment, or model changes.

## Quality Gates

- Folder README structure check.
- Ruff lint and format checks.
- Backend and model-service pytest suites.
- Model registry validation.
- Runtime smoke tests.
- Security scans.
- Docker image builds.

## Releases

- Use semantic versioning (`vMAJOR.MINOR.PATCH`).
- Update `CHANGELOG.md`.
- Keep deployment evidence in `docs/evidence/` or `reports/`.
- Record model changes in `docs/model-governance.md`.
