# Wireframes

Canonical wireframe manifest:

- `docs/wireframes/veggieai_frontend_wireframe.xml`

Per-page XML wireframes:

- `docs/wireframes/global_shell_wireframe.xml`
- `docs/wireframes/home_wireframe.xml`
- `docs/wireframes/auth_wireframe.xml`
- `docs/wireframes/predict_wireframe.xml`
- `docs/wireframes/prices_wireframe.xml`
- `docs/wireframes/profile_wireframe.xml`
- `docs/wireframes/history_wireframe.xml`

Coverage:

- Global shell (navbar, chat, footer)
- Home (`/`)
- Auth (`/auth`) with sign-in/sign-up/OTP/captcha/forgot/reset states
- Classify (`/predict`) including camera modal and history tab state
- Prices (`/prices`) with centered modal
- Profile (`/profile`) with delete confirmation
- History route (`/history`) equivalent state after redirect
- Legacy `/web/*` redirect mapping

If screenshots are added later, keep them as supporting evidence only. XML remains the source of truth.
