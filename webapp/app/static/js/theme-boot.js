(function () {
  var root = document.documentElement;
  if (!root) {
    return;
  }

  root.classList.add("theme-init");

  function normalizeTheme(value) {
    return value === "dark" || value === "light" ? value : null;
  }

  function setThemeClass(nextTheme) {
    var classes = (root.className || "").split(/\s+/);
    var filtered = [];
    for (var index = 0; index < classes.length; index += 1) {
      var current = classes[index];
      if (!current || current === "dark" || current === "light") {
        continue;
      }
      filtered.push(current);
    }
    filtered.push(nextTheme);
    root.className = filtered.join(" ");
  }

  function readCookieTheme() {
    try {
      var cookiePairs = (document.cookie || "").split(";");
      var resolved = null;
      for (var index = 0; index < cookiePairs.length; index += 1) {
        var pair = cookiePairs[index].trim();
        if (pair.indexOf("veggie-theme=") === 0) {
          var value = decodeURIComponent(pair.slice("veggie-theme=".length));
          var normalized = normalizeTheme(value);
          if (normalized) {
            // Keep the last valid cookie value to avoid stale duplicates winning.
            resolved = normalized;
          }
        }
      }
      return resolved;
    } catch (_) {
      return null;
    }
    return null;
  }

  function readStoredTheme() {
    try {
      if (window.localStorage) {
        var value = window.localStorage.getItem("veggie-theme");
        return normalizeTheme(value);
      }
    } catch (_) {
      return null;
    }
    return null;
  }

  var serverTheme = normalizeTheme(root.getAttribute("data-server-theme"));
  var htmlTheme = normalizeTheme(root.getAttribute("data-theme"));
  var storedTheme = readStoredTheme();
  var cookieTheme = readCookieTheme();
  var theme =
    storedTheme === "dark" || storedTheme === "light"
      ? storedTheme
      : cookieTheme === "dark" || cookieTheme === "light"
        ? cookieTheme
        : serverTheme === "dark" || serverTheme === "light"
          ? serverTheme
        : htmlTheme === "dark" || htmlTheme === "light"
          ? htmlTheme
          : "dark";

  setThemeClass(theme);
  root.setAttribute("data-theme", theme);
  root.style.colorScheme = theme;
  root.style.backgroundColor = theme === "dark" ? "#000000" : "#f9fafb";

  var colorSchemeMeta = document.querySelector('meta[name="color-scheme"]');
  if (colorSchemeMeta) {
    colorSchemeMeta.setAttribute("content", theme === "dark" ? "dark light" : "light dark");
  }

  var themeColorMeta = document.querySelector('meta[name="theme-color"]');
  if (themeColorMeta) {
    themeColorMeta.setAttribute("content", theme === "dark" ? "#000000" : "#f9fafb");
  }

  try {
    if (window.localStorage) {
      window.localStorage.setItem("veggie-theme", theme);
    }
  } catch (_) {
    // Ignore storage failures.
  }

  try {
    document.cookie = "veggie-theme=" + encodeURIComponent(theme) + "; Path=/; Max-Age=31536000; SameSite=Lax";
    // Clear older scoped cookies so future reads are deterministic.
    document.cookie = "veggie-theme=; Path=/web; Max-Age=0; SameSite=Lax";
    document.cookie = "veggie-theme=; Path=/web/; Max-Age=0; SameSite=Lax";
  } catch (_) {
    // Ignore cookie failures.
  }

  window.__VEGGIE_THEME_BOOT__ = theme;

  var releaseThemeInit = function () {
    root.classList.remove("theme-init");
  };

  if (window.requestAnimationFrame) {
    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(releaseThemeInit);
    });
  } else {
    window.setTimeout(releaseThemeInit, 0);
  }

  window.setTimeout(releaseThemeInit, 1200);
  window.addEventListener(
    "load",
    function () {
      releaseThemeInit();
    },
    { once: true },
  );
})();
