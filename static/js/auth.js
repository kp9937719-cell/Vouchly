/**
 * auth.js — Authentication Forms
 * =================================
 * Handles login, signup, forgot password, reset password forms.
 * Calls: initLoginForm(), initSignupForm(), initForgotPasswordForm(), initResetPasswordForm()
 */

'use strict';

// ─────────────────────────────────────────────
// SHARED HELPERS
// ─────────────────────────────────────────────

function showFieldError(fieldId, message) {
  const el = document.getElementById(fieldId + 'Error');
  if (el) el.textContent = message;
}

function clearFieldErrors() {
  document.querySelectorAll('.field-error').forEach(el => el.textContent = '');
}

function showFormAlert(id, message, type = 'error', isHtml = false) {
  const el = document.getElementById(id);
  if (!el) return;
  if (isHtml) {
    el.innerHTML = message;
  } else {
    el.textContent = message;
  }
  el.style.display = message ? 'block' : 'none';
  el.className = `form-alert form-alert--${type}`;
}

function hideFormAlert(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = 'none';
}

// Password visibility toggle
function initPasswordToggle(inputId, toggleId, iconId) {
  const input  = document.getElementById(inputId);
  const toggle = document.getElementById(toggleId);
  const icon   = document.getElementById(iconId);
  if (!input || !toggle) return;

  toggle.addEventListener('click', () => {
    const isHidden = input.type === 'password';
    input.type = isHidden ? 'text' : 'password';
    if (icon) icon.className = isHidden ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye';
  });
}

// Redirect authenticated users away from auth pages
async function redirectIfLoggedIn() {
  try {
    const { ok } = await apiFetch('/api/auth/me');
    if (ok) window.location.href = '/dashboard';
  } catch (_) {}
}

// ─────────────────────────────────────────────
// PASSWORD STRENGTH
// ─────────────────────────────────────────────

function checkPasswordStrength(password) {
  let score = 0;
  if (password.length >= 8)          score++;
  if (/[A-Z]/.test(password))        score++;
  if (/[0-9]/.test(password))        score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  const levels = [
    { label: '',       color: '',           width: '0%'   },
    { label: 'Weak',   color: 'var(--error)',   width: '25%'  },
    { label: 'Fair',   color: 'var(--warning)', width: '50%'  },
    { label: 'Good',   color: 'var(--gold)',     width: '75%'  },
    { label: 'Strong', color: 'var(--success)',  width: '100%' },
  ];

  return levels[score] || levels[0];
}

function initPasswordStrength(inputId, fillId, labelId) {
  const input = document.getElementById(inputId);
  const fill  = document.getElementById(fillId);
  const label = document.getElementById(labelId);
  if (!input) return;

  input.addEventListener('input', () => {
    const result = checkPasswordStrength(input.value);
    if (fill) {
      fill.style.width      = result.width;
      fill.style.background = result.color;
    }
    if (label) {
      label.textContent = result.label;
      label.style.color = result.color;
    }
  });
}

// ─────────────────────────────────────────────
// LOGIN FORM
// ─────────────────────────────────────────────

function initLoginForm() {
  redirectIfLoggedIn();
  initPasswordToggle('password', 'passwordToggle', 'passwordToggleIcon');

  const form = document.getElementById('loginForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFieldErrors();
    hideFormAlert('formError');

    const email    = document.getElementById('email')?.value.trim();
    const password = document.getElementById('password')?.value;

    let valid = true;
    if (!email) { showFieldError('email', 'Email is required.'); valid = false; }
    if (!password) { showFieldError('password', 'Password is required.'); valid = false; }
    if (!valid) return;

    const btn = document.getElementById('loginBtn');
    setButtonLoading(btn, true);

    const { data, ok, status } = await apiFetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    if (ok && data?.success) {
      if (window.setFlashToast) {
        window.setFlashToast('Welcome back! You have logged in successfully.', 'success', 'Login Successful');
      }
      if (window.showToast) {
        window.showToast('Login successful! Taking you to your dashboard...', 'success', 'Login Successful', 2500);
      }
      setTimeout(() => {
        window.location.href = '/dashboard';
      }, 600);
    } else if (status === 403 && (data?.errors?.unverified || (data?.message && data.message.toLowerCase().includes('verify')))) {
      const unverifiedEmail = data?.errors?.email || email;
      const alertHtml = `
        <div style="text-align:left;">
          <strong style="display:block;margin-bottom:0.25rem;">Email Verification Required</strong>
          <p style="margin:0 0 0.75rem 0;font-size:0.875rem;line-height:1.4;">${escapeHtml(data?.message || 'Your email address has not been verified yet.')}</p>
          <a href="/verification-pending?email=${encodeURIComponent(unverifiedEmail)}" class="btn btn-secondary btn-sm btn-block" style="text-decoration:none;display:block;text-align:center;">
            <i class="fa-solid fa-envelope-circle-check"></i> Go to Verification Page
          </a>
        </div>
      `;
      showFormAlert('formError', alertHtml, 'warning', true);
    } else {
      showFormAlert('formError', data?.message || 'Login failed. Please try again.');
    }
  });
}

// ─────────────────────────────────────────────
// SIGNUP FORM
// ─────────────────────────────────────────────

