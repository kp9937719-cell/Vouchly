/**
 * main.js — Global JavaScript Utilities
 * =======================================
 * This file loads on every page and provides:
 *  - Toast notifications
 *  - Modal dialogs
 *  - Theme toggle (light/dark)
 *  - API helper (apiFetch)
 *  - Auth redirect helpers
 *  - Dashboard sidebar + topbar interactions
 *  - Safe DOM helpers
 *
 * Every other JS file imports and uses functions from here via globals.
 */

'use strict';

// ─────────────────────────────────────────────
// TOAST NOTIFICATIONS
// ─────────────────────────────────────────────

/**
 * Show a toast notification.
 * @param {string} message   - The message to display
 * @param {string} type      - 'success' | 'error' | 'warning' | 'info'
 * @param {string} [title]   - Optional bold title
 * @param {number} [duration]- Auto-dismiss in ms (default: 4000)
 */
function showToast(message, type = 'info', title = '', duration = 4000) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.setAttribute('aria-live', 'polite');
    document.body.appendChild(container);
  }

  const icons = {
    success: 'fa-circle-check',
    error:   'fa-circle-xmark',
    warning: 'fa-triangle-exclamation',
    info:    'fa-circle-info',
  };

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.setAttribute('role', 'alert');

  // Use textContent for safe rendering (no innerHTML with user data)
  const iconEl   = document.createElement('i');
  iconEl.className = `fa-solid ${icons[type] || icons.info} toast-icon`;

  const bodyEl   = document.createElement('div');
  bodyEl.className = 'toast-body';

  if (title) {
    const titleEl = document.createElement('div');
    titleEl.className = 'toast-title';
    titleEl.textContent = title;
    bodyEl.appendChild(titleEl);
  }

  const msgEl = document.createElement('div');
  msgEl.className = 'toast-msg';
  msgEl.textContent = message;
  bodyEl.appendChild(msgEl);

  const closeEl = document.createElement('button');
  closeEl.className = 'toast-close';
  closeEl.innerHTML = '<i class="fa-solid fa-xmark"></i>';
  closeEl.setAttribute('aria-label', 'Dismiss');

  toast.appendChild(iconEl);
  toast.appendChild(bodyEl);
  toast.appendChild(closeEl);
  container.appendChild(toast);

  const dismiss = () => {
    toast.classList.add('toast-leave');
    setTimeout(() => toast.remove(), 250);
  };

  closeEl.addEventListener('click', dismiss);
  if (duration > 0) setTimeout(dismiss, duration);
}

function setFlashToast(message, type = 'success', title = '', duration = 4000) {
  try {
    sessionStorage.setItem('vouchly_toast', JSON.stringify({ message, type, title, duration }));
  } catch (_) {}
}

window.showToast = showToast;
window.setFlashToast = setFlashToast;


// ─────────────────────────────────────────────
// CONFIRMATION MODAL
// ─────────────────────────────────────────────

/**
 * Show a confirmation dialog and return a Promise<boolean>.
 *
 * Usage:
 *   const confirmed = await confirmDialog('Delete this item?', 'This cannot be undone.');
 *   if (confirmed) { ... }
 */
function confirmDialog(title = 'Confirm Action', message = 'Are you sure?') {
  return new Promise((resolve) => {
    const modal   = document.getElementById('confirmModal');
    const titleEl = document.getElementById('confirmTitle');
    const msgEl   = document.getElementById('confirmMessage');
    const okBtn   = document.getElementById('confirmOk');
    const cancelBtn = document.getElementById('confirmCancel');

    if (!modal) { resolve(window.confirm(message)); return; }

    titleEl.textContent = title;
    msgEl.textContent   = message;
    modal.style.display = 'flex';

    const cleanup = () => { modal.style.display = 'none'; };

    const onOk     = () => { cleanup(); resolve(true); };
    const onCancel = () => { cleanup(); resolve(false); };

    okBtn.onclick     = onOk;
    cancelBtn.onclick = onCancel;

    // Close on backdrop click
    modal.onclick = (e) => { if (e.target === modal) onCancel(); };
  });
}

