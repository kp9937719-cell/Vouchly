/**
 * spaces.js — Spaces List, Create, Edit Pages
 * ==============================================
 */

'use strict';

// ─────────────────────────────────────────────
// SPACES LIST PAGE
// ─────────────────────────────────────────────

async function initSpacesPage() {
  await loadSpaces();

  // Delete modal
  const deleteModal   = document.getElementById('deleteModal');
  const deleteCancelBtn = document.getElementById('deleteCancelBtn');
  const deleteConfirmBtn = document.getElementById('deleteConfirmBtn');
  let pendingDeleteId = null;

  deleteCancelBtn?.addEventListener('click', () => {
    deleteModal.style.display = 'none';
    pendingDeleteId = null;
  });

  deleteConfirmBtn?.addEventListener('click', async () => {
    if (!pendingDeleteId) return;
    setButtonLoading(deleteConfirmBtn, true);
    const { data, ok } = await apiFetch(`/api/spaces/${pendingDeleteId}`, { method: 'DELETE' });
    setButtonLoading(deleteConfirmBtn, false);
    deleteModal.style.display = 'none';
    if (ok && data?.success) {
      showToast('Space deleted successfully.', 'success');
      loadSpaces();
    } else {
      showToast(data?.message || 'Could not delete space.', 'error');
    }
    pendingDeleteId = null;
  });

  window._openDeleteModal = (id, name) => {
    pendingDeleteId = id;
    document.getElementById('deleteSpaceName').textContent = name;
    deleteModal.style.display = 'flex';
  };
}

async function loadSpaces() {
  document.getElementById('skeletonGrid')?.remove();

  const { data, ok } = await apiFetch('/api/spaces');

  if (!ok || !data?.success) {
    showToast('Could not load spaces.', 'error');
    return;
  }

  const spaces  = data.data.spaces || [];
  const container = document.getElementById('spacesContainer');
  const emptyEl   = document.getElementById('emptySpaces');

  if (spaces.length === 0) {
    container.innerHTML = '';
    emptyEl.style.display = 'flex';
    return;
  }

  emptyEl.style.display = 'none';

  const grid = document.createElement('div');
  grid.className = 'spaces-grid';

  spaces.forEach(space => {
    const initial    = (space.name || '?').charAt(0).toUpperCase();
    const baseUrl    = window.location.origin;
    const collectUrl = `${baseUrl}/collect/${space.slug}`;
    const wallUrl    = `/wall/${space.slug}`;

    const card = document.createElement('div');
    card.className = 'space-card';
    card.innerHTML = `
      <div class="space-card-header">
        ${space.logo
          ? `<img class="space-logo" src="/${escapeHtml(space.logo)}" alt="${escapeHtml(space.name)}" />`
          : `<div class="space-logo-placeholder">${escapeHtml(initial)}</div>`
        }
        <div>
          <div class="space-name">${escapeHtml(space.name)}</div>
          <div class="space-business">${escapeHtml(space.business_name || '')}</div>
        </div>
        <div class="space-status">${space.is_active
          ? '<span class="badge badge-approved">Active</span>'
          : '<span class="badge badge-archived">Inactive</span>'}</div>
      </div>
      <div class="space-url">
        <span class="space-url-text">${escapeHtml(collectUrl)}</span>
        <button class="space-url-copy" data-url="${escapeHtml(collectUrl)}" title="Copy link">
          <i class="fa-solid fa-copy"></i>
        </button>
      </div>
      <div class="space-counts">
        <div class="space-count">
          <span class="space-count-num">${space.pending_count || 0}</span>
          <span class="space-count-label">Pending</span>
        </div>
        <div class="space-count">
          <span class="space-count-num">${space.approved_count || 0}</span>
          <span class="space-count-label">Approved</span>
        </div>
        <div class="space-count">
          <span class="space-count-num">${space.total_count || 0}</span>
          <span class="space-count-label">Total</span>
        </div>
      </div>
      <div class="space-card-actions">
        <a href="/spaces/${space.id}/edit" class="btn btn-secondary btn-sm">
          <i class="fa-solid fa-pen"></i> Edit
        </a>
        <a href="${escapeHtml(wallUrl)}" class="btn btn-ghost btn-sm" target="_blank">
          <i class="fa-solid fa-heart"></i> Wall
        </a>
        <a href="${escapeHtml(collectUrl)}" class="btn btn-ghost btn-sm" target="_blank">
          <i class="fa-solid fa-arrow-up-right-from-square"></i>
        </a>
        <button class="btn btn-ghost btn-sm" onclick="_openDeleteModal('${space.id}','${escapeHtml(space.name)}')">
          <i class="fa-solid fa-trash"></i>
        </button>
      </div>
    `;

    // Copy link button
    card.querySelector('.space-url-copy')?.addEventListener('click', (e) => {
      e.stopPropagation();
      copyToClipboard(e.currentTarget.dataset.url);
    });

    grid.appendChild(card);
  });

  container.innerHTML = '';
  container.appendChild(grid);
}

