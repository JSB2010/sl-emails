(() => {
  const defaults = window.__EVENT_REQUEST_DEFAULTS__ || {};
  const els = {
    form: document.getElementById('request-form'),
    startDate: document.getElementById('start-date'),
    endDate: document.getElementById('end-date'),
    weekPreviewLabel: document.getElementById('week-preview-label'),
    submitBtn: document.getElementById('submit-request'),
    success: document.getElementById('request-success'),
    successMessage: document.getElementById('request-success-message'),
    submitAnother: document.getElementById('submit-another'),
    error: document.getElementById('request-error'),
  };

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

  function syncWeekPreview() {
    els.weekPreviewLabel.textContent = weekLabel(els.startDate.value || defaults.defaultStartDate || '');
    if (!els.endDate.value) {
      els.endDate.value = els.startDate.value || defaults.defaultStartDate || '';
    }
  }

  function setError(message = '') {
    const hasMessage = Boolean(message);
    els.error.hidden = !hasMessage;
    els.error.textContent = message;
  }

  async function submitForm(event) {
    event.preventDefault();
    setError('');
    els.submitBtn.disabled = true;

    const formData = new FormData(els.form);
    const payload = Object.fromEntries(formData.entries());

    try {
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
      syncWeekPreview();
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
  }

  els.startDate.addEventListener('change', syncWeekPreview);
  els.submitAnother.addEventListener('click', resetForm);
  els.form.addEventListener('submit', submitForm);
  syncWeekPreview();
})();
