(function () {
  const api = window.webApi;
  if (!api || !api.ensureAuthenticated || !api.ensureAuthenticated()) {
    return;
  }

  const alertNode = document.getElementById("profile-alert");
  const alertText = document.getElementById("profile-alert-text");
  const alertIconSuccess = document.getElementById("profile-alert-icon-success");
  const alertIconError = document.getElementById("profile-alert-icon-error");

  const avatarImg = document.getElementById("profile-avatar");
  const avatarFallback = document.getElementById("profile-avatar-fallback");
  const avatarInput = document.getElementById("avatar-input");
  const avatarChangeBtn = document.getElementById("avatar-change-btn");
  const avatarChangeLabel = document.getElementById("avatar-change-label");

  const profileForm = document.getElementById("profile-form");
  const profileName = document.getElementById("profile-name");
  const profileEmail = document.getElementById("profile-email");
  const profileSaveBtn = document.getElementById("profile-save-btn");
  const profileSaveLabel = document.getElementById("profile-save-label");

  const passwordForm = document.getElementById("password-form");
  const passwordCurrent = document.getElementById("password-current");
  const passwordNew = document.getElementById("password-new");
  const passwordConfirm = document.getElementById("password-confirm");
  const passwordSaveBtn = document.getElementById("password-save-btn");
  const passwordSaveLabel = document.getElementById("password-save-label");
  const deleteProfileBtn = document.getElementById("profile-delete-btn");
  const deleteProfileLabel = document.getElementById("profile-delete-label");

  let currentUser = null;

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

  function showAlert(kind, message) {
    if (!alertNode || !alertText || !alertIconSuccess || !alertIconError) {
      return;
    }

    if (!message) {
      alertNode.className = "items-center gap-2 p-3 rounded-xl text-sm hidden";
      alertText.textContent = "";
      alertIconSuccess.classList.add("hidden");
      alertIconError.classList.add("hidden");
      return;
    }

    const isError = kind === "error";
    alertNode.className = `flex items-center gap-2 p-3 rounded-xl text-sm ${
      isError
        ? "bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400"
        : "bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400"
    }`;
    alertText.textContent = message;
    alertIconSuccess.classList.toggle("hidden", isError);
    alertIconError.classList.toggle("hidden", !isError);
  }

  function avatarSrc(user) {
    const raw = user && user.avatar ? String(user.avatar) : "";
    if (!raw) {
      return "";
    }
    if (raw.startsWith("/api/") && api.withTokenQuery) {
      return api.withTokenQuery(raw);
    }
    return raw;
  }

  function renderAvatar(user) {
    const src = avatarSrc(user);
    if (src) {
      avatarImg.src = src;
      avatarImg.classList.remove("hidden");
      avatarFallback.classList.add("hidden");
      return;
    }

    avatarImg.src = "";
    avatarImg.classList.add("hidden");
    avatarFallback.classList.remove("hidden");
  }

  function setButtonLoading(button, labelNode, isLoading, loadingText, defaultText) {
    if (button) {
      button.disabled = isLoading;
    }
    if (labelNode) {
      labelNode.textContent = isLoading ? loadingText : defaultText;
    }
  }

  async function loadProfile() {
    const payload = await api.apiRequest("/api/auth/me");
    const user = payload && payload.data ? payload.data.user : null;
    currentUser = user;

    profileName.value = user && user.name ? user.name : "";
    profileEmail.value = user && user.email ? user.email : "";
    renderAvatar(user);
  }

  async function submitProfile(event) {
    event.preventDefault();
    showAlert("", "");

    const name = String(profileName.value || "").trim();
    const email = String(profileEmail.value || "").trim();

    if (!currentUser) {
      showAlert("error", "Profile is not loaded yet.");
      return;
    }

    const payload = {};
    if (name !== String(currentUser.name || "").trim()) {
      payload.name = name;
    }
    if (email !== String(currentUser.email || "").trim()) {
      payload.email = email;
    }

    if (!payload.name && !payload.email) {
      showAlert("success", "No profile changes to save.");
      return;
    }

    setButtonLoading(profileSaveBtn, profileSaveLabel, true, "Saving...", "Save Profile");
    try {
      const response = await api.apiRequest("/api/auth/profile", {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      currentUser = response && response.data ? response.data.user : currentUser;
      profileName.value = currentUser && currentUser.name ? currentUser.name : profileName.value;
      profileEmail.value = currentUser && currentUser.email ? currentUser.email : profileEmail.value;
      renderAvatar(currentUser);
      showAlert("success", "Profile updated successfully.");
    } catch (error) {
      showAlert("error", error && error.message ? error.message : "Failed to update profile.");
    } finally {
      setButtonLoading(profileSaveBtn, profileSaveLabel, false, "Saving...", "Save Profile");
    }
  }

  async function submitPassword(event) {
    event.preventDefault();
    showAlert("", "");

    const current = String(passwordCurrent.value || "");
    const next = String(passwordNew.value || "");
    const confirm = String(passwordConfirm.value || "");

    if (!current || !next || !confirm) {
      showAlert("error", "Please complete all password fields.");
      return;
    }

    if (next.length < 8) {
      showAlert("error", "New password must be at least 8 characters.");
      return;
    }

    if (next !== confirm) {
      showAlert("error", "New passwords do not match.");
      return;
    }

    setButtonLoading(passwordSaveBtn, passwordSaveLabel, true, "Updating...", "Update Password");
    try {
      await api.apiRequest("/api/auth/password", {
        method: "POST",
        body: JSON.stringify({ current_password: current, new_password: next }),
      });
      passwordCurrent.value = "";
      passwordNew.value = "";
      passwordConfirm.value = "";
      showAlert("success", "Password changed successfully.");
    } catch (error) {
      showAlert("error", error && error.message ? error.message : "Failed to change password.");
    } finally {
      setButtonLoading(passwordSaveBtn, passwordSaveLabel, false, "Updating...", "Update Password");
    }
  }

  async function uploadAvatar(event) {
    const file = event.target.files && event.target.files[0] ? event.target.files[0] : null;
    if (!file) {
      return;
    }

    showAlert("", "");
    setButtonLoading(avatarChangeBtn, avatarChangeLabel, true, "Uploading...", "Change Picture");

    try {
      const form = new FormData();
      form.append("image", file);
      const response = await api.apiRequest("/api/auth/avatar", {
        method: "POST",
        isForm: true,
        body: form,
      });
      currentUser = response && response.data ? response.data.user : currentUser;
      renderAvatar(currentUser);
      showAlert("success", "Profile picture updated.");
    } catch (error) {
      showAlert("error", error && error.message ? error.message : "Failed to upload profile picture.");
    } finally {
      setButtonLoading(avatarChangeBtn, avatarChangeLabel, false, "Uploading...", "Change Picture");
      avatarInput.value = "";
    }
  }

  async function deleteProfile() {
    showAlert("", "");
    const warning = "This will permanently delete your profile, history, and chat data.";
    const confirmed = window.confirm(`${warning}\n\nAre you sure you want to continue?`);
    if (!confirmed) {
      return;
    }

    const finalCheck = window.prompt("Type DELETE to confirm profile deletion:");
    if (String(finalCheck || "").trim().toUpperCase() !== "DELETE") {
      showAlert("error", "Profile deletion cancelled. Confirmation text did not match.");
      return;
    }

    setButtonLoading(deleteProfileBtn, deleteProfileLabel, true, "Deleting...", "Delete Profile");
    try {
      await api.apiRequest("/api/auth/profile", {
        method: "DELETE",
        body: JSON.stringify({ confirm: "DELETE" }),
      });
      window.location.href = "/logout";
    } catch (error) {
      showAlert("error", error && error.message ? error.message : "Failed to delete profile.");
      setButtonLoading(deleteProfileBtn, deleteProfileLabel, false, "Deleting...", "Delete Profile");
    }
  }

  avatarChangeBtn.addEventListener("click", function () {
    avatarInput.click();
  });
  avatarInput.addEventListener("change", function (event) {
    void uploadAvatar(event);
  });

  profileForm.addEventListener("submit", function (event) {
    void submitProfile(event);
  });

  passwordForm.addEventListener("submit", function (event) {
    void submitPassword(event);
  });

  if (deleteProfileBtn) {
    deleteProfileBtn.addEventListener("click", function () {
      void deleteProfile();
    });
  }

  refreshIcons();
  loadProfile().catch(function (error) {
    showAlert("error", error && error.message ? error.message : "Unable to load profile");
  });
})();
