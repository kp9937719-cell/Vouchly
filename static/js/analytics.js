/**
 * analytics.js — Analytics Dashboard Page
 * ==========================================
 */

'use strict';

let ratingBarChart = null;
let trendLineChart = null;
let selectedSpaceId = '';

async function initAnalyticsPage() {
  // Load spaces for dropdown
  const select = document.getElementById('analyticsSpaceSelect');
  if (!select) return;

  const { data, ok } = await apiFetch('/api/spaces');
  if (!ok || !data?.success) { showToast('Could not load spaces.', 'error'); return; }

  const spaces = data.data.spaces || [];
  if (!spaces.length) {
    document.getElementById('analyticsEmpty').innerHTML =
      '<div class="empty-icon"><i class="fa-solid fa-layer-group"></i></div><h2>No spaces yet</h2><p>Create a space to see analytics.</p><a href="/spaces/new" class="btn btn-primary">Create Space</a>';
    return;
  }

  spaces.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.id;
    opt.textContent = s.name;
    select.appendChild(opt);
  });

  select.addEventListener('change', async (e) => {
    selectedSpaceId = e.target.value;
    if (!selectedSpaceId) return;
    document.getElementById('analyticsEmpty').style.display   = 'none';
    document.getElementById('analyticsContent').style.display = 'block';
    await loadSpaceAnalytics(selectedSpaceId);
  });

  // Days selector for trend
  document.getElementById('trendDaysSelect')?.addEventListener('change', async () => {
    if (selectedSpaceId) await loadTrend(selectedSpaceId);
  });
}

async function loadSpaceAnalytics(spaceId) {
  const { data, ok } = await apiFetch(`/api/spaces/${spaceId}/analytics`);
  if (!ok || !data?.success) { showToast('Could not load analytics.', 'error'); return; }

  const d = data.data;

  // Metric cards
  renderAnalyticsMetrics(d);

  // Rating distribution
  renderRatingDistChart(d.rating_distribution, d.average_rating);

  // Trend
  renderTrendChart(d.submission_trend);
}

async function loadTrend(spaceId) {
  const days = document.getElementById('trendDaysSelect')?.value || 30;
  const { data, ok } = await apiFetch(`/api/spaces/${spaceId}/analytics?trend_days=${days}`);
  if (!ok || !data?.success) return;
  renderTrendChart(data.data.submission_trend);
}

function renderAnalyticsMetrics(d) {
  const grid = document.getElementById('analyticsMetrics');
  if (!grid) return;

  const avg = d.average_rating ? d.average_rating.toFixed(1) : '—';

  grid.innerHTML = `
    <div class="metric-card">
      <div class="metric-icon"><i class="fa-solid fa-comment-dots"></i></div>
      <div class="metric-label">Total</div>
      <div class="metric-value">${d.total || 0}</div>
      <div class="metric-sub">all submissions</div>
    </div>
    <div class="metric-card">
      <div class="metric-icon"><i class="fa-solid fa-clock"></i></div>
      <div class="metric-label">Pending</div>
      <div class="metric-value" style="color:var(--warning)">${d.pending || 0}</div>
    </div>
    <div class="metric-card">
      <div class="metric-icon"><i class="fa-solid fa-circle-check"></i></div>
      <div class="metric-label">Approved</div>
      <div class="metric-value" style="color:var(--success)">${d.approved || 0}</div>
    </div>
    <div class="metric-card">
      <div class="metric-icon"><i class="fa-solid fa-star"></i></div>
      <div class="metric-label">Avg. Rating</div>
      <div class="metric-value metric-value--gold">${avg}</div>
    </div>
  `;
}

function renderRatingDistChart(distribution, avgRating) {
  const canvas = document.getElementById('ratingBarChart');
  const noEl   = document.getElementById('noRatingDist');
  const avgEl  = document.getElementById('avgRatingLabel');

  if (!distribution || !Object.keys(distribution).length) {
    if (canvas) canvas.parentElement.style.display = 'none';
    if (noEl)   noEl.style.display = 'block';
    return;
  }

  if (noEl) noEl.style.display = 'none';
  if (avgEl && avgRating) avgEl.textContent = `Average: ${avgRating.toFixed(1)} ★`;

  const labels = ['1 ★','2 ★','3 ★','4 ★','5 ★'];
  const values = [1,2,3,4,5].map(i => distribution[i] || 0);

  if (ratingBarChart) ratingBarChart.destroy();

  ratingBarChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: [
          'rgba(185,74,72,0.6)',
          'rgba(185,133,44,0.6)',
          'rgba(184,154,90,0.6)',
          'rgba(71,122,91,0.6)',
          'rgba(71,122,91,0.9)',
        ],
        borderWidth: 0,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: 'var(--text-secondary)' }, grid: { display: false } },
        y: { beginAtZero: true, ticks: { precision: 0, color: 'var(--text-secondary)' }, grid: { color: 'var(--border-color)' } },
      },
    },
  });
}

function renderTrendChart(trend) {
  const canvas = document.getElementById('trendLineChart');
  if (!canvas || !trend?.length) return;

  const labels = trend.map(d => {
    const dt = new Date(d.date);
    return `${dt.getMonth()+1}/${dt.getDate()}`;
  });
  const values = trend.map(d => d.count);

  if (trendLineChart) trendLineChart.destroy();

  trendLineChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        data: values,
        borderColor: 'rgba(184,154,90,0.9)',
        backgroundColor: 'rgba(184,154,90,0.08)',
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointBackgroundColor: 'rgba(184,154,90,1)',
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: 'var(--text-secondary)', maxTicksLimit: 10 }, grid: { display: false } },
        y: { beginAtZero: true, ticks: { precision: 0, color: 'var(--text-secondary)' }, grid: { color: 'var(--border-color)' } },
      },
    },
  });
}