window.confirmDialog = confirmDialog;


// ─────────────────────────────────────────────
// THEME TOGGLE
// ─────────────────────────────────────────────

function initThemeToggle() {
  const toggleBtn  = document.getElementById('themeToggle');
  const themeIcon  = document.getElementById('themeIcon');
  const darkToggle = document.getElementById('darkModeToggle');

  const PREF_KEY = 'vouchly_theme';

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(PREF_KEY, theme);

    if (themeIcon) {
      themeIcon.className = theme === 'dark' ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
    }
    if (darkToggle) {
      darkToggle.checked = theme === 'dark';
    }
  }

  // Load saved preference
  const saved = localStorage.getItem(PREF_KEY) || 'light';
  applyTheme(saved);

  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });
  }

  if (darkToggle) {
    darkToggle.addEventListener('change', () => {
      applyTheme(darkToggle.checked ? 'dark' : 'light');
    });
  }
}

// ─────────────────────────────────────────────
// SAFE DOM HELPER
// ─────────────────────────────────────────────

/**
 * Escape HTML to prevent XSS when rendering user-supplied text.
 * Always use this before inserting user content into the DOM via innerHTML.
 */
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

window.escapeHtml = escapeHtml;

/**
 * Format a date string (ISO) to a readable format.
 */
function formatDate(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

window.formatDate = formatDate;

/**
 * Relative time (e.g. "3 days ago")
 */
function timeAgo(isoString) {
  if (!isoString) return '';
  const now  = new Date();
  const past = new Date(isoString);
  const diff = Math.floor((now - past) / 1000);

  if (diff < 60)     return 'just now';
  if (diff < 3600)   return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400)  return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return formatDate(isoString);
}

window.timeAgo = timeAgo;

/**
 * Render star icons for a rating value (1-5).
 * Returns an HTML string — safe to use because it contains no user data.
 */
function renderStars(rating) {
  if (!rating) return '';
  let html = '';
  for (let i = 1; i <= 5; i++) {
    html += i <= rating
      ? '<i class="fa-solid fa-star" style="color:var(--gold-warm)"></i>'
      : '<i class="fa-regular fa-star" style="color:var(--border-color)"></i>';
  }
  return html;
}

window.renderStars = renderStars;

/**
 * Render a status badge HTML string.
 */
function renderBadge(status) {
  const map = {
    pending:  ['badge-pending',  'Pending'],
    approved: ['badge-approved', 'Approved'],
    rejected: ['badge-rejected', 'Rejected'],
    archived: ['badge-archived', 'Archived'],
  };
  const [cls, label] = map[status] || ['badge-archived', status];
  return `<span class="badge ${cls}">${label}</span>`;
}

window.renderBadge = renderBadge;


// ─────────────────────────────────────────────
// API FETCH HELPER
// ─────────────────────────────────────────────

/**
 * A wrapper around fetch() for making API calls.
 * Automatically:
 *  - Adds Content-Type: application/json header
 *  - Parses JSON responses
 *  - Handles 401 Unauthorized by redirecting to login
 *  - Tries to refresh the token once on 401 before giving up
 *
 * @param {string} url     - API endpoint
 * @param {object} options - fetch options (method, body, etc.)
 * @returns {Promise<{data, ok, status}>}
 */