function initSignupForm() {
  redirectIfLoggedIn();
  initPasswordToggle('password', 'passwordToggle', 'passwordToggleIcon');
  initPasswordStrength('password', 'strengthFill', 'strengthLabel');

  const form = document.getElementById('signupForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFieldErrors();
    hideFormAlert('formError');
    hideFormAlert('formSuccess');

    const full_name        = document.getElementById('full_name')?.value.trim();
    const email            = document.getElementById('email')?.value.trim();
    const password         = document.getElementById('password')?.value;
    const confirm_password = document.getElementById('confirm_password')?.value;

    let valid = true;
    if (!full_name)     { showFieldError('full_name', 'Full name is required.'); valid = false; }
    if (!email) {
      showFieldError('email', 'Email is required.'); valid = false;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      showFieldError('email', 'Please enter a valid email address (e.g. name@gmail.com).'); valid = false;
    }
    if (!password) {
      showFieldError('password', 'Password is required.'); valid = false;
    } else if (password.length < 8) {
      showFieldError('password', 'Password must be at least 8 characters long.'); valid = false;
    } else if (!/[A-Za-z]/.test(password)) {
      showFieldError('password', 'Password must contain at least one letter.'); valid = false;
    } else if (!/\d/.test(password)) {
      showFieldError('password', 'Password must contain at least one number.'); valid = false;
    }
    if (password && confirm_password && password !== confirm_password) {
      showFieldError('confirm_password', 'Passwords do not match.');
      valid = false;
    }
    if (!valid) return;

    const btn = document.getElementById('signupBtn');
    setButtonLoading(btn, true);

    const { data, ok } = await apiFetch('/api/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ full_name, email, password }),
    });

    setButtonLoading(btn, false);

    if (ok && data?.success) {
      // Show immediate popup toast
      if (window.showToast) {
        window.showToast('Your account has been created successfully!', 'success', 'Account Created', 3000);
      }
      // Pass flash toast to next page
      if (window.setFlashToast) {
        window.setFlashToast('Your account has been created successfully! Please verify your email.', 'success', 'Account Created');
      }
      // Redirect to verification pending page
      const verifyLink = data.data?.verify_link || '';
      const emailError = data.data?.email_error || '';
      const emailParam = encodeURIComponent(email);
      const linkParam  = verifyLink ? `&verify_link=${encodeURIComponent(verifyLink)}` : '';
      const errParam   = emailError ? `&email_error=${encodeURIComponent(emailError)}` : '';
      setTimeout(() => {
        window.location.href = `/verification-pending?email=${emailParam}${linkParam}${errParam}`;
      }, 700);
    } else {
      // Show per-field errors if the API returned them
      if (data?.errors && typeof data.errors === 'object') {
        let hasFieldError = false;
        Object.entries(data.errors).forEach(([field, msg]) => {
          const errEl = document.getElementById(field + 'Error');
          if (errEl) {
            errEl.textContent = msg;
            hasFieldError = true;
          }
        });
        // Only show the generic alert if no per-field error was mapped
        if (!hasFieldError) {
          showFormAlert('formError', data.message || 'Signup failed. Please try again.');
        } else {
          // Show a concise top-level hint so the user knows to look at the fields
          showFormAlert('formError', data.message || 'Please fix the errors below.');
        }
      } else {
        showFormAlert('formError', data?.message || 'Signup failed. Please try again.');
      }
    }
  });
}

// ─────────────────────────────────────────────
// FORGOT PASSWORD FORM
// ─────────────────────────────────────────────

function initForgotPasswordForm() {
  const form = document.getElementById('forgotForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFieldErrors();
    hideFormAlert('formError');
    hideFormAlert('formSuccess');

    const email = document.getElementById('email')?.value.trim();
    if (!email) { showFieldError('email', 'Email is required.'); return; }

    const btn = document.getElementById('forgotBtn');
    setButtonLoading(btn, true);

    const { data, ok } = await apiFetch('/api/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });

    setButtonLoading(btn, false);

    // Always show success (to prevent email enumeration)
    showFormAlert(
      'formSuccess',
      data?.message || 'If an account exists with this email, a reset link has been sent.',
      'success'
    );
  });
}

// ─────────────────────────────────────────────
// RESET PASSWORD FORM
// ─────────────────────────────────────────────

function initResetPasswordForm() {
  initPasswordToggle('password', 'passwordToggle', 'passwordToggleIcon');

  const form = document.getElementById('resetForm');
  if (!form) return;

  const token = document.getElementById('resetToken')?.value;
  if (!token) {
    showFormAlert('formError', 'Invalid or missing reset token. Please request a new link.');
    return;
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFieldErrors();
    hideFormAlert('formError');
    hideFormAlert('formSuccess');

    const password         = document.getElementById('password')?.value;
    const confirm_password = document.getElementById('confirm_password')?.value;

    if (!password) { showFieldError('password', 'Password is required.'); return; }
    if (password !== confirm_password) {
      showFieldError('confirm_password', 'Passwords do not match.');
      return;
    }

    const btn = document.getElementById('resetBtn');
    setButtonLoading(btn, true);

    const { data, ok } = await apiFetch('/api/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ token, new_password: password }),
    });

    setButtonLoading(btn, false);

    if (ok && data?.success) {
      if (window.showToast) {
        window.showToast('Password reset successfully!', 'success', 'Success', 2500);
      }
      if (window.setFlashToast) {
        window.setFlashToast('Password reset successfully! Please log in with your new password.', 'success', 'Password Reset');
      }
      showFormAlert('formSuccess', 'Password reset successfully! Redirecting to login...', 'success');
      setTimeout(() => { window.location.href = '/login'; }, 1500);
    } else {
      showFormAlert('formError', data?.message || 'Reset failed. The link may have expired.');
    }
  });
}