// ─────────────────────────────────────────────
// CREATE SPACE PAGE
// ─────────────────────────────────────────────

function initCreateSpacePage() {
  // File upload preview
  initFileUploadPreview('logo', 'logoPreview', 'logoPreviewImg', 'logoPlaceholder', 'removeLogoBtn');

  // Color picker sync
  initColorPickerSync('brand_color', 'brand_color_text');

  // Live preview updates
  ['name', 'description', 'welcome_heading'].forEach(id => {
    document.getElementById(id)?.addEventListener('input', updateLivePreview);
  });

  document.getElementById('logo')?.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const img = document.getElementById('previewLogoImg');
        if (img) { img.src = ev.target.result; img.style.display = 'block'; }
        const placeholder = document.getElementById('previewLogoPlaceholder');
        if (placeholder) placeholder.style.display = 'none';
      };
      reader.readAsDataURL(file);
    }
  });

  document.getElementById('brand_color')?.addEventListener('input', (e) => {
    document.getElementById('previewBtn')?.style.setProperty('background', e.target.value);
  });

  document.getElementById('enable_star_rating')?.addEventListener('change', (e) => {
    const stars = document.getElementById('previewStars');
    if (stars) stars.style.display = e.target.checked ? 'flex' : 'none';
  });

  // Auto-generate slug from name
  const nameInput = document.getElementById('name');
  const slugInput = document.getElementById('slug');
  let slugManuallyEdited = false;

  slugInput?.addEventListener('input', () => { slugManuallyEdited = true; });

  nameInput?.addEventListener('input', () => {
    if (!slugManuallyEdited && slugInput) {
      slugInput.value = nameInput.value
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .substring(0, 60);
    }
    updateLivePreview();
  });

  // Custom questions
  const questionsContainer = document.getElementById('questionsContainer');
  const addQuestionBtn     = document.getElementById('addQuestionBtn');
  let questionCount = 0;

  addQuestionBtn?.addEventListener('click', () => {
    if (questionCount >= 5) { showToast('Maximum 5 custom questions allowed.', 'warning'); return; }
    questionCount++;
    const item = document.createElement('div');
    item.className = 'question-item';
    item.innerHTML = `
      <input type="text" name="questions[]" class="form-input"
             placeholder="Question ${questionCount}" maxlength="200" />
      <button type="button" class="remove-question-btn" aria-label="Remove question">
        <i class="fa-solid fa-xmark"></i>
      </button>
    `;
    item.querySelector('.remove-question-btn').addEventListener('click', () => {
      item.remove();
      questionCount--;
    });
    questionsContainer.appendChild(item);
  });

  // Form submission
  const form = document.getElementById('createSpaceForm');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('createSpaceBtn');
    setButtonLoading(btn, true);
    hideAlert();

    const formData = new FormData(form);
    formData.set('enable_star_rating', document.getElementById('enable_star_rating')?.checked ? 'true' : 'false');
    formData.set('require_avatar', document.getElementById('require_avatar')?.checked ? 'true' : 'false');

    // Collect custom questions
    const questions = Array.from(form.querySelectorAll('input[name="questions[]"]'))
      .map(el => el.value.trim())
      .filter(Boolean);

    // Build JSON body (spaces API accepts JSON with fields)
    // Use FormData for file upload
    if (questions.length) {
      formData.set('custom_questions', JSON.stringify(questions));
    }

    const { data, ok } = await apiFetch('/api/spaces', {
      method: 'POST',
      body: formData,
    });

    setButtonLoading(btn, false);

    if (ok && data?.success) {
      showToast('Space created successfully!', 'success');
      setTimeout(() => { window.location.href = '/spaces'; }, 1000);
    } else {
      showAlert(data?.message || 'Failed to create space.');
    }
  });

  updateLivePreview();
}

