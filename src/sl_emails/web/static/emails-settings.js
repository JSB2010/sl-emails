(() => {
  const defaults = window.__EMAIL_SETTINGS_DEFAULTS__ || {};
  const settings = defaults.settings || {};
  const currentUserEmail = String((defaults.currentUser || {}).email || '').trim().toLowerCase();

  const els = {
    allowedAdmins: document.getElementById('allowed-admins'),
    opsNotifications: document.getElementById('ops-notifications'),
    emailFromName: document.getElementById('email-from-name'),
    replyToEmail: document.getElementById('reply-to-email'),
    senderTimezone: document.getElementById('sender-timezone'),
    middleSchoolTo: document.getElementById('middle-school-to'),
    middleSchoolBcc: document.getElementById('middle-school-bcc'),
    upperSchoolTo: document.getElementById('upper-school-to'),
    upperSchoolBcc: document.getElementById('upper-school-bcc'),
    saveSettings: document.getElementById('save-settings'),
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
    const sender = nextSettings.sender_metadata || {};
    const recipients = sender.audience_recipients || {};
    const middleSchool = recipients.middle_school || {};
    const upperSchool = recipients.upper_school || {};

    els.allowedAdmins.value = (nextSettings.allowed_admin_emails || []).join('\n');
    els.opsNotifications.value = (nextSettings.ops_notification_emails || []).join('\n');
    els.emailFromName.value = sender.email_from_name || '';
    els.replyToEmail.value = sender.reply_to_email || '';
    els.senderTimezone.value = sender.timezone || '';
    els.middleSchoolTo.value = middleSchool.to || '';
    els.middleSchoolBcc.value = (middleSchool.bcc || []).join('\n');
    els.upperSchoolTo.value = upperSchool.to || '';
    els.upperSchoolBcc.value = (upperSchool.bcc || []).join('\n');
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
    const middleSchoolTo = String(els.middleSchoolTo.value || '').trim().toLowerCase();
    const upperSchoolTo = String(els.upperSchoolTo.value || '').trim().toLowerCase();

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
    if (!middleSchoolTo) {
      setFlash('A middle-school To recipient is required.', true);
      return;
    }
    if (!upperSchoolTo) {
      setFlash('An upper-school To recipient is required.', true);
      return;
    }

    els.saveSettings.disabled = true;
    els.saveSettings.textContent = 'Saving…';
    setFlash('Saving settings…');

    try {
      const response = await fetch('/api/emails/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          allowed_admin_emails: allowedAdminEmails,
          ops_notification_emails: opsNotificationEmails,
          sender_metadata: {
            email_from_name: String(els.emailFromName.value || '').trim(),
            reply_to_email: String(els.replyToEmail.value || '').trim().toLowerCase(),
            timezone: String(els.senderTimezone.value || '').trim(),
            audience_recipients: {
              middle_school: {
                to: middleSchoolTo,
                bcc: parseEmails(els.middleSchoolBcc.value),
              },
              upper_school: {
                to: upperSchoolTo,
                bcc: parseEmails(els.upperSchoolBcc.value),
              },
            },
          },
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
      els.saveSettings.disabled = false;
      els.saveSettings.textContent = 'Save All Settings';
    }
  }

  els.saveSettings.addEventListener('click', saveSettings);
  populate(settings);
})();
