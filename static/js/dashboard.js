/**
 * dashboard.js — Dashboard Overview
 * ====================================
 * Loads metrics, recent testimonials, chart data, and activity feed.
 */

'use strict';

let ratingChart = null;

async function initDashboard() {
  await loadDashboardData();
}

async function loadDashboardData() {
  const { data, ok } = await apiFetch('/api/dashboard/overview');

  if (!ok || !data?.success) {
    showToast('Could not load dashboard data.', 'error');
    return;
  }

  const d = data.data;

  // ── Show / hide empty state ──
  if (d.total_spaces === 0) {
    document.getElementById('emptyDashboard').style.display = 'flex';
    document.getElementById('metricsGrid').style.display   = 'none';
    document.getElementById('quickActions').style.display  = 'none';
    document.querySelector('.dashboard-grid')?.remove();
    return;
  }

  document.getElementById('emptyDashboard').style.display = 'none';
  document.getElementById('quickActions').style.display   = 'flex';

  // ── Metric cards ──
  renderMetricCards(d);

  // ── Quick action: pending count ──
  const qaReview = document.getElementById('qaReview');
  if (qaReview && d.pending > 0) {
    qaReview.innerHTML = `<i class="fa-solid fa-inbox"></i> <span>Review Pending (${d.pending})</span>`;
    qaReview.style.borderColor = 'var(--warning)';
    qaReview.style.color       = 'var(--warning)';
  }

  // ── Recent testimonials ──
  renderRecentTestimonials(d.recent_testimonials || []);

  // ── Rating chart ──
  renderRatingChart(d.rating_distribution || {});

  // ── Activity ──
  renderActivity(d.recent_moderation_activity || []);
}

function renderMetricCards(d) {
  const grid = document.getElementById('metricsGrid');
  if (!grid) return;

  const avgRating = d.average_rating ? d.average_rating.toFixed(1) : '—';

  grid.innerHTML = `
    <div class="metric-card">
      <div class="metric-icon"><i class="fa-solid fa-layer-group"></i></div>
      <div class="metric-label">Spaces</div>
      <div class="metric-value">${d.total_spaces}</div>
      <div class="metric-sub">collection pages</div>
    </div>
    <div class="metric-card">
      <div class="metric-icon"><i class="fa-solid fa-inbox"></i></div>
      <div class="metric-label">Pending</div>
      <div class="metric-value" style="${d.pending > 0 ? 'color:var(--warning)' : ''}">${d.pending}</div>
      <div class="metric-sub">awaiting review</div>
    </div>
    <div class="metric-card">
      <div class="metric-icon"><i class="fa-solid fa-circle-check"></i></div>
      <div class="metric-label">Approved</div>
      <div class="metric-value" style="color:var(--success)">${d.approved}</div>
      <div class="metric-sub">live testimonials</div>
    </div>
    <div class="metric-card">
      <div class="metric-icon"><i class="fa-solid fa-star"></i></div>
      <div class="metric-label">Avg. Rating</div>
      <div class="metric-value metric-value--gold">${avgRating}</div>
      <div class="metric-sub">out of 5.0</div>
    </div>
    <div class="metric-card">
      <div class="metric-icon"><i class="fa-solid fa-heart"></i></div>
      <div class="metric-label">Total</div>
      <div class="metric-value">${d.total}</div>
      <div class="metric-sub">all submissions</div>
    </div>
  `;
}

function renderRecentTestimonials(testimonials) {
  const container = document.getElementById('recentTestimonials');
  if (!container) return;

  if (!testimonials.length) {
    container.innerHTML = '<div class="empty-state-sm"><p>No testimonials yet.</p></div>';
    return;
  }

  container.innerHTML = '';
  testimonials.forEach(t => {
    const initial = (t.customer_name || '?').charAt(0).toUpperCase();
    const item = document.createElement('a');
    item.href = `/testimonials/${t.id}`;
    item.className = 'recent-test-item';
    item.innerHTML = `
      <div class="recent-test-avatar">${escapeHtml(initial)}</div>
      <div class="recent-test-info">
        <div class="recent-test-name">${escapeHtml(t.customer_name)}</div>
        <div class="recent-test-preview">${escapeHtml(t.review_text)}</div>
      </div>
      <div class="recent-test-meta">
        ${renderBadge(t.status)}
        <span class="recent-test-date">${timeAgo(t.submitted_at)}</span>
      </div>
    `;
    container.appendChild(item);
  });
}

function renderRatingChart(distribution) {
  const canvas   = document.getElementById('ratingChart');
  const noRating = document.getElementById('noRatingsMsg');

  const total = Object.values(distribution).reduce((a, b) => a + b, 0);

  if (!canvas) return;

  if (total === 0) {
    canvas.parentElement.style.display = 'none';
    if (noRating) noRating.style.display = 'block';
    return;
  }

  if (noRating) noRating.style.display = 'none';

  const labels = ['5 ★', '4 ★', '3 ★', '2 ★', '1 ★'];
  const values = [
    distribution['5'] || 0,
    distribution['4'] || 0,
    distribution['3'] || 0,
    distribution['2'] || 0,
    distribution['1'] || 0,
  ];

  if (ratingChart) ratingChart.destroy();

  ratingChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: 'rgba(184,154,90,0.7)',
        borderColor: 'rgba(184,154,90,1)',
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          beginAtZero: true,
          ticks: { precision: 0, color: 'var(--text-secondary)' },
          grid: { color: 'var(--border-color)' },
        },
        y: {
          ticks: { color: 'var(--text-secondary)' },
          grid: { display: false },
        },
      },
    },
  });
}

function renderActivity(activity) {
  const container = document.getElementById('recentActivity');
  if (!container) return;

  if (!activity.length) {
    container.innerHTML = '<div class="empty-state-sm"><p>No recent activity.</p></div>';
    return;
  }

  container.innerHTML = '';
  activity.forEach(a => {
    const item = document.createElement('div');
    item.className = 'activity-item';
    item.innerHTML = `
      <div class="activity-dot"></div>
      <div>
        <div class="activity-text">${escapeHtml(a.description || a.action || '')}</div>
        <div class="activity-time">${timeAgo(a.performed_at)}</div>
      </div>
    `;
    container.appendChild(item);
  });
}
