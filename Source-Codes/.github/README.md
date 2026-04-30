# GitHub Configuration

This folder contains GitHub automation for the VeggieAI MLOps Platform when `Source-Codes/` is published as the repository root.

- `workflows/ci.yml`: CI/CD gates for docs, linting, pytest, MLOps validation, security scans, and Docker builds.
- `ISSUE_TEMPLATE/`: GitHub issue templates for bugs, features, and MLOps tasks.
- `PULL_REQUEST_TEMPLATE.md`: GitHub pull request checklist.
- `dependabot.yml`: dependency update schedule for GitHub Actions and Python package ecosystems.

The legacy GitLab pipeline is retained separately in `.gitlab-ci.yml` only for optional mirror hosting.
