/**
 * testimonials.js — Moderation Inbox + Detail Page
 * ===================================================
 */

'use strict';

let currentPage   = 1;
let currentStatus = 'all';
let currentSpaceId = '';
let searchTimeout  = null;
let pendingDeleteId = null;
let pendingEditId   = null;

async function initTestimonialsPage() {
  // Load spaces for the space selector
  await loadSpacesForSelector();

  // Tab switching
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('active');
      btn.setAttribute('aria-selected', 'true');
      currentStatus = btn.dataset.status || 'all';
      currentPage = 1;
      loadTestimonials();
    });
  });

  // Space selector
  document.getElementById('spaceSelect')?.addEventListener('change', (e) => {
    currentSpaceId = e.target.value;
    currentPage = 1;
    loadTestimonials();
  });

  // Search
  document.getElementById('searchInput')?.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      currentPage = 1;
      loadTestimonials();
    }, 400);
  });

  // Rating filter
  document.getElementById('ratingFilter')?.addEventListener('change', () => {
    currentPage = 1;
    loadTestimonials();
  });

  // Sort
  document.getElementById('sortSelect')?.addEventListener('change', () => {
    currentPage = 1;
    loadTestimonials();
  });

  // Clear filters
  document.getElementById('clearFiltersBtn')?.addEventListener('click', () => {
    document.getElementById('searchInput').value = '';
    document.getElementById('ratingFilter').value = '';
    document.getElementById('sortSelect').value = 'newest';
    currentPage = 1;
    loadTestimonials();
  });

  // Pagination
  document.getElementById('prevPageBtn')?.addEventListener('click', () => {
    if (currentPage > 1) { currentPage--; loadTestimonials(); }
  });

  document.getElementById('nextPageBtn')?.addEventListener('click', () => {
    currentPage++;
    loadTestimonials();
  });

  // Edit modal
  document.getElementById('editModalClose')?.addEventListener('click', closeEditModal);
  document.getElementById('editModalCancel')?.addEventListener('click', closeEditModal);
  document.getElementById('editModalSave')?.addEventListener('click', saveEditedTestimonial);

  // Delete modal
  document.getElementById('deleteCancelBtn')?.addEventListener('click', () => {
    document.getElementById('deleteModal').style.display = 'none';
    pendingDeleteId = null;
  });

  document.getElementById('deleteConfirmBtn')?.addEventListener('click', async () => {
    if (!pendingDeleteId) return;
    const btn = document.getElementById('deleteConfirmBtn');
    setButtonLoading(btn, true);
    const { data, ok } = await apiFetch(`/api/testimonials/${pendingDeleteId}`, { method: 'DELETE' });
    setButtonLoading(btn, false);
    document.getElementById('deleteModal').style.display = 'none';
    if (ok) { showToast('Testimonial deleted.', 'success'); loadTestimonials(); }
    else showToast(data?.message || 'Could not delete.', 'error');
    pendingDeleteId = null;
  });

  // Initial load
  loadTestimonials();
}

async function loadSpacesForSelector() {
  const select = document.getElementById('spaceSelect');
  if (!select) return;

  const { data, ok } = await apiFetch('/api/spaces');
  if (!ok || !data?.success) return;

  const spaces = data.data.spaces || [];
  select.innerHTML = '<option value="">All spaces</option>';
  spaces.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.id;
    opt.textContent = s.name;
    select.appendChild(opt);
  });
}

async function loadTestimonials() {
  const searchQuery = document.getElementById('searchInput')?.value.trim() || '';
  const rating      = document.getElementById('ratingFilter')?.value || '';
  const sort        = document.getElementById('sortSelect')?.value || 'newest';

  const params = new URLSearchParams({
    page:     currentPage,
    per_page: 15,
    sort,
  });

  if (currentStatus !== 'all') params.set('status', currentStatus);
  if (currentSpaceId)          params.set('space_id', currentSpaceId);
  if (searchQuery)             params.set('search', searchQuery);
  if (rating)                  params.set('rating', rating);

  const endpoint = currentSpaceId
    ? `/api/spaces/${currentSpaceId}/testimonials?${params}`
    : `/api/testimonials?${params}`;

  document.getElementById('skeletonList')?.remove();
  document.getElementById('emptyState').style.display = 'none';
  document.getElementById('paginationBar').style.display = 'none';

  const listContainer = document.getElementById('testimonialsContainer');
  listContainer.innerHTML = `
    <div id="skeletonList" class="testimonials-list">
      <div class="testimonial-card skeleton-card"><div class="skeleton skeleton-block" style="height:120px"></div></div>
      <div class="testimonial-card skeleton-card"><div class="skeleton skeleton-block" style="height:120px"></div></div>
    </div>
  `;

  const { data, ok } = await apiFetch(endpoint);

  document.getElementById('skeletonList')?.remove();

  if (!ok || !data?.success) {
    showToast('Could not load testimonials.', 'error');
    return;
  }

  const { testimonials, pagination } = data.data;

  // Update tab counts
  if (data.data.counts) {
    const c = data.data.counts;
    const countAll      = document.getElementById('countAll');
    const countPending  = document.getElementById('countPending');
    const countApproved = document.getElementById('countApproved');
    const countRejected = document.getElementById('countRejected');
    if (countAll)      countAll.textContent      = c.all      > 0 ? c.all      : '';
    if (countPending)  countPending.textContent  = c.pending  > 0 ? c.pending  : '';
    if (countApproved) countApproved.textContent = c.approved > 0 ? c.approved : '';
    if (countRejected) countRejected.textContent = c.rejected > 0 ? c.rejected : '';
  }

  if (!testimonials.length) {
    document.getElementById('emptyState').style.display = 'flex';
    document.getElementById('emptyTitle').textContent   = 'No testimonials';
    document.getElementById('emptyMessage').textContent =
      currentStatus !== 'all'
        ? `No ${currentStatus} testimonials match your filters.`
        : 'No testimonials found.';
    return;
  }

  // Render list
  const list = document.createElement('div');
  list.className = 'testimonials-list';

  testimonials.forEach(t => {
    list.appendChild(buildTestimonialCard(t));
  });

  listContainer.appendChild(list);

  // Pagination
  if (pagination && pagination.total_pages > 1) {
    const bar   = document.getElementById('paginationBar');
    const info  = document.getElementById('pageInfo');
    const prev  = document.getElementById('prevPageBtn');
    const next  = document.getElementById('nextPageBtn');

    bar.style.display = 'flex';
    info.textContent  = `Page ${pagination.page} of ${pagination.total_pages}`;
    prev.disabled     = !pagination.has_prev;
    next.disabled     = !pagination.has_next;
  }
}

