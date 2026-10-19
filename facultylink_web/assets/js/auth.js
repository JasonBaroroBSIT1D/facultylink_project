window.FL = window.FL || {};

FL.auth = {
  sessionKey: "facultylink.session",
  rememberKey: "facultylink.remember",

  current: function () {
    try {
      return JSON.parse(sessionStorage.getItem(this.sessionKey) || "null");
    } catch (error) {
      return null;
    }
  },

  home: function (role) {
    const here = window.location.pathname.replace(/\\/g, "/");
    const inFolder = /\/(admin|reviewer)\//.test(here);
    const prefix = inFolder ? "../" : "";
    if (role === "administrator") return prefix + "admin/dashboard.html";
    if (role === "reviewer") return prefix + "reviewer/dashboard.html";
    return prefix + "login.html";
  },

  loginUrl: function () {
    const here = window.location.pathname.replace(/\\/g, "/");
    return /\/(admin|reviewer)\//.test(here) ? "../login.html" : "login.html";
  },

  restore: function () {
    return FL.api.send("GET", "/api/session").then(function (data) {
      return data.user || null;
    }).catch(function () {
      return null;
    });
  },

  signIn: function (identity, password) {
    return FL.api.send("POST", "/api/login", {
      identity: identity.trim(),
      password: password
    });
  },

  signOut: function () {
    const loginUrl = this.loginUrl();
    FL.api.send("POST", "/api/logout").finally(function () {
      window.location.href = loginUrl;
    });
  },

  requirePasswordChange: function () {
    FL.ui.modal({
      title: "Change temporary password",
      confirmLabel: "Update password",
      cancelLabel: "Sign out",
      body: `
        <p>This sign-in used a temporary password. Set a new password before opening reviewer pages.</p>
        <label class="field"><span>Temporary password</span><input id="current-password" type="password" autocomplete="current-password"></label>
        <label class="field"><span>New password</span><input id="new-password" type="password" autocomplete="new-password"></label>
        <label class="field"><span>Confirm new password</span><input id="confirm-password" type="password" autocomplete="new-password"></label>
        <p class="note" id="password-change-error" hidden></p>`,
      onConfirm: function () {
        const current = document.getElementById("current-password").value;
        const next = document.getElementById("new-password").value;
        const again = document.getElementById("confirm-password").value;
        const error = document.getElementById("password-change-error");
        if (next !== again) {
          error.hidden = false;
          error.textContent = "The new passwords do not match.";
          return false;
        }
        error.hidden = true;
        FL.api.send("POST", "/api/account/password", {
          currentPassword: current,
          newPassword: next
        }).then(function () {
          FL.ui.closeModal();
          window.location.reload();
        }).catch(function (err) {
          error.hidden = false;
          error.textContent = err.message || "The password was not changed.";
        });
        return false;
      },
      onClose: function (ok) {
        if (!ok) FL.auth.signOut();
      }
    });
  }
};

FL.pages = FL.pages || {};
FL.pages.login = function () {
  const form = document.getElementById("login-form");
  const identity = document.getElementById("identity");
  const password = document.getElementById("password");
  const identityError = document.getElementById("identity-error");
  const passwordError = document.getElementById("password-error");
  const formError = document.getElementById("form-error");
  const submit = document.getElementById("sign-in");
  const toggle = document.getElementById("toggle-password");
  const remember = document.getElementById("remember");
  const saved = localStorage.getItem(FL.auth.rememberKey);
  if (saved) {
    identity.value = saved;
    remember.checked = true;
  }
  toggle.addEventListener("click", function () {
    const show = password.type === "password";
    password.type = show ? "text" : "password";
    toggle.classList.toggle("is-visible", show);
    toggle.setAttribute("aria-pressed", show ? "true" : "false");
    toggle.setAttribute("aria-label", show ? "Hide password" : "Show password");
  });
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    identityError.textContent = "";
    passwordError.textContent = "";
    formError.hidden = true;
    let invalid = false;
    if (!identity.value.trim()) {
      identityError.textContent = "Email address is required.";
      invalid = true;
    }
    if (!password.value) {
      passwordError.textContent = "Password is required.";
      invalid = true;
    }
    if (invalid) return;
    submit.disabled = true;
    submit.innerHTML = '<span class="spinner" aria-hidden="true"></span> Signing in';
    FL.auth.signIn(identity.value, password.value).then(function (session) {
      if (remember.checked) localStorage.setItem(FL.auth.rememberKey, identity.value.trim());
      else localStorage.removeItem(FL.auth.rememberKey);
      formError.hidden = true;
      submit.classList.add("is-success");
      submit.textContent = "Signed in";
      document.getElementById("login-success").hidden = false;
      window.setTimeout(function () {
        window.location.href = FL.auth.home(session.role);
      }, 400);
    }).catch(function (error) {
      submit.disabled = false;
      submit.textContent = "Sign in";
      formError.hidden = false;
      formError.textContent = error.status ? error.message : "FacultyLink could not reach the server. Start the backend, then try again.";
    });
  });
  document.getElementById("contact-admin").addEventListener("click", function () {
    FL.ui.modal({
      title: "Contact institution admin",
      body: "<p>New Administrator and Reviewer accounts are issued by the institution. Contact the Office of the Vice President for Academic Affairs.</p>",
      cancelLabel: "Close"
    });
  });
  FL.auth.restore().then(function (existing) {
    if (existing) window.location.replace(FL.auth.home(existing.role));
  });
};

FL.pages.forgotPassword = function () {
  const form = document.getElementById("reset-form");
  const email = document.getElementById("reset-email");
  const emailError = document.getElementById("reset-email-error");
  const formError = document.getElementById("reset-error");
  const confirmation = document.getElementById("reset-confirmation");
  const confirmationText = document.getElementById("reset-confirmation-text");
  const submit = document.getElementById("send-reset");
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    emailError.textContent = "";
    formError.hidden = true;
    confirmation.hidden = true;
    const value = email.value.trim();
    if (!value) {
      emailError.textContent = "Email address is required.";
      email.focus();
      return;
    }
    if (!emailPattern.test(value) || value.length > 254) {
      emailError.textContent = "Enter a valid email address.";
      email.focus();
      return;
    }
    submit.disabled = true;
    submit.innerHTML = '<span class="spinner" aria-hidden="true"></span> Sending';
    FL.api.send("POST", "/api/forgot-password", { email: value }).then(function (result) {
      submit.disabled = false;
      submit.textContent = "Send Reset Link";
      confirmationText.textContent = result.emailSent
        ? (result.message || "A reset link was sent to that email address.")
        : (result.message || "No reset email was sent. Password recovery by email is not connected yet. Contact your institution administrator.");
      confirmation.hidden = false;
    }).catch(function (error) {
      submit.disabled = false;
      submit.textContent = "Send Reset Link";
      formError.hidden = false;
      formError.textContent = error.status ? error.message : "FacultyLink could not reach the server. Start the backend, then try again.";
    });
  });

};