function updateLivePreview() {
  const heading = document.getElementById('welcome_heading')?.value || 'Share your experience with us!';
  const desc    = document.getElementById('description')?.value    || 'We\'d love to hear your feedback.';
  const hEl = document.getElementById('previewHeading');
  const dEl = document.getElementById('previewDesc');
  if (hEl) hEl.textContent = heading || 'Share your experience with us!';
  if (dEl) dEl.textContent = desc    || 'We\'d love to hear your feedback.';
}

function showAlert(message) {
  const el = document.getElementById('formError');
  if (el) { el.textContent = message; el.style.display = 'block'; }
}

function hideAlert() {
  const el = document.getElementById('formError');
  if (el) el.style.display = 'none';
}

// ─────────────────────────────────────────────
// EDIT SPACE PAGE
// ─────────────────────────────────────────────

async function initEditSpacePage() {
  const spaceId = document.getElementById('spaceId')?.value;
  if (!spaceId) return;

  // Load space data
  const { data, ok } = await apiFetch(`/api/spaces/${spaceId}`);

  if (!ok || !data?.success) {
    showToast('Could not load space data.', 'error');
    return;
  }

  const space = data.data;

  // Show form
  document.getElementById('editFormSkeleton').style.display = 'none';
  document.getElementById('editFormContainer').style.display = 'block';

  // Populate fields
  document.getElementById('name').value         = space.name || '';
  document.getElementById('slug').value         = space.slug || '';
  document.getElementById('business_name').value = space.business_name || '';
  document.getElementById('welcome_heading').value = space.welcome_heading || '';
  document.getElementById('description').value  = space.description || '';
  document.getElementById('thank_you_message').value = space.thank_you_message || '';
  document.getElementById('enable_star_rating').checked = space.enable_star_rating !== false;
  document.getElementById('is_active').checked = space.is_active !== false;

  const brandColor = space.brand_color || '#B89A5A';
  document.getElementById('brand_color').value      = brandColor;
  document.getElementById('brand_color_text').value = brandColor;

  // Show existing logo
  if (space.logo) {
    const previewImg = document.getElementById('logoPreviewImg');
    const preview    = document.getElementById('logoPreview');
    const placeholder = document.getElementById('logoPlaceholder');
    if (previewImg) previewImg.src = `/${space.logo}`;
    if (preview)    preview.style.display    = 'flex';
    if (placeholder) placeholder.style.display = 'none';
  }

  // Update preview and wall links
  const baseUrl = window.location.origin;
  document.getElementById('previewLink')?.setAttribute('href', `/collect/${space.slug}`);

  document.getElementById('copyLinkBtn')?.addEventListener('click', () => {
    copyToClipboard(`${baseUrl}/collect/${space.slug}`);
  });

  // Init file upload + color
  initFileUploadPreview('logo', 'logoPreview', 'logoPreviewImg', 'logoPlaceholder', 'removeLogoBtn');
  initColorPickerSync('brand_color', 'brand_color_text');

  // Form submission
  const form = document.getElementById('editSpaceForm');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('saveSpaceBtn');
    setButtonLoading(btn, true);

    const formData = new FormData(form);
    formData.set('is_active', document.getElementById('is_active')?.checked ? 'true' : 'false');
    formData.set('enable_star_rating', document.getElementById('enable_star_rating')?.checked ? 'true' : 'false');

    const { data: res, ok: resOk } = await apiFetch(`/api/spaces/${spaceId}`, {
      method: 'PATCH',
      body: formData,
    });

    setButtonLoading(btn, false);

    if (resOk && res?.success) {
      showToast('Space updated successfully!', 'success');
      const successEl = document.getElementById('formSuccess');
      if (successEl) { successEl.textContent = 'Changes saved.'; successEl.style.display = 'block'; }
    } else {
      const errEl = document.getElementById('formError');
      if (errEl) { errEl.textContent = res?.message || 'Failed to save changes.'; errEl.style.display = 'block'; }
    }
  });
}
