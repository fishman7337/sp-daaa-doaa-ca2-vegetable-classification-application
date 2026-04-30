# RPA (Optional)

This repository supports two RPA approaches:

1. Selenium script for lightweight scripted checks
2. UiPath coded workflow for full UI automation in Studio/Orchestrator

## Selenium path

File:

1. `scripts/rpa_test.py`

Flow:

1. Open web app URL
2. Log in
3. Upload sample image
4. Run prediction
5. Verify history updates

## UiPath coded workflow path

Files:

1. `scripts/uipath/VeggieAiFrontendE2E.cs`
2. `scripts/uipath/README.md`

Coverage:

1. Login with email/password
2. Optional sign-up fallback with terms checkbox
3. Captcha handling hook
4. OTP verification in development mode
5. Forgot-password request check
6. Batch prediction and history validation

## Security and reliability notes

1. Do not hardcode credentials in workflow code.
2. Store secrets in UiPath Assets/Credential Manager.
3. Captcha/OTP are anti-automation controls; unattended runs need development overrides.
4. Recommended dev/test flags for unattended pipeline runs:
   1. `CAPTCHA_DEV_MODE=true`
   2. `OTP_DEV_MODE=true`

## Environment

Use `RPA_BASE_URL` (for Selenium) or equivalent UiPath input/base URL configuration, typically:

1. `http://localhost:5000`