async function apiFetch(url, options = {}) {
  const defaults = {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
  };

  // Merge headers
  if (options.body instanceof FormData) {
    // Don't set Content-Type for FormData — browser sets it with boundary
    delete defaults.headers['Content-Type'];
  }

  const config = {
    ...defaults,
    ...options,
    headers: { ...defaults.headers, ...(options.headers || {}) },
  };

  let response = await fetch(url, config);

  const isAuthPage = ['/login', '/signup', '/forgot-password', '/reset-password', '/verification-pending', '/verify-email'].some(p => window.location.pathname.startsWith(p));
  const isAuthCheck = url.includes('/api/auth/me') || url.includes('/api/auth/login') || url.includes('/api/auth/signup');

  // Try token refresh on 401 (only for authenticated dashboard pages)
  if (response.status === 401 && !isAuthPage && !isAuthCheck && !options._retried) {
    try {
      const refreshRes = await fetch('/api/auth/refresh', { method: 'POST', credentials: 'same-origin' });
      if (refreshRes.ok) {
        config._retried = true;
        response = await fetch(url, config);
      } else {
        window.location.href = '/login';
        return { data: null, ok: false, status: 401 };
      }
    } catch (_) {
      window.location.href = '/login';
      return { data: null, ok: false, status: 401 };
    }
  }

  // Still 401 on protected page after refresh attempt? Send to login.
  if (response.status === 401 && !isAuthPage && !isAuthCheck) {
    window.location.href = '/login';
    return { data: null, ok: false, status: 401 };
  }

  let data = null;
  try {
    data = await response.json();
  } catch (_) {
    data = null;
  }

  return { data, ok: response.ok, status: response.status };
}

window.apiFetch = apiFetch;


// ─────────────────────────────────────────────
// BUTTON LOADING STATE
// ─────────────────────────────────────────────

function setButtonLoading(btn, loading) {
  const textEl    = btn.querySelector('.btn-text');
  const spinnerEl = btn.querySelector('.btn-spinner, .spinner');
  btn.disabled = loading;
  if (textEl)    textEl.style.opacity = loading ? '0' : '1';
  if (spinnerEl) spinnerEl.classList.toggle('hidden', !loading);
}

window.setButtonLoading = setButtonLoading;


// ─────────────────────────────────────────────
// COPY TO CLIPBOARD
// ─────────────────────────────────────────────

async function copyToClipboard(text, btn) {
  try {
    await navigator.clipboard.writeText(text);
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
      setTimeout(() => { btn.innerHTML = orig; }, 2000);
    }
    showToast('Copied to clipboard!', 'success');
  } catch (_) {
    showToast('Could not copy. Please copy manually.', 'error');
  }
}

window.copyToClipboard = copyToClipboard;


// ─────────────────────────────────────────────
// DASHBOARD: SIDEBAR + TOPBAR INTERACTIONS
// ─────────────────────────────────────────────

function initDashboardShell() {
  // Sidebar toggle (mobile)
  const hamburgerBtn   = document.getElementById('hamburgerBtn');
  const sidebar        = document.getElementById('sidebar');
  const sidebarOverlay = document.getElementById('sidebarOverlay');
  const sidebarClose   = document.getElementById('sidebarCloseBtn');

  function openSidebar() {
    sidebar?.classList.add('open');
    sidebarOverlay?.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar?.classList.remove('open');
    sidebarOverlay?.classList.remove('active');
    document.body.style.overflow = '';
  }

  hamburgerBtn?.addEventListener('click', openSidebar);
  sidebarClose?.addEventListener('click', closeSidebar);
  sidebarOverlay?.addEventListener('click', closeSidebar);

  // Notifications dropdown
  const notifBtn      = document.getElementById('notifBtn');
  const notifDropdown = document.getElementById('notifDropdown');

  notifBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    notifDropdown?.classList.toggle('open');
    if (notifDropdown?.classList.contains('open')) {
      loadNotifications();
    }
  });

  // Profile dropdown
  const profileBtn      = document.getElementById('profileBtn');
  const profileDropdown = document.getElementById('profileDropdown');

  profileBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    profileDropdown?.classList.toggle('open');
  });

  // Close dropdowns on outside click
  document.addEventListener('click', () => {
    notifDropdown?.classList.remove('open');
    profileDropdown?.classList.remove('open');
  });

  // Logout buttons
  ['logoutBtn', 'logoutBtn2', 'logoutSettingsBtn'].forEach(id => {
    document.getElementById(id)?.addEventListener('click', handleLogout);
  });

  // Mark notifications read
  document.getElementById('markAllRead')?.addEventListener('click', async () => {
    await apiFetch('/api/notifications/mark-read', { method: 'POST' });
    document.getElementById('notifDot')?.style && (document.getElementById('notifDot').style.display = 'none');
    document.querySelectorAll('.notif-item.unread').forEach(el => el.classList.remove('unread'));
  });

  // Load current owner info for topbar + sidebar
  loadCurrentOwner();

  // Copy buttons
  document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.dataset.target;
      const codeEl   = document.getElementById(targetId);
      if (codeEl) copyToClipboard(codeEl.textContent, btn);
    });
  });
}


