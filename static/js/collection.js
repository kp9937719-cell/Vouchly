/**
 * collection.js — Public Testimonial Collection Form
 * =====================================================
 * Runs on /collect/<slug>. Loads space info, renders form, handles submission.
 */

'use strict';

let currentRating = 0;
let spaceData     = null;

async function initCollectionPage() {
  const slug = document.getElementById('spaceSlug')?.value;
  if (!slug) return;

  // Load space info
  const { data, ok } = await fetch(`/api/public/spaces/${slug}`)
    .then(r => r.json())
    .then(d => ({ data: d, ok: d.success }))
    .catch(() => ({ data: null, ok: false }));

  const loadingEl = document.getElementById('collectionLoading');
  const errorEl   = document.getElementById('collectionError');
  const wrapperEl = document.getElementById('collectionWrapper');

  if (!ok || !data?.data) {
    loadingEl.style.display = 'none';
    errorEl.style.display   = 'flex';
    return;
  }

  spaceData = data.data;
  loadingEl.style.display = 'none';
  wrapperEl.style.display  = 'flex';

  // Apply brand color
  document.documentElement.style.setProperty('--gold', spaceData.brand_color || '#B89A5A');

  // Logo
  if (spaceData.logo) {
    const logoEl  = document.getElementById('collectionLogo');
    const logoImg = document.getElementById('collectionLogoImg');
    logoEl.style.display  = 'block';
    logoImg.src           = `/${spaceData.logo}`;
    logoImg.alt           = escapeHtml(spaceData.business_name || spaceData.name);
  }

  // Heading + description
  document.getElementById('collectionHeading').textContent =
    spaceData.welcome_heading || 'Share your experience!';
  document.getElementById('collectionDesc').textContent =
    spaceData.description || '';

  // Star rating toggle
  if (spaceData.enable_star_rating) {
    document.getElementById('ratingGroup').style.display = 'block';
    initStarRating();
  }

  // Avatar required
  const avatarRequired = document.getElementById('avatarRequired');
  if (avatarRequired) {
    avatarRequired.textContent = spaceData.require_avatar ? '*' : '(optional)';
  }

  // Custom questions
  renderCustomQuestions(spaceData.custom_questions || []);

  // Avatar upload preview
  initFileUploadPreview('avatar', 'avatarPreview', 'avatarPreviewImg', 'avatarPlaceholder', 'removeAvatarBtn');

  // Character counter
  const reviewTextArea = document.getElementById('review_text');
  const charCount      = document.getElementById('charCount');
  reviewTextArea?.addEventListener('input', () => {
    if (charCount) charCount.textContent = reviewTextArea.value.length;
  });

  // Form submission
  document.getElementById('testimonialForm')?.addEventListener('submit', handleSubmit);

  // Submit another
  document.getElementById('submitAnotherBtn')?.addEventListener('click', () => {
    document.getElementById('thankYouScreen').style.display = 'none';
    document.getElementById('testimonialForm').style.display = 'block';
    document.getElementById('testimonialForm').reset();
    currentRating = 0;
    resetStars();
    if (charCount) charCount.textContent = '0';
  });
}

function initStarRating() {
  const starBtns = document.querySelectorAll('.star-btn');
  const ratingInput = document.getElementById('rating');

  starBtns.forEach(btn => {
    btn.addEventListener('mouseenter', () => {
      const val = parseInt(btn.dataset.value);
      highlightStars(val);
    });

    btn.addEventListener('mouseleave', () => {
      highlightStars(currentRating);
    });

    btn.addEventListener('click', () => {
      currentRating = parseInt(btn.dataset.value);
      if (ratingInput) ratingInput.value = currentRating;
      highlightStars(currentRating);
      // Clear the error highlight and message
      document.getElementById('starRating')?.classList.remove('rating-error');
      const ratingErr = document.getElementById('ratingError');
      if (ratingErr) ratingErr.textContent = '';
    });
  });
}

function highlightStars(upTo) {
  document.querySelectorAll('.star-btn').forEach(btn => {
    const val = parseInt(btn.dataset.value);
    btn.classList.toggle('selected', val <= upTo);
    btn.classList.toggle('hovered', val <= upTo);
  });
}

function resetStars() {
  document.querySelectorAll('.star-btn').forEach(btn => {
    btn.classList.remove('selected', 'hovered');
  });
  const ratingInput = document.getElementById('rating');
  if (ratingInput) ratingInput.value = '';
}

function renderCustomQuestions(questions) {
  const container = document.getElementById('customQuestionsContainer');
  if (!container || !questions.length) return;

  questions.forEach((q, i) => {
    const div = document.createElement('div');
    div.className = 'form-group custom-question';
    div.innerHTML = `
      <label for="cq_${i}" class="form-label">${escapeHtml(q)}</label>
      <input type="text" id="cq_${i}" name="custom_answer_${i}" class="form-input"
             placeholder="Your answer..." maxlength="500" />
    `;
    container.appendChild(div);
  });
}

