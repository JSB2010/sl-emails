(() => {
  const defaults = window.__EMAIL_SETTINGS_DEFAULTS__ || {};
  const settings = defaults.settings || {};
  const currentUserEmail = String((defaults.currentUser || {}).email || '').trim().toLowerCase();

  const els = {
    allowedAdmins: document.getElementById('allowed-admins'),
    opsNotifications: document.getElementById('ops-notifications'),
    saveAdmins: document.getElementById('save-admins'),
    saveNotifications: document.getElementById('save-notifications'),
    meta: document.getElementById('settings-meta'),
    flash: document.getElementById('settings-flash'),
  };

  function setFlash(message, isError = false) {
    els.flash.textContent = message;
    els.flash.classList.toggle('error', isError);
  }

  function renderMeta(nextSettings) {
    const updatedAt = nextSettings.updated_at || 'unknown time';
    const updatedBy = nextSettings.updated_by || 'unknown actor';
    els.meta.textContent = `Last updated by ${updatedBy} at ${updatedAt}.`;
  }

  function populate(nextSettings) {
    els.allowedAdmins.value = (nextSettings.allowed_admin_emails || []).join('\n');
    els.opsNotifications.value = (nextSettings.ops_notification_emails || []).join('\n');
    renderMeta(nextSettings);
  }

  function parseEmails(text) {
    return String(text || '')
      .split(/\n+/)
      .map((value) => value.trim().toLowerCase())
      .filter(Boolean);
  }

  async function saveSettings() {
    const allowedAdminEmails = parseEmails(els.allowedAdmins.value);
    const opsNotificationEmails = parseEmails(els.opsNotifications.value);

    if (!allowedAdminEmails.length) {
      setFlash('At least one allowed admin email is required.', true);
      return;
    }
    if (!allowedAdminEmails.includes(currentUserEmail)) {
      setFlash('You cannot remove your own email from the allowlist while signed in.', true);
      return;
    }
    if (!opsNotificationEmails.length) {
      setFlash('At least one notification email is required.', true);
      return;
    }

    els.saveAdmins.disabled = true;
    els.saveNotifications.disabled = true;
    setFlash('Saving settings...');

    try {
      const response = await fetch('/api/emails/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          allowed_admin_emails: allowedAdminEmails,
          ops_notification_emails: opsNotificationEmails,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.ok === false) {
        throw new Error(payload.error || `Request failed (${response.status})`);
      }
      populate(payload.settings || {});
      setFlash('Settings saved.');
    } catch (error) {
      setFlash(error.message || 'Unable to save settings.', true);
    } finally {
      els.saveAdmins.disabled = false;
      els.saveNotifications.disabled = false;
    }
  }

  els.saveAdmins.addEventListener('click', saveSettings);
  els.saveNotifications.addEventListener('click', saveSettings);
  populate(settings);
})();