async function handleLogout() {
  if (window.setFlashToast) {
    window.setFlashToast('You have been logged out successfully.', 'info', 'Signed Out');
  }
  try {
    await apiFetch('/api/auth/logout', { method: 'POST' });
  } catch (_) {}
  window.location.href = '/login';
}


async function loadCurrentOwner() {
  try {
    const { data, ok } = await apiFetch('/api/auth/me');
    if (!ok || !data?.success) return;

    const owner = data.data;
    const initial = (owner.full_name || 'O').charAt(0).toUpperCase();

    // Update sidebar
    const sidebarName  = document.getElementById('sidebarName');
    const sidebarEmail = document.getElementById('sidebarEmail');
    const sidebarAvatar = document.getElementById('sidebarAvatar');
    const topbarAvatar  = document.getElementById('topbarAvatar');
    const topbarName    = document.getElementById('topbarName');

    if (sidebarName)  sidebarName.textContent  = owner.full_name;
    if (sidebarEmail) sidebarEmail.textContent = owner.email;
    if (sidebarAvatar) sidebarAvatar.textContent = initial;
    if (topbarAvatar)  topbarAvatar.textContent  = initial;
    if (topbarName)    topbarName.textContent     = owner.full_name.split(' ')[0];

    // Update greeting if on dashboard
    const greeting = document.getElementById('ownerGreeting');
    if (greeting) greeting.textContent = owner.full_name.split(' ')[0];

    // Update "Wall of Love" link in sidebar based on first space
    updateWallLink();

    // Load pending badge count
    loadPendingCount();

  } catch (_) {}
}


async function loadNotifications() {
  const list = document.getElementById('notifList');
  const dot  = document.getElementById('notifDot');
  if (!list) return;

  try {
    const { data, ok } = await apiFetch('/api/notifications');
    if (!ok || !data?.success) return;

    const { notifications, unread_count } = data.data;

    if (dot) dot.style.display = unread_count > 0 ? 'block' : 'none';

    if (!notifications.length) {
      list.innerHTML = '<div class="notif-empty">No notifications yet.</div>';
      return;
    }

    list.innerHTML = '';
    notifications.forEach(n => {
      const item = document.createElement('div');
      item.className = `notif-item${n.is_read ? '' : ' unread'}`;

      const titleEl = document.createElement('div');
      titleEl.className = 'notif-item-title';
      titleEl.textContent = n.title;

      const msgEl = document.createElement('div');
      msgEl.className = 'notif-item-msg';
      msgEl.textContent = n.message;

      const timeEl = document.createElement('div');
      timeEl.className = 'notif-item-time';
      timeEl.textContent = timeAgo(n.created_at);

      item.appendChild(titleEl);
      item.appendChild(msgEl);
      item.appendChild(timeEl);
      list.appendChild(item);
    });
  } catch (_) {}
}


async function loadPendingCount() {
  try {
    const { data, ok } = await apiFetch('/api/dashboard/overview');
    if (!ok || !data?.success) return;
    const pending = data.data.pending;
    const badge = document.getElementById('pendingBadge');
    if (badge) {
      badge.textContent = pending;
      badge.style.display = pending > 0 ? 'inline' : 'none';
    }
  } catch (_) {}
}


