# UiPath Coded Workflow (VeggieAI)

This folder contains a coded UiPath workflow template for your Flask/Jinja frontend:

- `VeggieAiFrontendE2E.cs`

It covers:

1. Sign in (email + password)
2. Optional sign-up fallback (name + email + password + terms + captcha)
3. OTP verify in development mode
4. Forgot password request check
5. Batch prediction flow (multi-sample)
6. History validation

## 1) Prerequisites

1. Install `UiPath Studio` (Community is fine).
2. Create a new process project in Studio.
3. Install packages:
   1. `UiPath.CodedWorkflows`
   2. `UiPath.UIAutomation.Activities`
4. Copy `scripts/uipath/VeggieAiFrontendE2E.cs` into your UiPath project (for example in `CodedWorkflows/`).

## 2) Object Repository Setup

Create these two screens:

1. `VeggieAI.AuthScreen`: URL like `*://*/auth*`
2. `VeggieAI.PredictScreen`: URL like `*://*/predict*`

Create the elements below with the exact names used by the coded workflow.

### `VeggieAI.AuthScreen` elements

1. `GetStartedButton` -> header/button text "Get Started" on home (optional fallback when opened on `/`)
1. `ModeSignInButton` -> `#mode-login`
2. `ModeSignUpButton` -> `#mode-signup`
3. `AuthTitleText` -> `#auth-title`
4. `EmailInput` -> `#input-email`
5. `PasswordInput` -> `#input-password`
6. `FullNameInput` -> `#input-name`
7. `TermsCheckbox` -> `#agree-terms`
8. `CaptchaPromptText` -> `#captcha-prompt`
9. `CaptchaAnswerInput` -> `#captcha-answer`
10. `AuthSubmitButton` -> `#auth-submit`
11. `AuthErrorText` -> `#auth-error-text`
12. `AuthSuccessText` -> `#auth-success-text`
13. `AuthWarningText` -> `#auth-warning-text`
14. `DevOtpText` -> `#auth-dev-otp-text`
15. `OtpInput` -> `#input-otp`
16. `OtpVerifyButton` -> `#otp-verify-btn`
17. `ForgotPasswordLink` -> `#forgot-password-link`
18. `ForgotEmailInput` -> `#forgot-email`
19. `ForgotSubmitButton` -> `#forgot-submit`
20. `ForgotBackButton` -> `#forgot-back`

### `VeggieAI.PredictScreen` elements

1. `SampleCapsicumButton` -> CSS `[data-sample*='capsicum.jpg']`
2. `SampleCarrotButton` -> CSS `[data-sample*='carrot.jpg']`
3. `SampleTomatoButton` -> CSS `[data-sample*='tomato.jpg']`
4. `PredictButton` -> `#predict-btn`
5. `BatchCompleteText` -> text anchor near batch completion text (or map `#predict-error-text` + result banner)
6. `ResultListText` -> `#result-list`
7. `HistoryTabButton` -> `#tab-history`
8. `HistoryTotalText` -> `#history-total`
9. `HistoryCountBadgeText` -> `#history-count`

Notes:

1. For text elements, use "Get Text" capable targets.
2. If any selector is unstable, use strict anchors plus ancestor container.
3. Keep element names identical to avoid code edits.
4. For `AuthScreen` window selector, do not hardcode page title to `Home`; use wildcard title like `VeggieAI | * - Google Chrome`.

## 3) Run Arguments

In UiPath Studio, run `Execute` with arguments like:

1. `email`: test account email
2. `password`: test account password
3. `fullName`: fallback sign-up name
4. `captchaCode`: required when captcha is visible
5. `authPageUrl`: full URL to auth page, for example `http://127.0.0.1:5000/auth` (recommended)
6. `captchaRequired`: usually `true`
7. `allowSignUpFallback`: set `true` if account may not exist yet
8. `allowDevOtp`: set `true` for development OTP display mode
9. `exerciseForgotPassword`: set `true` to validate forgot-password send-link flow

## 4) Captcha and OTP for unattended runs

The app enforces captcha and OTP by design.

For unattended automation:

1. Enable development helpers in backend env:
   1. `CAPTCHA_DEV_MODE=true`
   2. `OTP_DEV_MODE=true`
2. Feed `captchaCode` from `/api/auth/captcha` response field `captcha_text`.
3. OTP is read from `#auth-dev-otp-text` by the workflow.

If dev helpers are off, human-in-the-loop is required for captcha/OTP.

## 5) Credential Safety

Do not hardcode real credentials in code.

Use:

1. UiPath Orchestrator Assets (Credential type), or
2. Windows Credential Manager + UiPath secure activities.

Then pass secure values into workflow arguments at runtime.
