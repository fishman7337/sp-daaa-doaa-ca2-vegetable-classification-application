(function () {
  const api = window.webApi || {};
  const appContext = window.APP_CONTEXT || {};
  const root = document.documentElement;

  function createIcons(target) {
    if (!window.lucide || typeof window.lucide.createIcons !== "function") {
      return;
    }
    try {
      window.lucide.createIcons({
        icons: window.lucide.icons,
        attrs: {
          "stroke-width": 2,
        },
        nameAttr: "data-lucide",
        ...(target ? { root: target } : {}),
      });
    } catch (_) {
      // Ignore icon refresh failures to avoid breaking interaction flows.
    }
  }

  function applyTheme(theme) {
    const next = theme === "dark" ? "dark" : "light";
    const options = arguments.length > 1 && arguments[1] ? arguments[1] : {};
    const persist = options.persist !== false;
    const syncServer = options.syncServer !== false;
    const classes = (root.className || "")
      .split(/\s+/)
      .filter(function (item) {
        return item && item !== "dark" && item !== "light";
      });
    classes.push(next);
    root.className = classes.join(" ");
    root.setAttribute("data-theme", next);
    root.style.colorScheme = next;
    root.style.backgroundColor = next === "dark" ? "#000000" : "#f9fafb";
    const colorSchemeMeta = document.querySelector('meta[name="color-scheme"]');
    if (colorSchemeMeta) {
      colorSchemeMeta.setAttribute("content", next === "dark" ? "dark light" : "light dark");
    }
    const themeColorMeta = document.querySelector('meta[name="theme-color"]');
    if (themeColorMeta) {
      themeColorMeta.setAttribute("content", next === "dark" ? "#000000" : "#f9fafb");
    }
    if (persist) {
      try {
        localStorage.setItem("veggie-theme", next);
      } catch (_) {
        // Ignore storage write failures and keep in-memory theme state.
      }
      try {
        document.cookie = `veggie-theme=${encodeURIComponent(next)}; Path=/; Max-Age=31536000; SameSite=Lax`;
        // Clear older scoped cookies so navigation never falls back to stale values.
        document.cookie = "veggie-theme=; Path=/web; Max-Age=0; SameSite=Lax";
        document.cookie = "veggie-theme=; Path=/web/; Max-Age=0; SameSite=Lax";
      } catch (_) {
        // Ignore cookie write failures and keep in-memory theme state.
      }
    }
    const themeEndpoint = String(appContext.themeEndpoint || "").trim();
    if (syncServer && themeEndpoint) {
      fetch(themeEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        keepalive: true,
        cache: "no-store",
        body: JSON.stringify({ theme: next }),
      }).catch(function () {
        return null;
      });
    }

    const sun = document.getElementById("theme-icon-sun");
    const moon = document.getElementById("theme-icon-moon");
    if (sun && moon) {
      if (next === "dark") {
        sun.className = "absolute inset-0 w-5 h-5 text-amber-500 transition-all duration-300 rotate-0 scale-100 opacity-100";
        moon.className = "absolute inset-0 w-5 h-5 text-slate-700 dark:text-slate-400 transition-all duration-300 rotate-90 scale-0 opacity-0";
      } else {
        sun.className = "absolute inset-0 w-5 h-5 text-amber-500 transition-all duration-300 -rotate-90 scale-0 opacity-0";
        moon.className = "absolute inset-0 w-5 h-5 text-slate-700 dark:text-slate-400 transition-all duration-300 rotate-0 scale-100 opacity-100";
      }
    }
  }

  function initTheme() {
    const bootTheme = window.__VEGGIE_THEME_BOOT__;
    const htmlTheme = root.getAttribute("data-theme");
    const resolvedTheme =
      (bootTheme === "dark" || bootTheme === "light"
        ? bootTheme
        : htmlTheme === "dark" || htmlTheme === "light"
          ? htmlTheme
          : "dark");
    applyTheme(resolvedTheme, { persist: false, syncServer: false });

    const toggle = document.getElementById("theme-toggle");
    if (toggle) {
      toggle.addEventListener("click", function () {
        const current = root.getAttribute("data-theme") || "light";
        applyTheme(current === "dark" ? "light" : "dark");
      });
    }

    window.requestAnimationFrame(function () {
      root.classList.remove("theme-init");
    });
    window.setTimeout(function () {
      root.classList.remove("theme-init");
    }, 1200);
    window.addEventListener(
      "load",
      function () {
        root.classList.remove("theme-init");
      },
      { once: true },
    );
  }

  function initNavbar() {
    const navbar = document.getElementById("main-navbar");
    const navbarBg = document.getElementById("main-navbar-bg");
    const mobileToggle = document.getElementById("mobile-menu-toggle");
    const mobileMenu = document.getElementById("mobile-menu");
    const menuIcon = document.getElementById("mobile-icon-menu");
    const closeIcon = document.getElementById("mobile-icon-close");

    const profileRoot = document.getElementById("profile-menu-root");
    const profileToggle = document.getElementById("profile-menu-toggle");
    const profileMenu = document.getElementById("profile-menu");
    const profileChevron = document.getElementById("profile-menu-chevron");

    let mobileOpen = false;
    let profileOpen = false;

    function updateNavbarStyle() {
      if (!navbar || !navbarBg) {
        return;
      }
      const scrolled = window.scrollY > 20;
      const active = scrolled || mobileOpen;
      navbar.classList.toggle("py-3", active);
      navbar.classList.toggle("py-5", !active);
      navbarBg.className = active
        ? "absolute inset-0 transition-all duration-500 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl border-b border-gray-200/50 dark:border-gray-800/50 shadow-lg shadow-gray-900/5 dark:shadow-black/10"
        : "absolute inset-0 transition-all duration-500 bg-transparent";
    }

    function setMobileState(open) {
      if (!mobileMenu) {
        return;
      }
      mobileOpen = Boolean(open);

      if (menuIcon && closeIcon) {
        if (mobileOpen) {
          menuIcon.classList.add("-rotate-90", "scale-0", "opacity-0");
          menuIcon.classList.remove("rotate-0", "scale-100", "opacity-100");
          closeIcon.classList.remove("rotate-90", "scale-0", "opacity-0");
          closeIcon.classList.add("rotate-0", "scale-100", "opacity-100");
        } else {
          closeIcon.classList.add("rotate-90", "scale-0", "opacity-0");
          closeIcon.classList.remove("rotate-0", "scale-100", "opacity-100");
          menuIcon.classList.remove("-rotate-90", "scale-0", "opacity-0");
          menuIcon.classList.add("rotate-0", "scale-100", "opacity-100");
        }
      }

      if (mobileOpen) {
        mobileMenu.classList.remove("hidden");
        if (window.gsap) {
          window.gsap.fromTo(
            mobileMenu,
            { opacity: 0, height: 0 },
            { opacity: 1, height: "auto", duration: 0.35, ease: "power3.out" },
          );
          window.gsap.fromTo(
            mobileMenu.children,
            { opacity: 0, x: -20 },
            { opacity: 1, x: 0, duration: 0.25, stagger: 0.05, ease: "power2.out", delay: 0.08 },
          );
        }
      } else {
        if (window.gsap) {
          window.gsap.to(mobileMenu, {
            opacity: 0,
            height: 0,
            duration: 0.22,
            ease: "power2.in",
            onComplete: function () {
              mobileMenu.classList.add("hidden");
              mobileMenu.style.removeProperty("height");
              mobileMenu.style.removeProperty("opacity");
            },
          });
        } else {
          mobileMenu.classList.add("hidden");
        }
      }

      updateNavbarStyle();
    }

    function setProfileState(open) {
      if (!profileMenu) {
        return;
      }
      profileOpen = Boolean(open);
      profileMenu.classList.toggle("hidden", !profileOpen);
      if (profileChevron) {
        profileChevron.classList.toggle("rotate-180", profileOpen);
      }
    }

    if (mobileToggle && mobileMenu) {
      mobileToggle.addEventListener("click", function () {
        setMobileState(!mobileOpen);
      });

      mobileMenu.querySelectorAll("a").forEach(function (link) {
        link.addEventListener("click", function () {
          setMobileState(false);
        });
      });
    }

    if (profileRoot && profileToggle && profileMenu) {
      profileToggle.addEventListener("click", function (event) {
        event.preventDefault();
        setProfileState(!profileOpen);
      });

      document.addEventListener("mousedown", function (event) {
        if (!profileRoot.contains(event.target)) {
          setProfileState(false);
        }
      });
    }

    window.addEventListener("scroll", updateNavbarStyle, { passive: true });
    updateNavbarStyle();
  }

  function bindLogout() {
    function handleLogout() {
      const logoutEndpoint = String(appContext.sessionLogoutEndpoint || "/web/session/logout").trim();
      fetch(logoutEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: "{}",
      })
        .catch(function () {
          return null;
        })
        .finally(function () {
          if (window.VeggieNav && typeof window.VeggieNav.navigate === "function") {
            window.VeggieNav.navigate("/");
            return;
          }
          window.location.href = "/";
        });
    }

    ["profile-logout-btn", "mobile-logout-btn"].forEach(function (id) {
      const button = document.getElementById(id);
      if (button) {
        button.addEventListener("click", handleLogout);
      }
    });
  }

  function resolveNavbarAvatar() {
    const avatar = document.getElementById("navbar-avatar");
    const fallback = document.getElementById("navbar-avatar-fallback");
    if (!avatar || !fallback) {
      return;
    }

    const raw = String(avatar.getAttribute("data-avatar") || "").trim();
    if (!raw) {
      avatar.classList.add("hidden");
      fallback.classList.remove("hidden");
      return;
    }

    let src = raw;
    if (raw.startsWith("/api/") && api.withTokenQuery) {
      src = api.withTokenQuery(raw);
    }
    avatar.src = src;
    avatar.classList.remove("hidden");
    fallback.classList.add("hidden");
  }

  function initHomeEffects() {
    if ((window.APP_CONTEXT && window.APP_CONTEXT.page) !== "home") {
      return;
    }

    const words = ["TOMATOES", "BROCCOLI", "CARROTS", "SPINACH", "PEPPERS", "CABBAGE", "LETTUCE", "ONIONS"];
    const typed = document.getElementById("hero-typed");
    const cursor = document.getElementById("hero-cursor");

    if (typed) {
      let wordIndex = 0;
      let deleting = false;
      let text = "";

      function tick() {
        const current = words[wordIndex];
        const speed = deleting ? 50 : 100;

        if (!deleting && text === current) {
          setTimeout(function () {
            deleting = true;
            tick();
          }, 1500);
          return;
        }

        if (deleting && text.length === 0) {
          deleting = false;
          wordIndex = (wordIndex + 1) % words.length;
          setTimeout(tick, 250);
          return;
        }

        text = deleting ? current.slice(0, text.length - 1) : current.slice(0, text.length + 1);
        typed.textContent = text;
        setTimeout(tick, speed);
      }

      tick();
    }

    if (cursor) {
      setInterval(function () {
        cursor.classList.toggle("opacity-0");
      }, 530);
    }

    if (window.gsap) {
      const heroTimeline = window.gsap.timeline({ delay: 0.35 });
      heroTimeline
        .fromTo(
          "#hero-title",
          { opacity: 0, y: 40, filter: "blur(10px)" },
          { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.8, ease: "power3.out" },
        )
        .fromTo(
          "#hero-subtitle",
          { opacity: 0, y: 30 },
          { opacity: 1, y: 0, duration: 0.6, ease: "power2.out" },
          "-=0.4",
        )
        .fromTo("#hero-cta", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5, ease: "power2.out" }, "-=0.3")
        .fromTo(
          "#hero-showcase",
          { opacity: 0, scale: 0.9, rotateY: 20 },
          { opacity: 1, scale: 1, rotateY: 0, duration: 1, ease: "power2.out" },
          "-=0.5",
        )
        .fromTo(
          "#hero-stats > *",
          { opacity: 0, y: 20 },
          { opacity: 1, y: 0, duration: 0.4, stagger: 0.1, ease: "power2.out" },
          "-=0.5",
        );

      const lines = document.querySelectorAll("#hero-scan-lines > *");
      if (lines.length > 0) {
        window.gsap.to(lines, {
          yPercent: 100,
          duration: 2,
          stagger: 0.3,
          repeat: -1,
          ease: "none",
        });
      }

      const imageScanner = document.getElementById("hero-image-scanner");
      if (imageScanner && imageScanner.parentElement) {
        window.gsap.to(imageScanner, {
          y: function () {
            return Math.max(24, imageScanner.parentElement.clientHeight - imageScanner.clientHeight - 8);
          },
          duration: 2.4,
          ease: "sine.inOut",
          yoyo: true,
          repeat: -1,
        });
      }

      if (window.ScrollTrigger) {
        window.gsap.fromTo(
          "#features-title",
          { opacity: 0, y: 60 },
          {
            opacity: 1,
            y: 0,
            duration: 0.9,
            ease: "power3.out",
            scrollTrigger: { trigger: "#features-title", start: "top 85%" },
          },
        );

        window.gsap.fromTo(
          "#features-grid > *",
          { opacity: 0, y: 60, rotateX: -15 },
          {
            opacity: 1,
            y: 0,
            rotateX: 0,
            duration: 0.8,
            stagger: { each: 0.08, grid: "auto", from: "start" },
            ease: "power3.out",
            scrollTrigger: { trigger: "#features-grid", start: "top 80%" },
          },
        );

        ["#how-title", "#showcase-title", "#cta-content"].forEach(function (selector) {
          window.gsap.fromTo(
            selector,
            { opacity: 0, y: 45 },
            {
              opacity: 1,
              y: 0,
              duration: 0.8,
              ease: "power3.out",
              scrollTrigger: { trigger: selector, start: "top 85%" },
            },
          );
        });

        window.gsap.fromTo(
          "#how-steps > *",
          { opacity: 0, x: -50 },
          {
            opacity: 1,
            x: 0,
            duration: 0.6,
            stagger: 0.2,
            ease: "power2.out",
            scrollTrigger: { trigger: "#how-steps", start: "top 80%" },
          },
        );

        window.gsap.fromTo(
          "#how-demo",
          { opacity: 0, scale: 0.9 },
          {
            opacity: 1,
            scale: 1,
            duration: 0.8,
            ease: "power2.out",
            scrollTrigger: { trigger: "#how-demo", start: "top 80%" },
          },
        );

        window.gsap.fromTo(
          "#showcase-grid > *",
          { opacity: 0, y: 30, scale: 0.95 },
          {
            opacity: 1,
            y: 0,
            scale: 1,
            duration: 0.5,
            stagger: { each: 0.08, grid: "auto", from: "start" },
            ease: "power2.out",
            scrollTrigger: { trigger: "#showcase-grid", start: "top 80%" },
          },
        );
      }
    }
  }

  function initPageTransitions() {
    const root = document.documentElement;
    const shell = document.getElementById("page-shell");
    const overlayPanel = document.getElementById("route-transition-panel");
    const scanLine = document.getElementById("route-transition-scan-line");
    const logo = document.getElementById("route-transition-logo");
    if (!root || !shell || !overlayPanel || !scanLine || !logo) {
      return;
    }

    const prefersReducedMotion =
      !!window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const hasGsap = !!window.gsap && typeof window.gsap.timeline === "function";
    let navigating = false;
    let entryTimeline = null;
    let exitTimeline = null;
    let entryRecoveryTimer = 0;

    function clearTransitionFlag() {
      root.classList.remove("route-transition-pending");
      try {
        if (window.sessionStorage) {
          window.sessionStorage.removeItem("veggie-nav-transition");
        }
      } catch (_) {
        // Ignore unavailable session storage.
      }
    }

    function clearEntryRecoveryTimer() {
      if (!entryRecoveryTimer) {
        return;
      }
      window.clearTimeout(entryRecoveryTimer);
      entryRecoveryTimer = 0;
    }

    function setIdleState() {
      shell.style.opacity = "1";
      shell.style.transform = "translate3d(0, 0, 0)";
      overlayPanel.style.transform = "scaleY(0)";
      overlayPanel.style.transformOrigin = "top";
      logo.style.opacity = "0";
      logo.style.transform = "scale(0.5)";
      scanLine.style.transform = "translateY(-100%)";
    }

    function finalizeEntryTransition() {
      clearEntryRecoveryTimer();
      clearTransitionFlag();
      navigating = false;
      setIdleState();
    }

    function motionDuration(full) {
      if (prefersReducedMotion) {
        return Math.min(full, 220);
      }
      return full;
    }

    function waitFor(durationMs) {
      const ms = Math.max(0, Number(durationMs) || 0);
      if (!ms) {
        return Promise.resolve();
      }
      return new Promise(function (resolve) {
        window.setTimeout(resolve, ms);
      });
    }

    function applyFrameStyles(element, frame) {
      if (!element || !element.style || !frame) {
        return;
      }
      if (frame.transform != null) {
        element.style.transform = String(frame.transform);
      }
      if (frame.transformOrigin != null) {
        element.style.transformOrigin = String(frame.transformOrigin);
      }
      if (frame.opacity != null) {
        element.style.opacity = String(frame.opacity);
      }
    }

    function animateElement(element, keyframes, options) {
      const opts = {
        fill: "forwards",
        easing: "ease",
        ...options,
      };
      let durationMs = 0;
      if (typeof opts.duration === "number") {
        opts.duration = motionDuration(opts.duration);
        durationMs = opts.duration;
      }

      const lastFrame = Array.isArray(keyframes) && keyframes.length ? keyframes[keyframes.length - 1] : null;
      if (!element) {
        return waitFor(durationMs);
      }

      if (typeof element.animate !== "function") {
        applyFrameStyles(element, lastFrame);
        return waitFor(durationMs);
      }

      try {
        const animation = element.animate(keyframes, opts);
        return animation.finished.catch(function () {
          applyFrameStyles(element, lastFrame);
          return waitFor(durationMs);
        });
      } catch (_) {
        applyFrameStyles(element, lastFrame);
        return waitFor(durationMs);
      }
    }

    async function playEntryTransitionFallback(pending) {
      if (!pending) {
        setIdleState();
        return;
      }

      overlayPanel.style.transformOrigin = "bottom";
      overlayPanel.style.transform = "scaleY(1)";
      shell.style.opacity = "0";
      shell.style.transform = "translate3d(0, 10px, 0)";
      logo.style.opacity = "0";
      logo.style.transform = "scale(0.5)";
      scanLine.style.transform = "translateY(-100%)";

      await Promise.all([
        animateElement(
          logo,
          [{ transform: "scale(0.5)", opacity: 0 }, { transform: "scale(1)", opacity: 1 }],
          { duration: 280, easing: "cubic-bezier(0.34, 1.56, 0.64, 1)" },
        ),
        animateElement(
          scanLine,
          [{ transform: "translateY(-100%)" }, { transform: "translateY(100%)" }],
          { duration: 500, easing: "linear" },
        ),
      ]);
      await animateElement(
        logo,
        [{ transform: "scale(1)", opacity: 1 }, { transform: "scale(0.5)", opacity: 0 }],
        { duration: 190, easing: "cubic-bezier(0.4, 0, 1, 1)" },
      );
      await Promise.all([
        animateElement(
          overlayPanel,
          [{ transform: "scaleY(1)", transformOrigin: "bottom" }, { transform: "scaleY(0)", transformOrigin: "bottom" }],
          { duration: 360, easing: "cubic-bezier(0.4, 0, 0.2, 1)" },
        ),
        animateElement(
          shell,
          [{ opacity: 0, transform: "translate3d(0, 10px, 0)" }, { opacity: 1, transform: "translate3d(0, 0, 0)" }],
          { duration: 320, easing: "cubic-bezier(0.2, 0, 0, 1)" },
        ),
      ]);
      setIdleState();
    }

    async function playExitTransitionFallback(nextHref) {
      overlayPanel.style.transformOrigin = "top";
      overlayPanel.style.transform = "scaleY(0)";
      shell.style.opacity = "1";
      shell.style.transform = "translate3d(0, 0, 0)";
      logo.style.opacity = "0";
      logo.style.transform = "scale(0.5)";
      scanLine.style.transform = "translateY(-100%)";

      await Promise.all([
        animateElement(
          overlayPanel,
          [{ transform: "scaleY(0)", transformOrigin: "top" }, { transform: "scaleY(1)", transformOrigin: "top" }],
          { duration: 340, easing: "cubic-bezier(0.4, 0, 0.2, 1)" },
        ),
        animateElement(
          shell,
          [{ opacity: 1, transform: "translate3d(0, 0, 0)" }, { opacity: 0, transform: "translate3d(0, 10px, 0)" }],
          { duration: 280, easing: "cubic-bezier(0.4, 0, 1, 1)" },
        ),
      ]);
      window.location.assign(nextHref);
    }

    function playEntryTransition() {
      clearEntryRecoveryTimer();
      if (entryTimeline) {
        entryTimeline.kill();
        entryTimeline = null;
      }

      const pending = root.classList.contains("route-transition-pending");
      if (!hasGsap) {
        void playEntryTransitionFallback(pending).finally(function () {
          finalizeEntryTransition();
        });
        return;
      }

      if (!pending) {
        setIdleState();
        clearTransitionFlag();
        return;
      }

      entryTimeline = window.gsap.timeline({
        onComplete: function () {
          entryTimeline = null;
          finalizeEntryTransition();
        },
        onInterrupt: function () {
          entryTimeline = null;
          finalizeEntryTransition();
        },
      });
      entryTimeline
        .set(overlayPanel, { scaleY: 1, transformOrigin: "bottom" })
        .set(shell, { autoAlpha: 0, y: 10 })
        .set(logo, { scale: 0.5, autoAlpha: 0 })
        .set(scanLine, { yPercent: -100 })
        .to(logo, { scale: 1, autoAlpha: 1, duration: 0.28, ease: "back.out(1.7)" })
        .to(scanLine, { yPercent: 100, duration: 0.5, ease: "none" }, "-=0.2")
        .to(logo, { scale: 0.5, autoAlpha: 0, duration: 0.2, ease: "power2.in" }, "+=0.08")
        .to(overlayPanel, { scaleY: 0, transformOrigin: "bottom", duration: 0.38, ease: "power2.inOut" }, "-=0.06")
        .to(shell, { autoAlpha: 1, y: 0, duration: 0.34, ease: "power2.out" }, "-=0.2");

      entryRecoveryTimer = window.setTimeout(function () {
        finalizeEntryTransition();
      }, motionDuration(2600));
    }

    function navigateWithTransition(nextHref) {
      if (navigating) {
        return;
      }
      navigating = true;
      try {
        if (window.sessionStorage) {
          const transitionMeta = {
            startedAt: Date.now(),
            from: window.location.pathname + window.location.search + window.location.hash,
            to: "",
          };
          try {
            transitionMeta.to = new URL(nextHref, window.location.href).pathname;
          } catch (_) {
            transitionMeta.to = String(nextHref || "");
          }
          window.sessionStorage.setItem("veggie-nav-transition", JSON.stringify(transitionMeta));
        }
      } catch (_) {
        // Ignore unavailable session storage.
      }

      if (!hasGsap) {
        void playExitTransitionFallback(nextHref);
        return;
      }

      if (entryTimeline) {
        entryTimeline.kill();
        entryTimeline = null;
      }
      if (exitTimeline) {
        exitTimeline.kill();
        exitTimeline = null;
      }

      exitTimeline = window.gsap.timeline({
        onComplete: function () {
          window.location.assign(nextHref);
        },
      });

      exitTimeline
        .set(overlayPanel, { scaleY: 0, transformOrigin: "top" })
        .set(shell, { autoAlpha: 1, y: 0 })
        .set(logo, { scale: 0.5, autoAlpha: 0 })
        .set(scanLine, { yPercent: -100 })
        .to(overlayPanel, { scaleY: 1, duration: 0.34, ease: "power2.inOut" })
        .to(logo, { scale: 1, autoAlpha: 1, duration: 0.26, ease: "back.out(1.7)" }, "-=0.12")
        .to(scanLine, { yPercent: 100, duration: 0.5, ease: "none" }, "-=0.18")
        .to(logo, { scale: 0.5, autoAlpha: 0, duration: 0.2, ease: "power2.in" }, "+=0.08")
        .to(shell, { autoAlpha: 0, y: 10, duration: 0.28, ease: "power2.in" }, "<");

      window.setTimeout(function () {
        if (navigating) {
          window.location.assign(nextHref);
        }
      }, motionDuration(1400));
    }

    function resolveTransitionHref(anchor) {
      if (!anchor) {
        return null;
      }
      if (anchor.hasAttribute("download") || anchor.hasAttribute("data-no-transition")) {
        return null;
      }
      if (String(anchor.getAttribute("target") || "").toLowerCase() === "_blank") {
        return null;
      }

      const href = String(anchor.getAttribute("href") || "");
      if (!href || href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("tel:")) {
        return null;
      }

      const nextUrl = new URL(anchor.href, window.location.href);
      const currentUrl = new URL(window.location.href);
      if (nextUrl.origin !== currentUrl.origin) {
        return null;
      }
      if (
        nextUrl.pathname === currentUrl.pathname &&
        nextUrl.search === currentUrl.search &&
        nextUrl.hash !== currentUrl.hash
      ) {
        return null;
      }

      return nextUrl.href;
    }

    window.VeggieNav = window.VeggieNav || {};
    window.VeggieNav.navigate = function (href, options) {
      const rawHref = String(href || "").trim();
      if (!rawHref) {
        return;
      }

      let nextHref = rawHref;
      try {
        nextHref = new URL(rawHref, window.location.href).href;
      } catch (_) {
        // Keep raw href when URL parsing fails.
      }
      let isExternal = false;
      try {
        const nextUrl = new URL(nextHref, window.location.href);
        const currentUrl = new URL(window.location.href);
        isExternal = nextUrl.origin !== currentUrl.origin;
      } catch (_) {
        isExternal = false;
      }

      const opts = options || {};
      if (opts.transition === false || isExternal) {
        if (opts.replace) {
          window.location.replace(nextHref);
        } else {
          window.location.assign(nextHref);
        }
        return;
      }

      navigateWithTransition(nextHref);
    };

    playEntryTransition();
    window.setTimeout(function () {
      if (!navigating) {
        finalizeEntryTransition();
      }
    }, motionDuration(2400));
    window.addEventListener(
      "load",
      function () {
        if (!navigating) {
          finalizeEntryTransition();
        }
      },
      { once: true },
    );
    window.addEventListener("pageshow", function () {
      navigating = false;
      playEntryTransition();
    });

    document.addEventListener("click", function (event) {
      if (navigating || event.defaultPrevented || event.button !== 0) {
        return;
      }
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }

      const anchor = event.target && event.target.closest ? event.target.closest("a[href]") : null;
      const nextHref = resolveTransitionHref(anchor);
      if (!nextHref) {
        return;
      }

      event.preventDefault();
      navigateWithTransition(nextHref);
    }, true);

    document.addEventListener("keydown", function (event) {
      if (navigating || event.defaultPrevented || event.key !== "Enter") {
        return;
      }
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }

      const active = document.activeElement;
      const anchor = active && active.closest ? active.closest("a[href]") : null;
      const nextHref = resolveTransitionHref(anchor);
      if (!nextHref) {
        return;
      }

      event.preventDefault();
      navigateWithTransition(nextHref);
    }, true);
  }

  function initGlobalChatbot() {
    if (!window.CHAT_ENABLED) {
      return;
    }

    const toggleBtn = document.getElementById("chat-toggle");
    const toggleOpenIcon = document.getElementById("chat-toggle-open");
    const toggleCloseIcon = document.getElementById("chat-toggle-close");
    const panel = document.getElementById("chat-panel");
    const messagesNode = document.getElementById("chat-messages");
    const input = document.getElementById("chat-input");
    const sendBtn = document.getElementById("chat-send");
    const quick = document.getElementById("chat-quick");
    const clearBtn = document.getElementById("chat-clear");
    const conversationSelect = document.getElementById("chat-conversation-select");
    const newConversationBtn = document.getElementById("chat-new-conversation");
    if (
      !toggleBtn ||
      !panel ||
      !messagesNode ||
      !input ||
      !sendBtn ||
      !clearBtn ||
      !conversationSelect ||
      !newConversationBtn ||
      !api.apiRequest
    ) {
      return;
    }

    const intro = {
      id: "intro",
      text: "Hi! Ask me about vegetables, prices, nutrition, and shopping tips.",
      sender: "bot",
      timestamp: new Date(),
    };

    let isOpen = false;
    let isTyping = false;
    let isClearing = false;
    let isConversationLoading = false;
    let isConversationCreating = false;
    let messages = [intro];
    let conversations = [];
    let activeConversationId = null;

    function formatTime(value) {
      try {
        return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      } catch (_) {
        return "";
      }
    }

    function formatConversationTime(value) {
      try {
        return new Date(value).toLocaleString([], {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });
      } catch (_) {
        return "";
      }
    }

    function sortConversations() {
      function stamp(value) {
        const raw = String(value || "").trim();
        if (!raw) {
          return 0;
        }
        if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(raw)) {
          return Date.parse(raw.replace(" ", "T") + "Z") || 0;
        }
        return Date.parse(raw) || 0;
      }

      conversations.sort(function (left, right) {
        const leftStamp = stamp(left.last_message_at || left.updated_at || left.created_at);
        const rightStamp = stamp(right.last_message_at || right.updated_at || right.created_at);
        if (leftStamp !== rightStamp) {
          return rightStamp - leftStamp;
        }
        return Number(right.id || 0) - Number(left.id || 0);
      });
    }

    function upsertConversation(conversation) {
      if (!conversation || !conversation.id) {
        return;
      }
      const normalized = {
        id: Number(conversation.id),
        title: String(conversation.title || `Chat ${conversation.id}`),
        created_at: conversation.created_at || null,
        updated_at: conversation.updated_at || null,
        last_message_at: conversation.last_message_at || null,
        message_count: Number(conversation.message_count || 0),
      };

      const existingIndex = conversations.findIndex(function (item) {
        return Number(item.id) === normalized.id;
      });
      if (existingIndex >= 0) {
        conversations[existingIndex] = { ...conversations[existingIndex], ...normalized };
      } else {
        conversations.push(normalized);
      }
      sortConversations();
    }

    function conversationLabel(conversation) {
      const escapedTitle = api.escapeHtml
        ? api.escapeHtml(conversation.title || `Chat ${conversation.id}`)
        : String(conversation.title || `Chat ${conversation.id}`);
      const parts = [];
      if (Number(conversation.message_count || 0) > 0) {
        parts.push(`${conversation.message_count} msgs`);
      }
      const stamp = formatConversationTime(conversation.last_message_at || conversation.updated_at || conversation.created_at);
      if (stamp) {
        parts.push(stamp);
      }
      if (!parts.length) {
        return escapedTitle;
      }
      return `${escapedTitle} - ${api.escapeHtml ? api.escapeHtml(parts.join(" | ")) : parts.join(" | ")}`;
    }

    function renderConversationOptions() {
      sortConversations();
      if (!conversations.length) {
        conversationSelect.innerHTML = '<option value="">No chat history yet</option>';
        conversationSelect.disabled = true;
        return;
      }

      const hasActive = conversations.some(function (conversation) {
        return Number(conversation.id) === Number(activeConversationId);
      });
      if (!hasActive) {
        activeConversationId = Number(conversations[0].id);
      }

      conversationSelect.innerHTML = conversations
        .map(function (conversation) {
          return `<option value="${conversation.id}">${conversationLabel(conversation)}</option>`;
        })
        .join("");
      conversationSelect.value = String(activeConversationId);
      conversationSelect.disabled = isTyping || isConversationLoading || isConversationCreating;
    }

    function renderTyping() {
      return `
        <div class="flex justify-start">
          <div class="chat-bubble chat-bubble-bot px-4 py-3">
            <div class="flex gap-1">
              <span class="chat-typing-dot"></span>
              <span class="chat-typing-dot"></span>
              <span class="chat-typing-dot"></span>
            </div>
          </div>
        </div>
      `;
    }

    function renderMessages() {
      const html = messages
        .map(function (message) {
          const isUser = message.sender === "user";
          const side = isUser ? "justify-end" : "justify-start";
          const bubble = isUser ? "chat-bubble chat-bubble-user" : "chat-bubble chat-bubble-bot";
          const timeClass = isUser ? "text-white/80" : "text-slate-500 dark:text-slate-300";
          return `
            <div class="flex ${side}">
              <div class="max-w-[85%] px-4 py-2.5 ${bubble}">
                <p class="text-sm whitespace-pre-line">${api.escapeHtml ? api.escapeHtml(message.text) : message.text}</p>
                <p class="text-xs mt-1 ${timeClass}">${formatTime(message.timestamp)}</p>
              </div>
            </div>
          `;
        })
        .join("");

      messagesNode.innerHTML = html + (isTyping ? renderTyping() : "") + '<div id="chat-end-marker"></div>';
      const marker = document.getElementById("chat-end-marker");
      if (marker) {
        marker.scrollIntoView({ behavior: "smooth", block: "end" });
      }

      if (quick) {
        quick.classList.toggle("hidden", messages.length > 1);
      }

      createIcons(messagesNode);
    }

    function setOpen(open) {
      isOpen = Boolean(open);
      panel.classList.toggle("hidden", !isOpen);
      if (toggleOpenIcon && toggleCloseIcon) {
        toggleOpenIcon.classList.toggle("hidden", isOpen);
        toggleCloseIcon.classList.toggle("hidden", !isOpen);
      }
      if (isOpen && window.gsap) {
        window.gsap.fromTo(
          panel,
          { opacity: 0, y: 20, scale: 0.95 },
          { opacity: 1, y: 0, scale: 1, duration: 0.3, ease: "back.out(1.3)" },
        );
      }
    }

    function syncSendState() {
      sendBtn.disabled = isTyping || isConversationLoading || !input.value.trim();
      clearBtn.disabled = isTyping || isConversationLoading || isClearing || !activeConversationId;
      newConversationBtn.disabled = isTyping || isConversationLoading || isConversationCreating;
      conversationSelect.disabled =
        isTyping || isConversationLoading || isConversationCreating || conversations.length === 0;
    }

    function mapHistoryItemsToMessages(items) {
      if (!Array.isArray(items) || items.length === 0) {
        return [intro];
      }
      return items.map(function (item) {
        return {
          id: String(item.id),
          text: String(item.content || ""),
          sender: item.role === "assistant" ? "bot" : "user",
          timestamp: item.timestamp || new Date(),
        };
      });
    }

    async function loadConversations(options) {
      const opts = options || {};
      try {
        const payload = await api.apiRequest("/api/chat/conversations?limit=50");
        const items = (payload && payload.data && payload.data.conversations) || [];
        conversations = Array.isArray(items)
          ? items.map(function (item) {
            return {
              id: Number(item.id),
              title: String(item.title || `Chat ${item.id}`),
              created_at: item.created_at || null,
              updated_at: item.updated_at || null,
              last_message_at: item.last_message_at || null,
              message_count: Number(item.message_count || 0),
            };
          })
          : [];
        sortConversations();

        if (!conversations.length && opts.createIfEmpty !== false) {
          await createConversation({ skipConversationRefresh: true });
          return;
        }

        const preferred = opts.preferredConversationId ? Number(opts.preferredConversationId) : null;
        const hasPreferred = preferred
          ? conversations.some(function (conversation) {
            return Number(conversation.id) === preferred;
          })
          : false;
        const hasCurrent = activeConversationId
          ? conversations.some(function (conversation) {
            return Number(conversation.id) === Number(activeConversationId);
          })
          : false;

        if (hasPreferred) {
          activeConversationId = preferred;
        } else if (!hasCurrent) {
          activeConversationId = conversations.length ? Number(conversations[0].id) : null;
        }

        renderConversationOptions();
        if (opts.skipHistory !== true) {
          await loadHistory(activeConversationId);
        }
      } catch (_) {
        conversations = [];
        activeConversationId = null;
        messages = [intro];
        renderConversationOptions();
        renderMessages();
      } finally {
        syncSendState();
      }
    }

    async function createConversation(options) {
      const opts = options || {};
      if (isConversationCreating) {
        return;
      }
      isConversationCreating = true;
      syncSendState();
      try {
        const payload = await api.apiRequest("/api/chat/conversations", {
          method: "POST",
          body: JSON.stringify({}),
        });
        const conversation = payload && payload.data ? payload.data.conversation : null;
        if (!conversation || !conversation.id) {
          throw new Error("Unable to create a new chat");
        }
        activeConversationId = Number(conversation.id);
        upsertConversation(conversation);

        if (opts.skipConversationRefresh !== true) {
          await loadConversations({ preferredConversationId: activeConversationId, skipHistory: true, createIfEmpty: false });
        } else {
          renderConversationOptions();
        }

        await loadHistory(activeConversationId);
      } catch (error) {
        messages.push({
          id: String(Date.now() + 7),
          text: error && error.message ? error.message : "Unable to create a new chat",
          sender: "bot",
          timestamp: new Date(),
        });
        renderMessages();
      } finally {
        isConversationCreating = false;
        syncSendState();
      }
    }

    async function loadHistory(conversationId) {
      if (!conversationId) {
        messages = [intro];
        renderMessages();
        return;
      }

      isConversationLoading = true;
      syncSendState();
      try {
        const payload = await api.apiRequest(
          `/api/chat/history?limit=100&conversation_id=${encodeURIComponent(String(conversationId))}`,
        );
        const data = payload && payload.data ? payload.data : {};
        if (data && data.conversation) {
          upsertConversation(data.conversation);
        }
        messages = mapHistoryItemsToMessages(data.messages || []);
      } catch (_) {
        messages = [intro];
      } finally {
        isConversationLoading = false;
        renderConversationOptions();
        renderMessages();
        syncSendState();
      }
    }

    async function sendMessage() {
      const text = input.value.trim();
      if (!text || isTyping || isConversationLoading) {
        return;
      }

      if (!activeConversationId) {
        await createConversation();
        if (!activeConversationId) {
          return;
        }
      }

      input.value = "";
      syncSendState();
      messages.push({
        id: String(Date.now()),
        text: text,
        sender: "user",
        timestamp: new Date(),
      });
      isTyping = true;
      renderMessages();

      try {
        const payload = await api.apiRequest("/api/chat/message", {
          method: "POST",
          body: JSON.stringify({ message: text, conversation_id: activeConversationId }),
        });
        const data = payload && payload.data ? payload.data : {};
        if (data && data.conversation) {
          activeConversationId = Number(data.conversation.id || activeConversationId);
          upsertConversation(data.conversation);
        }

        const msg = data.message || null;
        if (!msg || !msg.content) {
          throw new Error("Chatbot did not return a valid reply");
        }

        messages.push({
          id: String(msg.id || Date.now() + 1),
          text: String(msg.content),
          sender: "bot",
          timestamp: new Date(),
        });
      } catch (error) {
        messages.push({
          id: String(Date.now() + 2),
          text: error && error.message ? error.message : "Chat request failed",
          sender: "bot",
          timestamp: new Date(),
        });
      } finally {
        isTyping = false;
        renderConversationOptions();
        renderMessages();
        syncSendState();
      }
    }

    async function clearHistory() {
      if (isClearing || !activeConversationId) {
        return;
      }
      isClearing = true;
      syncSendState();
      try {
        const payload = await api.apiRequest("/api/chat/history", {
          method: "DELETE",
          body: JSON.stringify({ conversation_id: activeConversationId }),
        });
        const data = payload && payload.data ? payload.data : {};
        if (data && data.conversation) {
          upsertConversation(data.conversation);
        } else {
          conversations = conversations.map(function (conversation) {
            if (Number(conversation.id) !== Number(activeConversationId)) {
              return conversation;
            }
            return { ...conversation, message_count: 0 };
          });
        }
        messages = [intro];
      } catch (error) {
        messages.push({
          id: String(Date.now() + 3),
          text: error && error.message ? error.message : "Unable to clear chat history",
          sender: "bot",
          timestamp: new Date(),
        });
      } finally {
        isClearing = false;
        renderConversationOptions();
        renderMessages();
        syncSendState();
      }
    }

    toggleBtn.addEventListener("click", function () {
      setOpen(!isOpen);
    });

    input.addEventListener("input", syncSendState);
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        void sendMessage();
      }
    });

    sendBtn.addEventListener("click", function () {
      void sendMessage();
    });

    clearBtn.addEventListener("click", function () {
      void clearHistory();
    });

    conversationSelect.addEventListener("change", function () {
      const selected = Number(conversationSelect.value || 0);
      if (!selected || selected === Number(activeConversationId)) {
        return;
      }
      activeConversationId = selected;
      void loadHistory(activeConversationId);
    });

    newConversationBtn.addEventListener("click", function () {
      void createConversation();
    });

    if (quick) {
      quick.querySelectorAll("[data-chat-quick]").forEach(function (button) {
        button.addEventListener("click", function () {
          input.value = button.getAttribute("data-chat-quick") || "";
          syncSendState();
          input.focus();
        });
      });
    }

    syncSendState();
    renderMessages();
    void loadConversations({ createIfEmpty: true });
  }

  function init() {
    if (window.gsap && window.ScrollTrigger) {
      window.gsap.registerPlugin(window.ScrollTrigger);
    }

    initTheme();
    createIcons();
    initNavbar();
    initPageTransitions();
    bindLogout();
    resolveNavbarAvatar();
    initHomeEffects();
    initGlobalChatbot();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