async function updateWallLink() {
  try {
    const { data, ok } = await apiFetch('/api/spaces');
    if (!ok || !data?.success || !data.data.spaces.length) return;
    const firstSpace = data.data.spaces[0];
    const wallLink = document.getElementById('wallLink');
    if (wallLink) {
      wallLink.href = `/wall/${firstSpace.slug}`;
      wallLink.target = '_blank';
    }
  } catch (_) {}
}


// ─────────────────────────────────────────────
// FILE UPLOAD PREVIEW
// ─────────────────────────────────────────────

/**
 * Set up a file upload area with image preview.
 * @param {string} inputId       - The file <input> id
 * @param {string} previewId     - The preview container id
 * @param {string} previewImgId  - The <img> preview id
 * @param {string} placeholderId - The placeholder container id
 * @param {string} removeBtnId   - The remove button id
 */
function initFileUploadPreview(inputId, previewId, previewImgId, placeholderId, removeBtnId) {
  const input       = document.getElementById(inputId);
  const preview     = document.getElementById(previewId);
  const previewImg  = document.getElementById(previewImgId);
  const placeholder = document.getElementById(placeholderId);
  const removeBtn   = document.getElementById(removeBtnId);

  if (!input) return;

  input.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      showToast('File is too large. Maximum size is 5MB.', 'error');
      input.value = '';
      return;
    }

    const reader = new FileReader();
    reader.onload = (ev) => {
      if (previewImg) previewImg.src = ev.target.result;
      if (preview)    preview.style.display    = 'flex';
      if (placeholder) placeholder.style.display = 'none';
    };
    reader.readAsDataURL(file);
  });

  removeBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    input.value = '';
    if (previewImg) previewImg.src = '';
    if (preview)    preview.style.display    = 'none';
    if (placeholder) placeholder.style.display = 'flex';
  });

  // Drag and drop
  const area = input.parentElement;
  area?.addEventListener('dragover', (e) => { e.preventDefault(); area.style.borderColor = 'var(--gold)'; });
  area?.addEventListener('dragleave', () => { area.style.borderColor = ''; });
  area?.addEventListener('drop', (e) => {
    e.preventDefault();
    area.style.borderColor = '';
    const file = e.dataTransfer.files[0];
    if (file) {
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      input.dispatchEvent(new Event('change'));
    }
  });
}

window.initFileUploadPreview = initFileUploadPreview;


// ─────────────────────────────────────────────
// COLOR PICKER SYNC
// ─────────────────────────────────────────────

function initColorPickerSync(pickerId, textId) {
  const picker = document.getElementById(pickerId);
  const textEl = document.getElementById(textId);
  if (!picker || !textEl) return;

  picker.addEventListener('input', () => {
    textEl.value = picker.value;
  });

  textEl.addEventListener('input', () => {
    const val = textEl.value.trim();
    if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
      picker.value = val;
    }
  });
}

window.initColorPickerSync = initColorPickerSync;


// ─────────────────────────────────────────────
// INITIALISE ON LOAD
// ─────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initThemeToggle();

  // Only init dashboard shell if sidebar exists
  if (document.getElementById('sidebar')) {
    initDashboardShell();
  }

  // Responsive CSS: load responsive.css on every page
  if (!document.querySelector('link[href*="responsive.css"]')) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = '/static/css/responsive.css';
    document.head.appendChild(link);
  }

  // Check for any flash toast passed across page navigations
  try {
    const pendingToast = sessionStorage.getItem('vouchly_toast');
    if (pendingToast) {
      const { message, type, title, duration } = JSON.parse(pendingToast);
      sessionStorage.removeItem('vouchly_toast');
      setTimeout(() => {
        showToast(message, type || 'success', title || '', duration || 4000);
      }, 200);
    }
  } catch (_) {
    sessionStorage.removeItem('vouchly_toast');
  }
});
