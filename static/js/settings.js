/**
 * settings.js — Profile & Settings Pages
 * =========================================
 */

'use strict';

// ─────────────────────────────────────────────
// PROFILE PAGE
// ─────────────────────────────────────────────

async function initProfilePage() {
  // Load current profile data
  const { data, ok } = await apiFetch('/api/auth/me');
  if (!ok || !data?.success) { showToast('Could not load profile.', 'error'); return; }

  const owner   = data.data;
  const initial = (owner.full_name || '?').charAt(0).toUpperCase();

  // Avatar + info display
  const avatarEl = document.getElementById('profileAvatarLarge');
  const nameEl   = document.getElementById('profileName');
  const emailEl  = document.getElementById('profileEmail');

  if (avatarEl) avatarEl.textContent = initial;
  if (nameEl)   nameEl.textContent   = owner.full_name;
  if (emailEl)  emailEl.textContent  = owner.email;

  // Populate form
  document.getElementById('full_name').value     = owner.full_name  || '';
  document.getElementById('email').value         = owner.email       || '';
  document.getElementById('business_name').value = owner.business_name || '';

  const color = owner.brand_color || '#B89A5A';
  const colorPicker = document.getElementById('brand_color');
  const colorText   = document.getElementById('brand_color_text');
  if (colorPicker) colorPicker.value = color;
  if (colorText)   colorText.value   = color;

  // Color picker sync
  initColorPickerSync('brand_color', 'brand_color_text');

  // Profile form submission
  const profileForm = document.getElementById('profileForm');
  profileForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearAlerts();

    const formData = new FormData(profileForm);
    const btn      = document.getElementById('saveProfileBtn');
    setButtonLoading(btn, true);

    const { data: res, ok: resOk } = await apiFetch('/api/profile', {
      method: 'PATCH',
      body: formData,
    });

    setButtonLoading(btn, false);

    if (resOk && res?.success) {
      showAlert('profileSuccess', 'Profile updated successfully.', 'success');
      // Update sidebar name
      const nameEl2 = document.getElementById('sidebarName');
      if (nameEl2 && res.data?.full_name) nameEl2.textContent = res.data.full_name;
    } else {
      showAlert('profileError', res?.message || 'Could not update profile.', 'error');
    }
  });

  // Password form submission
  const pwdForm = document.getElementById('passwordForm');
  pwdForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearAlerts();

    const current  = document.getElementById('current_password')?.value;
    const newPwd   = document.getElementById('new_password')?.value;
    const confirm  = document.getElementById('confirm_password')?.value;

    if (!current) { showFieldErr('current_password', 'Current password required.'); return; }
    if (!newPwd)  { showFieldErr('new_password', 'New password required.');   return; }
    if (newPwd !== confirm) { showFieldErr('confirm_password', 'Passwords do not match.'); return; }

    const btn = document.getElementById('changePasswordBtn');
    setButtonLoading(btn, true);

    const { data: res, ok: resOk } = await apiFetch('/api/profile/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: current, new_password: newPwd, confirm_password: confirm }),
    });

    setButtonLoading(btn, false);

    if (resOk && res?.success) {
      showAlert('pwdSuccess', 'Password changed successfully.', 'success');
      pwdForm.reset();
    } else {
      showAlert('pwdError', res?.message || 'Password change failed.', 'error');
    }
  });
}

// ─────────────────────────────────────────────
// SETTINGS PAGE
// ─────────────────────────────────────────────

function initSettingsPage() {
  // Sync dark mode toggle with current theme
  const darkToggle = document.getElementById('darkModeToggle');
  if (darkToggle) {
    darkToggle.checked = document.documentElement.getAttribute('data-theme') === 'dark';
    darkToggle.addEventListener('change', () => {
      const theme = darkToggle.checked ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('vouchly_theme', theme);
    });
  }

  // Logout
  document.getElementById('logoutSettingsBtn')?.addEventListener('click', async () => {
    try { await apiFetch('/api/auth/logout', { method: 'POST' }); } catch (_) {}
    window.location.href = '/login';
  });
}

// ─────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────

function showAlert(id, message, type = 'error') {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent  = message;
  el.style.display = 'block';
  el.className    = `form-alert form-alert--${type}`;
}

function clearAlerts() {
  document.querySelectorAll('.form-alert').forEach(el => {
    el.style.display = 'none';
    el.textContent   = '';
  });
  document.querySelectorAll('.field-error').forEach(el => el.textContent = '');
}

function showFieldErr(fieldId, message) {
  const el = document.getElementById(fieldId + 'Error');
  if (el) el.textContent = message;
}
