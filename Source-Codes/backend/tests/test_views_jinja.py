"""Jinja page access tests for public/protected route behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.e2e]


def test_public_pages_are_accessible_without_login(client):
    """Allow anonymous access to homepage and auth page."""
    assert client.get("/").status_code == 200
    assert client.get("/auth").status_code == 200


def test_protected_pages_redirect_without_login(client):
    """Redirect anonymous users to `/auth` for protected pages."""
    for path in ["/predict", "/prices", "/profile", "/history"]:
        response = client.get(path)
        assert response.status_code in {301, 302}
        location = response.headers.get("Location", "")
        assert "/auth" in location


def test_session_bridge_allows_jinja_page_access(client):
    """Allow Jinja page access after exchanging JWT for Flask session."""
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login.status_code == 200
    token = login.get_json()["data"]["token"]

    bridge = client.post("/web/session/login", json={"token": token})
    assert bridge.status_code == 200

    assert client.get("/predict").status_code == 200
    assert client.get("/prices").status_code == 200
    assert client.get("/profile").status_code == 200


def test_flask_app_uses_jinja_templates_and_sqlite_config(client):
    """Use Jinja templates and a SQLite database path in Flask config."""
    app = client.application
    assert app.jinja_env is not None
    assert "webapp/app/templates" in Path(app.template_folder).as_posix()
    assert app.config["DATABASE_PATH"].endswith(".db")


def test_theme_preference_is_persisted_for_server_rendered_pages(client):
    """Persist theme preference and render it on subsequent Jinja responses."""
    update = client.post("/web/theme", json={"theme": "dark"})
    assert update.status_code == 200
    assert "veggie-theme=dark" in (update.headers.get("Set-Cookie") or "")

    homepage = client.get("/")
    assert homepage.status_code == 200
    html = homepage.get_data(as_text=True)
    assert 'meta name="color-scheme" content="dark light"' in html
    assert 'meta name="theme-color" content="#000000"' in html
    assert 'class="theme-init dark"' in html
    assert 'data-theme="dark"' in html


def test_default_theme_is_dark_without_saved_preference(client):
    """Default first paint to dark when no theme exists yet."""
    homepage = client.get("/")
    assert homepage.status_code == 200
    html = homepage.get_data(as_text=True)
    assert 'meta name="color-scheme" content="dark light"' in html
    assert 'meta name="theme-color" content="#000000"' in html
    assert 'class="theme-init dark"' in html
    assert 'data-theme="dark"' in html


def test_light_theme_preference_is_rendered_on_server_response(client):
    """Render light mode immediately when the stored preference is light."""
    update = client.post("/web/theme", json={"theme": "light"})
    assert update.status_code == 200
    assert "veggie-theme=light" in (update.headers.get("Set-Cookie") or "")

    homepage = client.get("/")
    assert homepage.status_code == 200
    html = homepage.get_data(as_text=True)
    assert 'meta name="color-scheme" content="light dark"' in html
    assert 'meta name="theme-color" content="#f9fafb"' in html
    assert 'class="theme-init light"' in html
    assert 'data-theme="light"' in html


def test_theme_update_rejects_invalid_value(client):
    """Reject unsupported theme values."""
    update = client.post("/web/theme", json={"theme": "solarized"})
    assert update.status_code == 400


def test_theme_endpoint_supports_get(client):
    """Expose the effective server-side theme via GET for bootstrap compatibility."""
    initial = client.get("/web/theme")
    assert initial.status_code == 200
    assert initial.get_json()["data"]["theme"] == "dark"

    update = client.post("/web/theme", json={"theme": "light"})
    assert update.status_code == 200

    current = client.get("/web/theme")
    assert current.status_code == 200
    assert current.get_json()["data"]["theme"] == "light"


def test_theme_bootstrap_includes_no_flash_guards(client):
    """Ship CSP-safe theme boot assets and no-flash guards."""
    homepage = client.get("/")
    assert homepage.status_code == 200
    html = homepage.get_data(as_text=True)
    assert "css/theme-boot.css?v=" in html
    assert "js/theme-boot.js?v=" in html
    assert "@media (prefers-color-scheme: light)" not in html
    assert 'class="theme-init dark"' in html
    assert 'data-theme="dark"' in html
    assert 'data-server-theme="dark"' in html
    assert "html.theme-init.route-transition-pending body" not in html
    assert "veggie-nav-transition" not in html
    assert '"themeEndpoint": "/web/theme"' in html


def test_route_transition_pending_state_css_is_not_inlined(client):
    """Avoid shipping inline pending-state CSS hooks in the HTML document."""
    homepage = client.get("/")
    assert homepage.status_code == 200
    html = homepage.get_data(as_text=True)
    assert "html.route-transition-pending #page-shell" not in html


def test_route_transition_shell_is_rendered(client):
    """Render transition shell markup for page-to-page animation."""
    homepage = client.get("/")
    assert homepage.status_code == 200
    html = homepage.get_data(as_text=True)
    assert 'id="route-transition-overlay"' in html
    assert 'id="route-transition-panel"' in html
    assert 'id="route-transition-scan-line"' in html
    assert 'id="route-transition-logo"' in html


def test_page_level_scripts_are_cache_busted(client):
    """Append a version query to page-level scripts for reliable rollouts."""
    auth_page = client.get("/auth")
    assert auth_page.status_code == 200
    html = auth_page.get_data(as_text=True)
    assert "js/auth.js?v=" in html


def test_auth_page_has_terms_checkbox(client):
    """Render a terms checkbox on the auth page for signup."""
    auth_page = client.get("/auth")
    assert auth_page.status_code == 200
    html = auth_page.get_data(as_text=True)
    assert 'id="field-terms"' in html
    assert 'id="agree-terms"' in html


def test_auth_page_has_forgot_password_flow_controls(client):
    """Render forgot/reset password controls on the auth page."""
    auth_page = client.get("/auth")
    assert auth_page.status_code == 200
    html = auth_page.get_data(as_text=True)
    assert 'id="forgot-password-link"' in html
    assert 'id="forgot-fields"' in html
    assert 'id="reset-fields"' in html


def test_auth_page_disables_caching(client):
    """Ensure auth page always serves fresh markup and script versions."""
    auth_page = client.get("/auth")
    assert auth_page.status_code == 200
    cache_control = auth_page.headers.get("Cache-Control", "")
    pragma = auth_page.headers.get("Pragma", "")
    assert "no-store" in cache_control
    assert "no-cache" in pragma


def test_favicon_route_is_available(client):
    """Expose `/favicon.ico` for browser favicon discovery."""
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert "image/x-icon" in (response.headers.get("Content-Type") or "")
    assert "no-store" in (response.headers.get("Cache-Control") or "")