function buildTestimonialCard(t) {
  const initial = (t.customer_name || '?').charAt(0).toUpperCase();
  const card    = document.createElement('div');
  card.className = `testimonial-card${t.is_featured ? ' testimonial-card--featured' : ''}`;
  card.dataset.id = t.id;

  card.innerHTML = `
    <div class="testimonial-card-header">
      ${t.avatar
        ? `<img class="t-avatar" src="/${escapeHtml(t.avatar)}" alt="${escapeHtml(t.customer_name)}" />`
        : `<div class="t-avatar-placeholder">${escapeHtml(initial)}</div>`
      }
      <div class="t-info">
        <div class="t-name">${escapeHtml(t.customer_name)}</div>
        <div class="t-meta">${escapeHtml([t.company_role, t.company_name].filter(Boolean).join(' · '))}</div>
        <div class="t-email">${escapeHtml(t.customer_email || '')}</div>
      </div>
      <div class="t-header-right">
        ${renderBadge(t.status)}
        <span class="t-date">${timeAgo(t.submitted_at)}</span>
        <div class="t-indicators">
          ${t.is_featured ? '<span class="t-indicator featured"><i class="fa-solid fa-star"></i></span>' : ''}
          ${t.likes > 0  ? `<span class="t-indicator liked"><i class="fa-solid fa-heart"></i> ${t.likes}</span>` : ''}
        </div>
      </div>
    </div>
    ${t.rating ? `<div class="t-stars">${renderStars(t.rating)}</div>` : ''}
    <div class="t-review">${escapeHtml(t.review_text)}</div>
    <div class="t-actions">
      ${t.status === 'pending' ? `
        <button class="t-action-btn approve-btn" data-action="approve">
          <i class="fa-solid fa-check"></i> Approve
        </button>
        <button class="t-action-btn reject-btn" data-action="reject">
          <i class="fa-solid fa-xmark"></i> Reject
        </button>` : ''}
      ${t.status === 'approved' ? `
        <button class="t-action-btn" data-action="archive">
          <i class="fa-solid fa-box-archive"></i> Archive
        </button>` : ''}
      ${t.status === 'archived' ? `
        <button class="t-action-btn" data-action="restore">
          <i class="fa-solid fa-rotate-left"></i> Restore
        </button>` : ''}
      ${t.status === 'approved' ? `
        <button class="t-action-btn feature-btn${t.is_featured ? ' active' : ''}" data-action="feature">
          <i class="fa-solid fa-star"></i> ${t.is_featured ? 'Unfeature' : 'Feature'}
        </button>` : ''}
      <button class="t-action-btn like-btn${t.liked ? ' active' : ''}" data-action="like">
        <i class="fa-solid fa-heart"></i> ${t.likes || 0}
      </button>
      <div class="t-actions-spacer"></div>
      <a href="/testimonials/${t.id}" class="t-action-btn">
        <i class="fa-solid fa-eye"></i> View
      </a>
      <button class="t-action-btn edit-btn" data-action="edit">
        <i class="fa-solid fa-pen"></i> Edit
      </button>
      <button class="t-action-btn delete-btn" data-action="delete">
        <i class="fa-solid fa-trash"></i>
      </button>
    </div>
  `;

  // Bind action buttons
  card.querySelectorAll('[data-action]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      handleTestimonialAction(btn.dataset.action, t.id, card);
    });
  });

  return card;
}

