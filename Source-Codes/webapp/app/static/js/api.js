(function () {
  const ctx = window.APP_CONTEXT || {};
  const API_BASE = (ctx.apiBase || "").replace(/\/$/, "");

  function getToken() {
    return (window.APP_CONTEXT && window.APP_CONTEXT.token) || "";
  }

  function navigate(path) {
    if (window.VeggieNav && typeof window.VeggieNav.navigate === "function") {
      window.VeggieNav.navigate(path);
      return;
    }
    window.location.href = path;
  }

  function withTokenQuery(path) {
    const token = getToken();
    if (!token) {
      return `${API_BASE}${path}`;
    }
    const sep = path.includes("?") ? "&" : "?";
    return `${API_BASE}${path}${sep}token=${encodeURIComponent(token)}`;
  }

  async function apiRequest(path, options) {
    const opts = options || {};
    const headers = new Headers(opts.headers || {});
    const method = opts.method || "GET";
    const isForm = Boolean(opts.isForm);
    const useAuth = opts.auth !== false;
    const token = getToken();

    if (useAuth && token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    if (!isForm && opts.body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    const response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: opts.body,
      credentials: "same-origin",
    });

    const payload = await response.json().catch(function () {
      return {};
    });

    if (!response.ok) {
      const message = payload && payload.error && payload.error.message ? payload.error.message : "Request failed";
      if (response.status === 401 && useAuth) {
        navigate("/auth");
      }
      const err = new Error(message);
      err.status = response.status;
      err.payload = payload;
      throw err;
    }

    return payload;
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function setFeedback(node, message, kind) {
    if (!node) return;
    if (!message) {
      node.classList.add("hidden");
      node.classList.remove("error", "success");
      node.textContent = "";
      return;
    }
    node.classList.remove("hidden", "error", "success");
    if (kind === "error") {
      node.classList.add("error");
    } else if (kind === "success") {
      node.classList.add("success");
    }
    node.textContent = message;
  }

  function ensureAuthenticated() {
    if (!getToken()) {
      navigate("/auth");
      return false;
    }
    return true;
  }

  window.webApi = {
    apiRequest,
    withTokenQuery,
    escapeHtml,
    setFeedback,
    ensureAuthenticated,
  };
})();