async function handleSubmit(e) {
  e.preventDefault();

  // Clear all previous errors
  document.querySelectorAll('.field-error').forEach(el => el.textContent = '');
  document.getElementById('formError').style.display = 'none';
  document.getElementById('formError').textContent = '';

  // Validate
  let valid = true;
  let firstErrorEl = null;

  const name    = document.getElementById('customer_name')?.value.trim();
  const email   = document.getElementById('customer_email')?.value.trim();
  const review  = document.getElementById('review_text')?.value.trim();
  const consent = document.getElementById('consent')?.checked;

  if (!name) {
    const el = document.getElementById('customer_nameError');
    el.textContent = 'Your name is required.';
    if (!firstErrorEl) firstErrorEl = el;
    valid = false;
  }
  if (!email) {
    const el = document.getElementById('customer_emailError');
    el.textContent = 'Email is required.';
    if (!firstErrorEl) firstErrorEl = el;
    valid = false;
  }
  if (!review) {
    const el = document.getElementById('review_textError');
    el.textContent = 'Please write your testimonial.';
    if (!firstErrorEl) firstErrorEl = el;
    valid = false;
  } else if (review.length < 10) {
    const el = document.getElementById('review_textError');
    el.textContent = 'Testimonial must be at least 10 characters.';
    if (!firstErrorEl) firstErrorEl = el;
    valid = false;
  }
  if (!consent) {
    const el = document.getElementById('consentError');
    el.textContent = 'You must consent before submitting.';
    if (!firstErrorEl) firstErrorEl = el;
    valid = false;
  }

  // Clear star rating highlight first
  document.getElementById('starRating')?.classList.remove('rating-error');

  if (spaceData?.enable_star_rating && !currentRating) {
    const el = document.getElementById('ratingError');
    el.textContent = 'Please select a star rating.';
    document.getElementById('starRating')?.classList.add('rating-error');
    if (!firstErrorEl) firstErrorEl = el;
    valid = false;
  }

  if (spaceData?.require_avatar) {
    const avatarFile = document.getElementById('avatar')?.files[0];
    if (!avatarFile) {
      const el = document.getElementById('avatarError');
      el.textContent = 'A photo is required.';
      if (!firstErrorEl) firstErrorEl = el;
      valid = false;
    }
  }

  if (!valid) {
    // Scroll to the first error so the user can see it
    firstErrorEl?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    return;
  }

  // Build FormData for file upload
  const formData = new FormData(document.getElementById('testimonialForm'));

  // Collect custom answers as JSON
  const customAnswers = {};
  document.querySelectorAll('[name^="custom_answer_"]').forEach(el => {
    const idx = el.name.split('_').pop();
    if (el.value.trim()) {
      customAnswers[idx] = el.value.trim();
    }
  });
  if (Object.keys(customAnswers).length) {
    formData.set('custom_answers', JSON.stringify(customAnswers));
  }

  const slug = document.getElementById('spaceSlug')?.value;
  const btn  = document.getElementById('submitBtn');
  setButtonLoading(btn, true);

  const { data, ok } = await apiFetch(`/api/public/${slug}/testimonials`, {
    method: 'POST',
    body: formData,
  });

  setButtonLoading(btn, false);

  if (ok && data?.success) {
    // Show thank you screen
    document.getElementById('testimonialForm').style.display = 'none';
    const tyScreen = document.getElementById('thankYouScreen');
    tyScreen.style.display = 'block';
    document.getElementById('thankYouMessage').textContent =
      spaceData?.thank_you_message || data.message || 'Thank you for your testimonial!';
  } else {
    // Apply per-field errors from backend to the matching field-error spans
    const fieldErrorMap = {
      customer_name:  'customer_nameError',
      customer_email: 'customer_emailError',
      review_text:    'review_textError',
      rating:         'ratingError',
      avatar:         'avatarError',
      consent:        'consentError',
    };

    let firstBackendErrorEl = null;
    if (data?.errors && typeof data.errors === 'object') {
      for (const [field, msg] of Object.entries(data.errors)) {
        const spanId = fieldErrorMap[field];
        if (spanId) {
          const span = document.getElementById(spanId);
          if (span) {
            span.textContent = msg;
            if (!firstBackendErrorEl) firstBackendErrorEl = span;
          }
        }
      }
    }

    // Show the top-level error message
    const errEl = document.getElementById('formError');
    if (errEl) {
      errEl.textContent = data?.message || 'Submission failed. Please try again.';
      errEl.style.display = 'block';
    }

    // Scroll to the first field with a backend error (or the top error banner)
    const scrollTarget = firstBackendErrorEl || errEl;
    scrollTarget?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