async function handleTestimonialAction(action, id, card) {
  if (action === 'delete') {
    pendingDeleteId = id;
    document.getElementById('deleteModal').style.display = 'flex';
    return;
  }

  if (action === 'edit') {
    pendingEditId = id;
    document.getElementById('editTestimonialId').value = id;
    document.getElementById('editCustomerName').value =
      card.querySelector('.t-name')?.textContent || '';
    document.getElementById('editReviewText').value =
      card.querySelector('.t-review')?.textContent || '';
    document.getElementById('editModal').style.display = 'flex';
    return;
  }

  const actionMap = {
    approve: `/api/testimonials/${id}/approve`,
    reject:  `/api/testimonials/${id}/reject`,
    archive: `/api/testimonials/${id}/archive`,
    restore: `/api/testimonials/${id}/restore`,
    feature: `/api/testimonials/${id}/feature`,
    like:    `/api/testimonials/${id}/like`,
  };

  const url = actionMap[action];
  if (!url) return;

  const { data, ok } = await apiFetch(url, { method: 'POST' });

  if (ok) {
    showToast(data?.message || 'Action completed.', 'success');
    loadTestimonials();
  } else {
    showToast(data?.message || 'Action failed.', 'error');
  }
}

function closeEditModal() {
  document.getElementById('editModal').style.display = 'none';
  pendingEditId = null;
}

async function saveEditedTestimonial() {
  if (!pendingEditId) return;
  const name   = document.getElementById('editCustomerName')?.value.trim();
  const review = document.getElementById('editReviewText')?.value.trim();

  if (!name || !review) { showToast('Name and review cannot be empty.', 'error'); return; }

  const btn = document.getElementById('editModalSave');
  setButtonLoading(btn, true);

  const { data, ok } = await apiFetch(`/api/testimonials/${pendingEditId}`, {
    method: 'PATCH',
    body: JSON.stringify({ customer_name: name, review_text: review }),
  });

  setButtonLoading(btn, false);

  if (ok) {
    closeEditModal();
    showToast('Testimonial updated.', 'success');
    loadTestimonials();
  } else {
    showToast(data?.message || 'Update failed.', 'error');
  }
}

// ─────────────────────────────────────────────
// TESTIMONIAL DETAIL PAGE
// ─────────────────────────────────────────────

async function initTestimonialDetailPage(id) {
  if (!id) return;

  const container = document.getElementById('testimonialDetailContainer');

  const { data, ok } = await apiFetch(`/api/testimonials/${id}`);

  if (!ok || !data?.success) {
    container.innerHTML = '<div class="empty-state"><p>Testimonial not found.</p></div>';
    return;
  }

  const t = data.data;

  container.innerHTML = `
    <div class="testimonial-detail-card">
      <div class="detail-header">
        ${t.avatar
          ? `<img class="detail-avatar-lg" src="/${escapeHtml(t.avatar)}" alt="${escapeHtml(t.customer_name)}" />`
          : `<div class="detail-avatar-placeholder">${escapeHtml((t.customer_name || '?').charAt(0).toUpperCase())}</div>`
        }
        <div>
          <h2>${escapeHtml(t.customer_name)}</h2>
          <p>${escapeHtml([t.company_role, t.company_name].filter(Boolean).join(' · '))}</p>
          <p>${escapeHtml(t.customer_email)}</p>
          ${t.rating ? `<div class="t-stars" style="margin-top:0.5rem">${renderStars(t.rating)}</div>` : ''}
          <div style="margin-top:0.75rem">${renderBadge(t.status)}</div>
        </div>
      </div>
      <div class="detail-review">"${escapeHtml(t.review_text)}"</div>
      <div class="detail-actions">
        ${t.status === 'pending' ? `
          <button class="btn btn-primary" onclick="runAction('approve','${t.id}')">Approve</button>
          <button class="btn btn-danger" onclick="runAction('reject','${t.id}')">Reject</button>` : ''}
        ${t.status === 'approved' ? `
          <button class="btn btn-secondary" onclick="runAction('archive','${t.id}')">Archive</button>
          <button class="btn btn-ghost" onclick="runAction('feature','${t.id}')">
            ${t.is_featured ? 'Unfeature' : 'Feature'}
          </button>` : ''}
        <button class="btn btn-ghost text-danger" onclick="runAction('delete','${t.id}')">
          <i class="fa-solid fa-trash"></i> Delete
        </button>
      </div>
    </div>
  `;
}

async function runAction(action, id) {
  if (action === 'delete') {
    const confirmed = await confirmDialog('Delete Testimonial', 'This cannot be undone.');
    if (!confirmed) return;
    const { ok } = await apiFetch(`/api/testimonials/${id}`, { method: 'DELETE' });
    if (ok) { showToast('Deleted.', 'success'); setTimeout(() => window.location.href = '/testimonials', 1000); }
    return;
  }

  const { data, ok } = await apiFetch(`/api/testimonials/${id}/${action}`, { method: 'POST' });
  if (ok) { showToast(data?.message || 'Done.', 'success'); initTestimonialDetailPage(id); }
  else showToast(data?.message || 'Failed.', 'error');
}

window.runAction = runAction;
