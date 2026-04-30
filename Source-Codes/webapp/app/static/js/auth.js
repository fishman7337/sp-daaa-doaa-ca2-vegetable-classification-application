(function () {
  const api = window.webApi;
  const appContext = window.APP_CONTEXT || {};
  if (!api || !api.apiRequest) {
    return;
  }

  function navigate(path) {
    if (window.VeggieNav && typeof window.VeggieNav.navigate === "function") {
      window.VeggieNav.navigate(path);
      return;
    }
    window.location.href = path;
  }

  if (window.APP_CONTEXT && window.APP_CONTEXT.token) {
    navigate("/predict");
    return;
  }

  const modeLoginBtn = document.getElementById("mode-login");
  const modeSignupBtn = document.getElementById("mode-signup");
  const modeSlider = document.getElementById("mode-slider");
  const modeSwitch = document.getElementById("auth-mode-switch");

  const authTitle = document.getElementById("auth-title");
  const authSubtitle = document.getElementById("auth-subtitle");

  const authForm = document.getElementById("auth-form");
  const primaryFields = document.getElementById("primary-fields");
  const otpFields = document.getElementById("otp-fields");

  const fieldName = document.getElementById("field-name");
  const fieldTerms = document.getElementById("field-terms");
  const agreeTerms = document.getElementById("agree-terms");
  const inputName = document.getElementById("input-name");
  const inputEmail = document.getElementById("input-email");
  const inputPassword = document.getElementById("input-password");
  const togglePasswordBtn = document.getElementById("toggle-password");
  const eye = document.getElementById("password-eye");
  const eyeOff = document.getElementById("password-eye-off");

  const captchaBlock = document.getElementById("captcha-block");
  const captchaImage = document.getElementById("captcha-image");
  const captchaPrompt = document.getElementById("captcha-prompt");
  const captchaAnswer = document.getElementById("captcha-answer");
  const captchaRefresh = document.getElementById("captcha-refresh");

  const authSubmit = document.getElementById("auth-submit");
  const authSubmitLabel = document.getElementById("auth-submit-label");
  const authSubmitIcon = document.getElementById("auth-submit-icon");
  const authSubmitLoader = document.getElementById("auth-submit-loader");

  const forgotPasswordLink = document.getElementById("forgot-password-link");
  const forgotFields = document.getElementById("forgot-fields");
  const forgotEmail = document.getElementById("forgot-email");
  const forgotSubmit = document.getElementById("forgot-submit");
  const forgotSubmitLabel = document.getElementById("forgot-submit-label");
  const forgotBack = document.getElementById("forgot-back");

  const resetFields = document.getElementById("reset-fields");
  const resetNewPassword = document.getElementById("reset-new-password");
  const resetConfirmPassword = document.getElementById("reset-confirm-password");
  const resetSubmit = document.getElementById("reset-submit");
  const resetSubmitLabel = document.getElementById("reset-submit-label");
  const resetBack = document.getElementById("reset-back");

  const inputOtp = document.getElementById("input-otp");
  const otpVerifyBtn = document.getElementById("otp-verify-btn");
  const otpVerifyLabel = document.getElementById("otp-verify-label");
  const otpVerifyIcon = document.getElementById("otp-verify-icon");
  const otpVerifyLoader = document.getElementById("otp-verify-loader");
  const otpResend = document.getElementById("otp-resend");
  const otpBack = document.getElementById("otp-back");

  const errorNode = document.getElementById("auth-error");
  const errorText = document.getElementById("auth-error-text");
  const successNode = document.getElementById("auth-success");
  const successText = document.getElementById("auth-success-text");
  const warningNode = document.getElementById("auth-warning");
  const warningText = document.getElementById("auth-warning-text");
  const devNode = document.getElementById("auth-dev-otp");
  const devText = document.getElementById("auth-dev-otp-text");

  let mode = "login";
  let otpSession = "";
  let captchaEnabled = false;
  let captchaId = "";
  let loading = false;
  let resetToken = "";
  let resetCode = "";
  let formHeightSyncQueued = false;

  function refreshIcons(target) {
    if (!window.lucide || typeof window.lucide.createIcons !== "function") {
      return;
    }
    window.lucide.createIcons({
      icons: window.lucide.icons,
      nameAttr: "data-lucide",
      ...(target ? { root: target } : {}),
    });
  }

  function show(node, textNode, message) {
    if (!node || !textNode) {
      return;
    }
    if (!message) {
      node.classList.add("hidden");
      node.classList.remove("flex");
      textNode.textContent = "";
      return;
    }
    textNode.textContent = message;
    node.classList.remove("hidden");
    node.classList.add("flex");
  }

  function clearMessages() {
    show(errorNode, errorText, "");
    show(successNode, successText, "");
    show(warningNode, warningText, "");
    show(devNode, devText, "");
  }

  function syncSignupOnlyFields(isSignup) {
    if (fieldName) {
      fieldName.classList.toggle("hidden", !isSignup);
      if (isSignup) {
        fieldName.style.opacity = "1";
        fieldName.style.transform = "none";
      }
    }
    if (fieldTerms) {
      fieldTerms.classList.toggle("hidden", !isSignup);
      if (isSignup) {
        fieldTerms.style.opacity = "1";
        fieldTerms.style.transform = "none";
      }
    }
  }

  function syncPrimaryFieldsHeight() {
    if (!primaryFields || primaryFields.classList.contains("hidden")) {
      return;
    }

    const previousMode = mode === "signup";
    syncSignupOnlyFields(false);
    const loginHeight = primaryFields.scrollHeight;
    syncSignupOnlyFields(true);
    const signupHeight = primaryFields.scrollHeight;
    syncSignupOnlyFields(previousMode);

    const targetHeight = Math.max(loginHeight, signupHeight);
    if (targetHeight > 0) {
      primaryFields.style.minHeight = `${targetHeight}px`;
    }
  }

  function queuePrimaryFieldsHeightSync() {
    if (formHeightSyncQueued) {
      return;
    }
    formHeightSyncQueued = true;
    const runSync = function () {
      if (!formHeightSyncQueued) {
        return;
      }
      formHeightSyncQueued = false;
      syncPrimaryFieldsHeight();
    };
    if (window.requestAnimationFrame) {
      window.requestAnimationFrame(runSync);
    }
    window.setTimeout(runSync, 16);
  }

  function hideSpecialPanels() {
    if (forgotFields) {
      forgotFields.classList.add("hidden");
    }
    if (resetFields) {
      resetFields.classList.add("hidden");
    }
    resetToken = "";
    resetCode = "";
    if (resetNewPassword) {
      resetNewPassword.value = "";
    }
    if (resetConfirmPassword) {
      resetConfirmPassword.value = "";
    }
  }

  function isSpecialPanelOpen() {
    const forgotOpen = forgotFields && !forgotFields.classList.contains("hidden");
    const resetOpen = resetFields && !resetFields.classList.contains("hidden");
    return Boolean(forgotOpen || resetOpen);
  }

  function syncForgotPasswordLink() {
    if (!forgotPasswordLink) {
      return;
    }
    const showForgot = mode === "login" && !otpSession && !isSpecialPanelOpen();
    forgotPasswordLink.classList.toggle("hidden", !showForgot);
  }

  function setMode(next) {
    mode = next === "signup" ? "signup" : "login";
    const isSignup = mode === "signup";

    if (modeSlider) {
      modeSlider.style.transform = isSignup ? "translateX(calc(100% + 4px))" : "translateX(0)";
    }

    if (modeLoginBtn && modeSignupBtn) {
      modeLoginBtn.className = `relative z-10 flex-1 py-2.5 rounded-lg font-medium text-sm transition-all ${
        isSignup ? "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200" : "text-white"
      }`;
      modeSignupBtn.className = `relative z-10 flex-1 py-2.5 rounded-lg font-medium text-sm transition-all ${
        isSignup ? "text-white" : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
      }`;
    }

    syncSignupOnlyFields(isSignup);

    if (authSubmitLabel) {
      authSubmitLabel.textContent = isSignup ? "Create Account" : "Sign In";
    }

    if (!otpSession && !isSpecialPanelOpen()) {
      if (authTitle) {
        authTitle.textContent = isSignup ? "Create Account" : "Welcome Back";
      }
      if (authSubtitle) {
        authSubtitle.textContent = isSignup
          ? "Start your vegetable classification journey"
          : "Sign in to continue to VeggieAI";
      }
    }
    syncForgotPasswordLink();
    queuePrimaryFieldsHeightSync();
  }

  function setOtpStep(enabled, meta) {
    const useOtp = Boolean(enabled);
    otpSession = useOtp ? String(meta && meta.otpSession ? meta.otpSession : otpSession) : "";
    if (useOtp) {
      hideSpecialPanels();
    }

    if (modeSwitch) {
      modeSwitch.classList.toggle("hidden", useOtp);
    }
    if (primaryFields) {
      primaryFields.classList.toggle("hidden", useOtp);
    }
    if (otpFields) {
      otpFields.classList.toggle("hidden", !useOtp);
    }

    if (authTitle) {
      authTitle.textContent = useOtp ? "Verify OTP" : mode === "signup" ? "Create Account" : "Welcome Back";
    }
    if (authSubtitle) {
      authSubtitle.textContent = useOtp
        ? `Enter the code sent to ${meta && meta.emailHint ? meta.emailHint : "your email"}`
        : mode === "signup"
          ? "Start your vegetable classification journey"
          : "Sign in to continue to VeggieAI";
    }

    if (meta && meta.warning) {
      show(warningNode, warningText, meta.warning);
    }
    if (meta && meta.devOtp) {
      show(devNode, devText, `Development OTP: ${meta.devOtp}`);
    }

    if (!useOtp) {
      inputOtp.value = "";
      show(warningNode, warningText, "");
      show(devNode, devText, "");
    }
    syncForgotPasswordLink();
    if (!useOtp) {
      queuePrimaryFieldsHeightSync();
    }
  }

  function setLoading(target, isLoading) {
    loading = Boolean(isLoading);

    if (target === "otp") {
      if (otpVerifyBtn) {
        otpVerifyBtn.disabled = loading;
      }
      if (otpResend) {
        otpResend.disabled = loading;
      }
      if (otpBack) {
        otpBack.disabled = loading;
      }
      if (otpVerifyLoader && otpVerifyIcon) {
        otpVerifyLoader.classList.toggle("hidden", !loading);
        otpVerifyIcon.classList.toggle("hidden", loading);
      }
      if (otpVerifyLabel) {
        otpVerifyLabel.textContent = loading ? "Verifying..." : "Verify OTP";
      }
      return;
    }

    if (authSubmit) {
      authSubmit.disabled = loading;
    }
    if (authSubmitLoader && authSubmitIcon) {
      authSubmitLoader.classList.toggle("hidden", !loading);
      authSubmitIcon.classList.toggle("hidden", loading);
    }
    if (authSubmitLabel) {
      authSubmitLabel.textContent = loading ? "Please wait..." : mode === "signup" ? "Create Account" : "Sign In";
    }
  }

  function setActionButtonState(button, labelNode, isLoading, loadingText, idleText) {
    if (button) {
      button.disabled = Boolean(isLoading);
    }
    if (labelNode) {
      labelNode.textContent = isLoading ? loadingText : idleText;
    }
  }

  async function fetchCaptcha() {
    try {
      const payload = await api.apiRequest("/api/auth/captcha", { auth: false });
      const data = payload && payload.data ? payload.data : {};

      if (!data.enabled) {
        captchaEnabled = false;
        captchaId = "";
        captchaBlock.classList.add("hidden");
        captchaAnswer.value = "";
        queuePrimaryFieldsHeightSync();
        return;
      }

      captchaEnabled = true;
      captchaId = String(data.captcha_id || "").trim();
      captchaBlock.classList.remove("hidden");
      captchaImage.src = String(data.image_base64 || "");
      captchaPrompt.textContent = String(data.prompt || "Type the 5-digit code shown in the image.");
      captchaAnswer.value = "";
      queuePrimaryFieldsHeightSync();
    } catch (_) {
      captchaEnabled = false;
      captchaId = "";
      captchaBlock.classList.add("hidden");
      queuePrimaryFieldsHeightSync();
    }
  }

  async function establishSession(token) {
    const sessionLoginEndpoint = String(appContext.sessionLoginEndpoint || "/web/session/login").trim();
    const response = await fetch(sessionLoginEndpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ token: token }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(function () {
        return {};
      });
      const message = payload && payload.error && payload.error.message ? payload.error.message : "Unable to create web session";
      throw new Error(message);
    }
  }

  function buildIdentityBody() {
    const email = String(inputEmail.value || "").trim().toLowerCase();
    if (!email) {
      throw new Error("Please enter your email address");
    }
    if (!email.includes("@")) {
      throw new Error("Please enter a valid email address");
    }

    const password = String(inputPassword.value || "");
    if (!password) {
      throw new Error("Please enter your password");
    }

    if (password.length < 6) {
      throw new Error("Password must be at least 6 characters");
    }

    const body = {
      email: email,
      password: password,
    };

    if (mode === "signup") {
      const name = String(inputName.value || "").trim();
      if (!name) {
        throw new Error("Please enter your full name");
      }
      if (!agreeTerms || !agreeTerms.checked) {
        throw new Error("Please agree to the terms and conditions");
      }
      body.name = name;
      body.agree_terms = true;
    }

    if (captchaEnabled) {
      const answer = String(captchaAnswer.value || "").trim();
      if (!captchaId || !answer) {
        throw new Error("Please complete the captcha challenge");
      }
      body.captcha_id = captchaId;
      body.captcha_answer = answer;
    }

    return body;
  }

  async function submitPrimary() {
    clearMessages();
    setLoading("auth", true);
    try {
      const body = buildIdentityBody();
      const path = mode === "signup" ? "/api/auth/signup" : "/api/auth/login";
      const payload = await api.apiRequest(path, {
        method: "POST",
        auth: false,
        body: JSON.stringify(body),
      });
      const data = payload && payload.data ? payload.data : {};

      if (data.token) {
        await establishSession(data.token);
        show(successNode, successText, mode === "signup" ? "Account created successfully! Redirecting..." : "Welcome back! Redirecting...");
        navigate("/predict");
        return;
      }

      if (data.otp_required && data.otp_session) {
        setOtpStep(true, {
          otpSession: data.otp_session,
          emailHint: data.email,
          devOtp: data.dev_otp,
          warning: data.warning,
        });
        show(successNode, successText, data.delivery === "development" ? "OTP sent (development mode)." : "OTP sent to your email.");
        return;
      }

      throw new Error("Unexpected authentication response");
    } catch (error) {
      show(errorNode, errorText, error && error.message ? error.message : "Authentication failed.");
      await fetchCaptcha();
    } finally {
      setLoading("auth", false);
    }
  }

  async function submitOtp() {
    clearMessages();
    const code = String(inputOtp.value || "").trim();
    if (!otpSession || !code) {
      show(errorNode, errorText, "Please enter the OTP code");
      return;
    }

    setLoading("otp", true);
    try {
      const payload = await api.apiRequest("/api/auth/otp/verify", {
        method: "POST",
        auth: false,
        body: JSON.stringify({ otp_session: otpSession, otp_code: code }),
      });
      const data = payload && payload.data ? payload.data : {};
      if (!data.token) {
        throw new Error("OTP verification did not return a token.");
      }

      await establishSession(data.token);
      show(successNode, successText, "Verification successful. Redirecting...");
      navigate("/predict");
    } catch (error) {
      show(errorNode, errorText, error && error.message ? error.message : "OTP verification failed.");
    } finally {
      setLoading("otp", false);
    }
  }

  async function resendOtp() {
    if (!otpSession) {
      show(errorNode, errorText, "Missing OTP session");
      return;
    }

    clearMessages();
    setLoading("otp", true);
    try {
      const payload = await api.apiRequest("/api/auth/otp/resend", {
        method: "POST",
        auth: false,
        body: JSON.stringify({ otp_session: otpSession }),
      });
      const data = payload && payload.data ? payload.data : {};
      show(successNode, successText, "OTP resent successfully.");
      if (data.warning) {
        show(warningNode, warningText, data.warning);
      }
      if (data.dev_otp) {
        show(devNode, devText, `Development OTP: ${data.dev_otp}`);
      }
    } catch (error) {
      show(errorNode, errorText, error && error.message ? error.message : "Unable to resend OTP");
    } finally {
      setLoading("otp", false);
    }
  }

  function showForgotPasswordPanel() {
    clearMessages();
    setMode("login");
    setOtpStep(false);
    hideSpecialPanels();
    if (modeSwitch) {
      modeSwitch.classList.add("hidden");
    }
    if (primaryFields) {
      primaryFields.classList.add("hidden");
    }
    if (otpFields) {
      otpFields.classList.add("hidden");
    }
    if (forgotFields) {
      forgotFields.classList.remove("hidden");
    }
    if (primaryFields) {
      primaryFields.style.removeProperty("min-height");
    }
    if (authTitle) {
      authTitle.textContent = "Forgot Password";
    }
    if (authSubtitle) {
      authSubtitle.textContent = "Enter your email and we will send a one-time reset link.";
    }
    const existingIdentity = String(inputEmail.value || "").trim();
    if (forgotEmail) {
      forgotEmail.value = existingIdentity.includes("@") ? existingIdentity : "";
    }
    syncForgotPasswordLink();
    refreshIcons(forgotFields || undefined);
  }

  function showResetPasswordPanel(token, code) {
    clearMessages();
    setMode("login");
    setOtpStep(false);
    hideSpecialPanels();
    resetToken = String(token || "").trim();
    resetCode = String(code || "").trim();
    if (!resetToken || !resetCode) {
      show(errorNode, errorText, "Password reset link is invalid.");
      return;
    }
    if (modeSwitch) {
      modeSwitch.classList.add("hidden");
    }
    if (primaryFields) {
      primaryFields.classList.add("hidden");
    }
    if (otpFields) {
      otpFields.classList.add("hidden");
    }
    if (resetFields) {
      resetFields.classList.remove("hidden");
    }
    if (primaryFields) {
      primaryFields.style.removeProperty("min-height");
    }
    if (authTitle) {
      authTitle.textContent = "Reset Password";
    }
    if (authSubtitle) {
      authSubtitle.textContent = "Create a new password for your account.";
    }
    syncForgotPasswordLink();
    refreshIcons(resetFields || undefined);
  }

  function switchBackToSignIn() {
    clearMessages();
    hideSpecialPanels();
    setMode("login");
    setOtpStep(false);
    if (modeSwitch) {
      modeSwitch.classList.remove("hidden");
    }
    if (primaryFields) {
      primaryFields.classList.remove("hidden");
    }
    if (otpFields) {
      otpFields.classList.add("hidden");
    }
    void fetchCaptcha();
    queuePrimaryFieldsHeightSync();
  }

  async function submitForgotPassword() {
    clearMessages();
    const email = String(forgotEmail && forgotEmail.value ? forgotEmail.value : "")
      .trim()
      .toLowerCase();
    if (!email || !email.includes("@")) {
      show(errorNode, errorText, "Please enter a valid email address");
      return;
    }

    setActionButtonState(forgotSubmit, forgotSubmitLabel, true, "Sending...", "Send Reset Link");
    try {
      const payload = await api.apiRequest("/api/auth/password/forgot", {
        method: "POST",
        auth: false,
        body: JSON.stringify({ email: email }),
      });
      const data = payload && payload.data ? payload.data : {};
      show(successNode, successText, String(data.message || "If that email exists, a one-time reset link has been sent."));
      if (data.delivery === "development" && data.reset_link) {
        show(warningNode, warningText, `Development reset link: ${data.reset_link}`);
      }
    } catch (error) {
      show(errorNode, errorText, error && error.message ? error.message : "Unable to send reset link.");
    } finally {
      setActionButtonState(forgotSubmit, forgotSubmitLabel, false, "Sending...", "Send Reset Link");
    }
  }

  async function submitResetPassword() {
    clearMessages();
    if (!resetToken || !resetCode) {
      show(errorNode, errorText, "Password reset link is invalid or missing.");
      return;
    }

    const newPassword = String(resetNewPassword && resetNewPassword.value ? resetNewPassword.value : "");
    const confirmPassword = String(resetConfirmPassword && resetConfirmPassword.value ? resetConfirmPassword.value : "");

    if (!newPassword || newPassword.length < 8) {
      show(errorNode, errorText, "New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      show(errorNode, errorText, "Passwords do not match.");
      return;
    }

    setActionButtonState(resetSubmit, resetSubmitLabel, true, "Resetting...", "Reset Password");
    try {
      await api.apiRequest("/api/auth/password/reset", {
        method: "POST",
        auth: false,
        body: JSON.stringify({
          reset_token: resetToken,
          reset_code: resetCode,
          new_password: newPassword,
        }),
      });
      show(successNode, successText, "Password reset successful. Please sign in with your new password.");
      if (window.history && typeof window.history.replaceState === "function") {
        const cleanUrl = new URL(window.location.href);
        cleanUrl.searchParams.delete("reset_token");
        cleanUrl.searchParams.delete("reset_code");
        window.history.replaceState({}, document.title, `${cleanUrl.pathname}${cleanUrl.search}${cleanUrl.hash}`);
      }
      window.setTimeout(function () {
        switchBackToSignIn();
      }, 900);
    } catch (error) {
      show(errorNode, errorText, error && error.message ? error.message : "Unable to reset password.");
    } finally {
      setActionButtonState(resetSubmit, resetSubmitLabel, false, "Resetting...", "Reset Password");
    }
  }

  function switchBackFromOtp() {
    clearMessages();
    setOtpStep(false);
    void fetchCaptcha();
  }

  authForm.addEventListener("submit", function (event) {
    event.preventDefault();
    if (forgotFields && !forgotFields.classList.contains("hidden")) {
      void submitForgotPassword();
      return;
    }
    if (resetFields && !resetFields.classList.contains("hidden")) {
      void submitResetPassword();
      return;
    }
    if (!otpSession) {
      void submitPrimary();
    } else {
      void submitOtp();
    }
  });

  modeLoginBtn.addEventListener("click", function () {
    clearMessages();
    hideSpecialPanels();
    setOtpStep(false);
    setMode("login");
    void fetchCaptcha();
  });

  modeSignupBtn.addEventListener("click", function () {
    clearMessages();
    hideSpecialPanels();
    setOtpStep(false);
    setMode("signup");
    void fetchCaptcha();
  });

  togglePasswordBtn.addEventListener("click", function () {
    const show = inputPassword.type === "password";
    inputPassword.type = show ? "text" : "password";
    eye.classList.toggle("hidden", show);
    eyeOff.classList.toggle("hidden", !show);
    refreshIcons(togglePasswordBtn);
  });

  captchaRefresh.addEventListener("click", function () {
    void fetchCaptcha();
  });

  if (captchaAnswer) {
    captchaAnswer.addEventListener("input", function () {
      captchaAnswer.value = String(captchaAnswer.value || "")
        .replace(/[^0-9]/g, "")
        .slice(0, 5);
    });
  }

  otpResend.addEventListener("click", function () {
    void resendOtp();
  });

  otpBack.addEventListener("click", function () {
    switchBackFromOtp();
  });

  if (forgotPasswordLink) {
    forgotPasswordLink.addEventListener("click", function () {
      showForgotPasswordPanel();
    });
  }

  if (forgotSubmit) {
    forgotSubmit.addEventListener("click", function () {
      void submitForgotPassword();
    });
  }

  if (forgotBack) {
    forgotBack.addEventListener("click", function () {
      switchBackToSignIn();
    });
  }

  if (resetSubmit) {
    resetSubmit.addEventListener("click", function () {
      void submitResetPassword();
    });
  }

  if (resetBack) {
    resetBack.addEventListener("click", function () {
      switchBackToSignIn();
    });
  }

  if (window.gsap) {
    const imagePanel = document.getElementById("auth-image-panel");
    const container = document.getElementById("auth-container");
    window.gsap
      .timeline({ delay: 0.3 })
      .fromTo(imagePanel, { opacity: 0, x: -50 }, { opacity: 1, x: 0, duration: 0.8, ease: "power3.out" })
      .fromTo(authForm, { opacity: 0, x: 50 }, { opacity: 1, x: 0, duration: 0.8, ease: "power3.out" }, "-=0.6");

    if (container) {
      const fields = authForm.querySelectorAll(".form-field");
      window.gsap.fromTo(
        fields,
        { opacity: 0, y: 20, scale: 0.95, rotateX: -10 },
        { opacity: 1, y: 0, scale: 1, rotateX: 0, duration: 0.5, stagger: 0.08, ease: "back.out(1.4)" },
      );
    }
  }

  refreshIcons();

  const resetParams = new URLSearchParams(window.location.search);
  const resetTokenParam = String(resetParams.get("reset_token") || "").trim();
  const resetCodeParam = String(resetParams.get("reset_code") || "").trim();

  if (resetTokenParam && resetCodeParam) {
    showResetPasswordPanel(resetTokenParam, resetCodeParam);
  } else {
    setMode("login");
    setOtpStep(false);
    void fetchCaptcha();
    queuePrimaryFieldsHeightSync();
  }

  window.addEventListener("resize", function () {
    if (primaryFields && !primaryFields.classList.contains("hidden")) {
      queuePrimaryFieldsHeightSync();
    }
  });
})();
