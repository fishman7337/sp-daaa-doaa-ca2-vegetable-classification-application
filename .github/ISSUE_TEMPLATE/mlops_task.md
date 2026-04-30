---
name: MLOps task
about: Track model, deployment, monitoring, or CI/CD work
title: "chore(mlops): "
labels: mlops
assignees: ""
---

## Objective

State the model, pipeline, deployment, or monitoring outcome.

## Validation Plan

- [ ] `python scripts/check_readmes.py`
- [ ] `python scripts/validate_model_registry.py --models-root models --report reports/model-registry-report.json`
- [ ] `pytest`
- [ ] Smoke checks pass

## Evidence

Link reports, screenshots, logs, or deployment proof.
