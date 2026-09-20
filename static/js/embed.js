/**
 * embed.js — Embed Generator Page
 * ==================================
 */

'use strict';

let embedSpaceSlug = '';

async function initEmbedPage() {
  // Load spaces
  const select = document.getElementById('embedSpaceSelect');
  if (!select) return;

  const { data, ok } = await apiFetch('/api/spaces');
  if (!ok || !data?.success) { showToast('Could not load spaces.', 'error'); return; }

  const spaces = data.data.spaces || [];
  select.innerHTML = '<option value="">Select a space...</option>';
  spaces.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.slug;
    opt.textContent = s.name;
    select.appendChild(opt);
  });

  select.addEventListener('change', (e) => {
    embedSpaceSlug = e.target.value;
    document.getElementById('embedOptions').style.display = embedSpaceSlug ? 'block' : 'none';
    if (embedSpaceSlug) {
      generateEmbedCode();
    }
  });

  if (spaces.length > 0) {
    select.value = spaces[0].slug;
    embedSpaceSlug = spaces[0].slug;
    document.getElementById('embedOptions').style.display = 'block';
    generateEmbedCode();
  }

  // Slider label
  document.getElementById('embedCount')?.addEventListener('input', (e) => {
    document.getElementById('countLabel').textContent = e.target.value;
  });

  // Color picker sync
  initColorPickerSync('embedBrandColor', 'embedBrandColorText');

  // Generate button
  document.getElementById('generateEmbedBtn')?.addEventListener('click', generateEmbedCode);

  // Reset
  document.getElementById('resetConfigBtn')?.addEventListener('click', () => {
    document.querySelectorAll('input[name="layout"]').forEach(r => r.checked = r.value === 'grid');
    document.querySelectorAll('input[name="theme"]').forEach(r => r.checked = r.value === 'light');
    document.getElementById('embedCount').value = 6;
    document.getElementById('countLabel').textContent = '6';
    document.getElementById('embedBrandColor').value = '#B89A5A';
    document.getElementById('embedBrandColorText').value = '#B89A5A';
    document.getElementById('showRatings').checked = true;
    document.getElementById('showAvatars').checked  = true;
    document.getElementById('showCompany').checked  = true;
  });

  // Refresh preview
  document.getElementById('refreshPreviewBtn')?.addEventListener('click', generateEmbedCode);

  // Copy buttons
  document.querySelectorAll('.copy-btn[data-target]').forEach(btn => {
    btn.addEventListener('click', () => {
      const codeEl = document.getElementById(btn.dataset.target);
      if (codeEl) copyToClipboard(codeEl.textContent, btn);
    });
  });
}

async function generateEmbedCode() {
  if (!embedSpaceSlug) { showToast('Please select a space first.', 'warning'); return; }

  const config = getCurrentConfig();

  const { data, ok } = await apiFetch('/api/embed/generate', {
    method: 'POST',
    body: JSON.stringify({ slug: embedSpaceSlug, config }),
  });

  if (!ok || !data?.success) {
    showToast(data?.message || 'Could not generate embed code.', 'error');
    return;
  }

  const { iframe, html, widget_url } = data.data;

  // Show code blocks
  document.getElementById('embedCodeSection').style.display = 'block';
  document.getElementById('iframeCode').textContent = iframe;
  document.getElementById('htmlCode').textContent   = html;

  // Show live preview in iframe
  const frame = document.getElementById('previewFrame');
  const placeholder = document.getElementById('previewPlaceholder');
  frame.src = widget_url;
  frame.classList.add('active');
  frame.style.display = 'block';
  if (placeholder) placeholder.style.display = 'none';

  // Save config to server
  const spaceRes = await apiFetch('/api/spaces');
  if (spaceRes.ok && spaceRes.data?.success) {
    const space = spaceRes.data.data.spaces.find(s => s.slug === embedSpaceSlug);
    if (space) {
      await apiFetch(`/api/spaces/${space.id}/widget-config`, {
        method: 'POST',
        body: JSON.stringify(config),
      });
    }
  }
}

function getCurrentConfig() {
  const layout     = document.querySelector('input[name="layout"]:checked')?.value || 'grid';
  const theme      = document.querySelector('input[name="theme"]:checked')?.value  || 'light';
  const count      = parseInt(document.getElementById('embedCount')?.value || '6');
  const brand_color = document.getElementById('embedBrandColor')?.value || '#B89A5A';
  const show_ratings = document.getElementById('showRatings')?.checked ?? true;
  const show_avatars  = document.getElementById('showAvatars')?.checked  ?? true;
  const show_company  = document.getElementById('showCompany')?.checked  ?? true;

  return { layout, theme, count, brand_color, show_ratings, show_avatars, show_company };
}
