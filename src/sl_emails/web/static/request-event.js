(() => {
  const defaults = window.__EVENT_REQUEST_DEFAULTS__ || {};
  const ICON_CDN_BASE = 'https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.5.2/svgs/solid';
  const sportOptions = Array.isArray(defaults.sportOptions) ? defaults.sportOptions : [];
  const eventCategoryOptions = Array.isArray(defaults.eventCategoryOptions) ? defaults.eventCategoryOptions : [];

  const els = {
    form: document.getElementById('request-form'),
    startDate: document.getElementById('start-date'),
    endDate: document.getElementById('end-date'),
    singleDay: document.getElementById('single-day'),
    timeMode: document.getElementById('time-mode'),
    timeValue: document.getElementById('time-value'),
    timeValueWrap: document.getElementById('time-value-wrap'),
    weekPreviewLabel: document.getElementById('week-preview-label'),
    submitBtn: document.getElementById('submit-request'),
    success: document.getElementById('request-success'),
    successMessage: document.getElementById('request-success-message'),
    submitAnother: document.getElementById('submit-another'),
    error: document.getElementById('request-error'),
    titleLabel: document.getElementById('title-label'),
    titleInput: document.getElementById('title-input'),
    previewKind: document.getElementById('preview-kind'),
    previewAudience: document.getElementById('preview-audience'),
    previewIcon: document.getElementById('preview-icon'),
    previewTitle: document.getElementById('preview-title'),
    previewSubtitle: document.getElementById('preview-subtitle'),
    previewWhen: document.getElementById('preview-when'),
    previewLocation: document.getElementById('preview-location'),
    previewLink: document.getElementById('preview-link'),
    previewRequester: document.getElementById('preview-requester'),
    previewDescription: document.getElementById('preview-description'),
    kindPanels: Array.from(document.querySelectorAll('[data-kind-panel]')),
  };

  function selectedValue(name) {
    const checked = els.form.querySelector(`[name="${name}"]:checked`);
    return checked ? String(checked.value || '').trim() : '';
  }

  function optionFor(list, value) {
    return list.find((item) => String(item.value || '').trim() === value) || null;
  }

  function currentKind() {
    return selectedValue('kind') || 'event';
  }

  function currentCategory() {
    return currentKind() === 'game'
      ? selectedValue('sport_category') || 'Athletics'
      : selectedValue('event_category') || 'School Event';
  }

  function currentCategoryOption() {
    return currentKind() === 'game'
      ? optionFor(sportOptions, currentCategory())
      : optionFor(eventCategoryOptions, currentCategory());
  }

  function currentAudienceLabel() {
    const value = selectedValue('audience') || 'both';
    if (value === 'middle-school') return 'Middle School';
    if (value === 'upper-school') return 'Upper School';
    return 'Both Audiences';
  }

  function mondayFor(dateString) {
    const value = new Date(`${dateString}T00:00:00`);
    if (Number.isNaN(value.getTime())) return null;
    const monday = new Date(value);
    monday.setDate(value.getDate() - ((value.getDay() + 6) % 7));
    return monday;
  }

  function weekLabel(dateString) {
    const monday = mondayFor(dateString);
    if (!monday) return 'Review week will be assigned from the event start date.';

    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    const startMonth = monday.toLocaleDateString('en-US', { month: 'long' });
    const endMonth = sunday.toLocaleDateString('en-US', { month: 'long' });
    const startDay = monday.getDate();
    const endDay = sunday.getDate();
    const year = sunday.getFullYear();
    const range = startMonth === endMonth
      ? `${startMonth} ${startDay}-${endDay}, ${year}`
      : `${startMonth} ${startDay}-${endMonth} ${endDay}, ${year}`;
    return `This request will route to the review week of ${range}.`;
  }

  function formatDate(dateString) {
    const value = new Date(`${dateString}T00:00:00`);
    if (Number.isNaN(value.getTime())) return '';
    return value.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  }

  function formatTime(timeValue) {
    const [hoursText, minutesText] = String(timeValue || '').split(':');
    const hours = Number(hoursText);
    const minutes = Number(minutesText);
    if (!Number.isFinite(hours) || !Number.isFinite(minutes)) return '';
    const suffix = hours >= 12 ? 'PM' : 'AM';
    const normalizedHour = hours % 12 || 12;
    return `${normalizedHour}:${String(minutes).padStart(2, '0')} ${suffix}`;
  }

  function computedTimeText() {
    if (els.timeMode.value === 'all-day') return 'All Day';
    if (els.timeMode.value === 'tbd') return 'TBA';
    return formatTime(els.timeValue.value);
  }

  function currentSubtitle() {
    if (currentKind() !== 'game') return currentCategory();
    const opponent = String(els.form.elements.opponent_name?.value || '').trim();
    if (!opponent) return 'Opponent TBD';
    return `${selectedValue('home_away') === 'away' ? '@' : 'vs.'} ${opponent}`;
  }

  function syncWeekPreview() {
    els.weekPreviewLabel.textContent = weekLabel(els.startDate.value || defaults.defaultStartDate || '');
  }

  function syncDateFields() {
    if (els.singleDay.checked) {
      els.endDate.value = els.startDate.value || defaults.defaultStartDate || '';
      els.endDate.disabled = true;
    } else {
      els.endDate.disabled = false;
      if (!els.endDate.value) {
        els.endDate.value = els.startDate.value || defaults.defaultStartDate || '';
      }
    }
  }

  function syncTimeControls() {
    const scheduled = els.timeMode.value === 'scheduled';
    els.timeValueWrap.hidden = !scheduled;
    els.timeValue.disabled = !scheduled;
  }

  function syncKindPanels() {
    const kind = currentKind();
    els.kindPanels.forEach((panel) => {
      panel.hidden = panel.dataset.kindPanel !== kind;
    });
    els.titleLabel.textContent = kind === 'game' ? 'Team Name' : 'Event Title';
    els.titleInput.placeholder = kind === 'game' ? 'Varsity Baseball' : 'Community Night';
  }

  function previewIconMarkup() {
    const option = currentCategoryOption();
    if (option && option.icon) {
      return `<img src="${ICON_CDN_BASE}/${option.icon}.svg" alt="" aria-hidden="true" />`;
    }
    return '<span>Auto</span>';
  }

  function updatePreview() {
    const kind = currentKind();
    const title = String(els.titleInput.value || '').trim() || (kind === 'game' ? 'Team Name' : 'Event Title');
    const whenDate = formatDate(els.startDate.value);
    const endDate = els.endDate.value && els.endDate.value !== els.startDate.value ? formatDate(els.endDate.value) : '';
    const timeText = computedTimeText();
    const location = String(els.form.elements.location?.value || '').trim() || 'On Campus';
    const link = String(els.form.elements.link?.value || '').trim();
    const requesterName = String(els.form.elements.requester_name?.value || '').trim();
    const requesterEmail = String(els.form.elements.requester_email?.value || '').trim();
    const description = String(els.form.elements.description?.value || '').trim();

    els.previewKind.textContent = kind === 'game' ? 'Athletic Game' : 'School Event';
    els.previewAudience.textContent = currentAudienceLabel();
    els.previewIcon.innerHTML = previewIconMarkup();
    els.previewTitle.textContent = title;
    els.previewSubtitle.textContent = currentSubtitle();

    const dateText = endDate ? `${whenDate} to ${endDate}` : whenDate || 'Select a date';
    els.previewWhen.textContent = [dateText, timeText].filter(Boolean).join(' · ') || 'Select a date';
    els.previewLocation.textContent = location;
    els.previewLink.textContent = link || 'Optional';
    els.previewRequester.textContent = [requesterName, requesterEmail].filter(Boolean).join(' · ') || 'Add your contact info';
    els.previewDescription.textContent = description || 'Any description you provide will appear here for the reviewer before approval.';
  }

  function setError(message = '') {
    const hasMessage = Boolean(message);
    els.error.hidden = !hasMessage;
    els.error.textContent = message;
  }

  function buildPayload() {
    const formData = new FormData(els.form);
    const payload = Object.fromEntries(formData.entries());
    const kind = currentKind();
    const title = String(payload.title || '').trim();
    const category = currentCategory();
    const opponent = String(payload.opponent_name || '').trim();
    const timeText = computedTimeText();

    if (!title) throw new Error(kind === 'game' ? 'Team name is required.' : 'Event title is required.');
    if (!payload.start_date) throw new Error('Start date is required.');
    if (!payload.end_date) throw new Error('End date is required.');
    if (!category) throw new Error(kind === 'game' ? 'Choose a sport.' : 'Choose an event category.');
    if (kind === 'game' && !opponent) throw new Error('Opponent is required for a game request.');
    if (els.timeMode.value === 'scheduled' && !timeText) throw new Error('Choose a start time or mark the event as All Day / Time TBD.');

    payload.kind = kind;
    payload.category = category;
    payload.time_text = timeText || 'TBA';
    payload.end_date = String(payload.end_date || payload.start_date);
    payload.location = String(payload.location || '').trim() || 'On Campus';
    payload.title = title;
    payload.team = title;
    payload.subtitle = kind === 'game' ? `${selectedValue('home_away') === 'away' ? '@' : 'vs.'} ${opponent}` : category;
    payload.opponent = kind === 'game' ? opponent : '';
    payload.is_home = kind !== 'game' || selectedValue('home_away') !== 'away';
    return payload;
  }

  async function submitForm(event) {
    event.preventDefault();
    setError('');
    els.submitBtn.disabled = true;

    try {
      const payload = buildPayload();
      const response = await fetch('/api/emails/requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok || !data || data.ok === false) {
        throw new Error((data && data.error) || 'Unable to submit the request right now.');
      }

      els.form.hidden = true;
      els.success.hidden = false;
      els.successMessage.textContent = `Your request for ${data.week_label || 'the selected review week'} has been submitted and is now waiting for admin review.`;
      els.form.reset();
      els.startDate.value = defaults.defaultStartDate || '';
      els.endDate.value = defaults.defaultStartDate || '';
      els.singleDay.checked = true;
      els.timeMode.value = 'scheduled';
      els.timeValue.value = '18:00';
      syncAll();
    } catch (error) {
      setError(error.message || 'Unable to submit the request right now.');
    } finally {
      els.submitBtn.disabled = false;
    }
  }

  function resetForm() {
    els.success.hidden = true;
    els.form.hidden = false;
    setError('');
    syncAll();
  }

  function syncAll() {
    syncKindPanels();
    syncDateFields();
    syncTimeControls();
    syncWeekPreview();
    updatePreview();
  }

  els.form.addEventListener('change', syncAll);
  els.form.addEventListener('input', updatePreview);
  els.startDate.addEventListener('change', syncAll);
  els.singleDay.addEventListener('change', syncAll);
  els.timeMode.addEventListener('change', syncAll);
  els.submitAnother.addEventListener('click', resetForm);
  els.form.addEventListener('submit', submitForm);

  syncAll();
})();
