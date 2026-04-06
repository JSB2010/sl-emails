/**
 * Kent Denver Sports Email Automation
 *
 * Google Apps Script owns the sports email cron flow:
 * 0. Daily at midnight MT: refresh the public signage snapshot in the web app.
 * 1. Sunday 8:00 AM MT: create or confirm the weekly draft in the web app.
 * 2. Email the admin/ops list a review link to /emails?week=<YYYY-MM-DD>.
 * 3. Daily 4:00 PM MT: dispatch only the approved payloads scheduled for that day.
 *
 * Required Script Properties:
 * - API_BASE_URL
 * - AUTOMATION_API_KEY
 * - ADMIN_NOTIFICATION_EMAILS
 * - MIDDLE_SCHOOL_TO
 * - MIDDLE_SCHOOL_BCC
 * - UPPER_SCHOOL_TO
 * - UPPER_SCHOOL_BCC
 *
 * Optional Script Properties:
 * - EMAIL_FROM_NAME
 * - API_ACTOR
 * - REPLY_TO_EMAIL
 * - TIMEZONE
 */

const CONFIG = {
  API_ACTOR: 'google-apps-script',
  EMAIL_FROM_NAME: 'Student Leadership',
  REPLY_TO_EMAIL: 'studentleader@kentdenver.org',
  TIMEZONE: 'America/Denver'
};

const MANAGED_TRIGGER_FUNCTIONS = ['refreshDailySignage', 'runSundayDraftCycle', 'sendSportsEmails'];

function getScriptProperties() {
  return PropertiesService.getScriptProperties();
}

function getRawProperty(name) {
  return String(getScriptProperties().getProperty(name) || '').trim();
}

function getRequiredProperty(name) {
  const value = getRawProperty(name);
  if (!value) {
    throw new Error(`Missing required Script Property: ${name}`);
  }
  return value;
}

function parseEmailList(value) {
  return String(value || '')
    .split(/[,\n;]/)
    .map(item => item.trim())
    .filter(Boolean);
}

function getEffectiveConfig() {
  const apiBaseUrl = getRequiredProperty('API_BASE_URL').replace(/\/+$/, '');
  const automationApiKey = getRequiredProperty('AUTOMATION_API_KEY');
  const adminNotificationEmails = parseEmailList(getRequiredProperty('ADMIN_NOTIFICATION_EMAILS'));
  const middleSchoolTo = getRequiredProperty('MIDDLE_SCHOOL_TO');
  const upperSchoolTo = getRequiredProperty('UPPER_SCHOOL_TO');
  const middleSchoolBcc = parseEmailList(getRequiredProperty('MIDDLE_SCHOOL_BCC'));
  const upperSchoolBcc = parseEmailList(getRequiredProperty('UPPER_SCHOOL_BCC'));

  if (!adminNotificationEmails.length) {
    throw new Error('ADMIN_NOTIFICATION_EMAILS must contain at least one email address');
  }

  return {
    API_BASE_URL: apiBaseUrl,
    API_ACTOR: getRawProperty('API_ACTOR') || CONFIG.API_ACTOR,
    AUTOMATION_API_KEY: automationApiKey,
    ADMIN_NOTIFICATION_EMAILS: adminNotificationEmails,
    EMAIL_FROM_NAME: getRawProperty('EMAIL_FROM_NAME') || CONFIG.EMAIL_FROM_NAME,
    REPLY_TO_EMAIL: getRawProperty('REPLY_TO_EMAIL') || CONFIG.REPLY_TO_EMAIL,
    TIMEZONE: getRawProperty('TIMEZONE') || CONFIG.TIMEZONE,
    EMAIL_RECIPIENTS: {
      MIDDLE_SCHOOL: {
        to: middleSchoolTo,
        bcc: middleSchoolBcc
      },
      UPPER_SCHOOL: {
        to: upperSchoolTo,
        bcc: upperSchoolBcc
      }
    }
  };
}

function validateConfiguration(options) {
  let config;
  try {
    config = getEffectiveConfig();
  } catch (error) {
    const missingMatch = String(error && error.message || '').match(/Missing required Script Property: (.+)$/);
    return {
      ok: false,
      missing: missingMatch ? [missingMatch[1]] : ['unknown'],
      config: {
        API_BASE_URL: getRawProperty('API_BASE_URL'),
        ADMIN_NOTIFICATION_EMAILS: parseEmailList(getRawProperty('ADMIN_NOTIFICATION_EMAILS')),
        EMAIL_RECIPIENTS: {
          MIDDLE_SCHOOL: { to: getRawProperty('MIDDLE_SCHOOL_TO'), bcc: parseEmailList(getRawProperty('MIDDLE_SCHOOL_BCC')) },
          UPPER_SCHOOL: { to: getRawProperty('UPPER_SCHOOL_TO'), bcc: parseEmailList(getRawProperty('UPPER_SCHOOL_BCC')) }
        }
      }
    };
  }
  const missing = [];

  if (!config.API_BASE_URL) missing.push('API_BASE_URL');
  if (!config.AUTOMATION_API_KEY) missing.push('AUTOMATION_API_KEY');
  if (!config.ADMIN_NOTIFICATION_EMAILS.length) missing.push('ADMIN_NOTIFICATION_EMAILS');
  if (!(options && options.skipRecipients)) {
    if (!config.EMAIL_RECIPIENTS.MIDDLE_SCHOOL.to) missing.push('MIDDLE_SCHOOL_TO');
    if (!config.EMAIL_RECIPIENTS.UPPER_SCHOOL.to) missing.push('UPPER_SCHOOL_TO');
  }

  return {
    ok: missing.length === 0,
    missing,
    config
  };
}

function assertConfigured(options) {
  const result = validateConfiguration(options);
  if (!result.ok) {
    throw new Error(`Missing required Script Properties: ${result.missing.join(', ')}`);
  }
  return result.config;
}

function runSundayDraftCycle() {
  const config = assertConfigured({ skipRecipients: true });
  const weekId = getCurrentWeekId();

  try {
    console.log(`📥 Starting Sunday draft cycle for ${weekId}...`);
    const ingestResult = triggerScheduledIngest(weekId, config);
    if (shouldSuppressReviewNotification(ingestResult)) {
      const message = `Suppressed review notification for ${weekId} because the week is marked “No email this week”.`;
      reportAutomationActivity(
        weekId,
        'review_notification',
        'suppressed',
        message,
        { reason: 'week_marked_skip', delivery: ingestResult.week.delivery }
      );
      logEmailActivity('SKIP', message);
      return;
    }
    sendAdminReviewNotification(weekId, ingestResult, config);
    reportAutomationActivity(
      weekId,
      'review_notification',
      'success',
      `Sent review notification for ${weekId}`,
      { recipients: config.ADMIN_NOTIFICATION_EMAILS, ingest_action: ingestResult.action }
    );
    logEmailActivity('DRAFT', `Weekly draft cycle ${ingestResult.action} for ${weekId}`);
  } catch (error) {
    console.error('❌ Error in runSundayDraftCycle:', error);
    try {
      sendErrorNotification(`Error running Sunday draft cycle for ${weekId}: ${error.message}`, config);
      reportAutomationActivity(
        weekId,
        'review_notification',
        'failed',
        `Sunday draft cycle failed for ${weekId}: ${error.message}`
      );
    } catch (notificationError) {
      console.error('❌ Error while notifying ops about Sunday draft cycle failure:', notificationError);
    }
    logEmailActivity('ERROR', `Draft cycle failed for ${weekId}: ${error.message}`);
  }
}

function runSundayDraftCycleManual() {
  runSundayDraftCycle();
}

function refreshDailySignage() {
  const config = assertConfigured({ skipRecipients: true });
  const dayId = getCurrentSignageDayId();

  try {
    console.log(`🖥️ Refreshing signage snapshot for ${dayId}...`);
    const refreshResult = triggerSignageRefresh(dayId, config);
    console.log(`✅ Signage refresh ${refreshResult.action || 'completed'} for ${dayId}`);
    logEmailActivity('SIGNAGE', `Daily signage refresh ${refreshResult.action || 'completed'} for ${dayId}`);
  } catch (error) {
    console.error('❌ Error in refreshDailySignage:', error);
    sendErrorNotification(`Error refreshing digital signage for ${dayId}: ${error.message}`, config);
    logEmailActivity('ERROR', `Daily signage refresh failed for ${dayId}: ${error.message}`);
  }
}

function refreshDailySignageManual() {
  refreshDailySignage();
}

function sendSportsEmails() {
  const config = assertConfigured();
  let weekId = 'unknown';
  let sendClaimed = false;

  try {
    const dispatch = resolveSendDispatch(config);
    if (!dispatch.shouldAttempt) {
      console.log(`⏭️ No scheduled send window today (${dispatch.todayIso || 'unknown day'}).`);
      logEmailActivity('SKIP', `No scheduled send window today (${dispatch.dayType})`);
      return;
    }
    weekId = dispatch.weekId;

    console.log('🏈 Starting automated sports email sending...');
    console.log(`📅 Evaluating scheduled delivery for week: ${weekId}`);

    const payload = fetchApprovedEmailPayloads(weekId, config);
    const readiness = evaluatePayloadForDispatch(payload, dispatch);
    if (!readiness.shouldSend) {
      console.log(`⏭️ ${readiness.message}`);
      reportAutomationActivity(weekId, 'send', 'skipped', readiness.message, { delivery: payload.delivery || {}, approved: !!payload.approved });
      logEmailActivity('SKIP', readiness.message);
      return;
    }

    if (!ensureWeekCanSend(payload.sent, weekId)) {
      reportAutomationActivity(weekId, 'send', 'skipped', `Week ${weekId} already marked sent; no delivery attempted.`);
      return;
    }

    const emails = normalizeApprovedOutputs(payload, weekId);
    const sendClaim = claimWeekSend(weekId, config);

    if (sendClaim && sendClaim.sent) {
      console.warn(`⚠️ Week ${weekId} was marked sent before this run could claim it.`);
      logEmailActivity('SKIP', `Week ${weekId} already marked sent before send claim`);
      return;
    }
    if (!sendClaim || !sendClaim.sending) {
      throw new Error(`Failed to claim week ${weekId} for sending before email delivery`);
    }

    sendClaimed = true;

    let sentCount = 0;
    const totalEmails = 2;

    if (!sendEmail(config.EMAIL_RECIPIENTS.MIDDLE_SCHOOL, emails.middleSchool.subject, emails.middleSchool.html, config)) {
      throw new Error(`Failed to send middle-school email for ${weekId}`);
    }
    sentCount++;

    if (!sendEmail(config.EMAIL_RECIPIENTS.UPPER_SCHOOL, emails.upperSchool.subject, emails.upperSchool.html, config)) {
      throw new Error(`Failed to send upper-school email for ${weekId}`);
    }
    sentCount++;

    if (sentCount !== totalEmails) {
      throw new Error(`Expected to send ${totalEmails} emails but only sent ${sentCount}`);
    }

    const sentState = markWeekSent(weekId, config);

    console.log(`✅ Successfully sent ${sentCount} approved sports emails for week ${weekId}!`);
    console.log(`📝 Backend sent-state recorded: ${JSON.stringify(sentState)}`);
    reportAutomationActivity(weekId, 'send', 'success', `Delivered ${sentCount} audience emails for ${weekId}`);
    logEmailActivity('SUCCESS', `Sent ${sentCount} emails for week ${weekId}`);
  } catch (error) {
    console.error('❌ Error in sendSportsEmails:', error);
    const errorMessage = sendClaimed
      ? `Error sending sports emails: ${error.message}\n\nWeek ${weekId} remains claimed as sending to prevent duplicate reruns. Verify whether any audience emails were delivered before resolving the backend sent-state.`
      : `Error sending sports emails: ${error.message}`;
    sendErrorNotification(errorMessage, config);
    reportAutomationActivity(weekId, 'send', 'failed', errorMessage);
    logEmailActivity('ERROR', errorMessage);
  }
}

function sendSportsEmailsManual() {
  sendSportsEmails();
}

function getTargetMondayDate() {
  const timezone = getEffectiveConfig().TIMEZONE;
  const today = getTodayInTimezone(timezone);
  const isoWeekday = getIsoWeekdayInTimezone(today, timezone);

  let daysUntilMonday;
  if (isoWeekday === 7) {
    daysUntilMonday = 1;
  } else if (isoWeekday === 1) {
    daysUntilMonday = 0;
  } else {
    daysUntilMonday = 8 - isoWeekday;
  }

  return addDaysUtc(today, daysUntilMonday);
}

function getCurrentMondayDate() {
  const timezone = getEffectiveConfig().TIMEZONE;
  const today = getTodayInTimezone(timezone);
  const isoWeekday = getIsoWeekdayInTimezone(today, timezone);
  const daysSinceMonday = isoWeekday === 7 ? 6 : isoWeekday - 1;
  return addDaysUtc(today, -daysSinceMonday);
}

function getTodayInTimezone(timezone) {
  const todayIso = Utilities.formatDate(new Date(), timezone, 'yyyy-MM-dd');
  return utcDateFromIso(todayIso);
}

function getIsoWeekdayInTimezone(date, timezone) {
  return Number(Utilities.formatDate(date, timezone, 'u'));
}

function utcDateFromIso(isoDate) {
  const parts = String(isoDate || '').split('-').map(part => Number(part));
  return new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
}

function addDaysUtc(date, days) {
  const next = new Date(date.getTime());
  next.setUTCDate(next.getUTCDate() + Number(days || 0));
  return next;
}

function getCurrentWeekId() {
  return Utilities.formatDate(getTargetMondayDate(), getEffectiveConfig().TIMEZONE, 'yyyy-MM-dd');
}

function getCurrentWeekFolder() {
  return Utilities.formatDate(getTargetMondayDate(), getEffectiveConfig().TIMEZONE, 'MMMdd').toLowerCase();
}

function getCurrentMondayWeekId() {
  return Utilities.formatDate(getCurrentMondayDate(), getEffectiveConfig().TIMEZONE, 'yyyy-MM-dd');
}

function getSundayBeforeWeekId(weekId) {
  return Utilities.formatDate(addDaysUtc(utcDateFromIso(weekId), -1), getEffectiveConfig().TIMEZONE, 'yyyy-MM-dd');
}

function normalizeDelivery(delivery, weekId) {
  const source = delivery && typeof delivery === 'object' ? delivery : {};
  const mode = String(source.mode || 'default').trim().toLowerCase();
  const normalizedMode = ['default', 'postpone', 'skip'].indexOf(mode) >= 0 ? mode : 'default';
  return {
    mode: normalizedMode,
    send_on: normalizedMode === 'skip'
      ? ''
      : String(source.send_on || (normalizedMode === 'default' ? getSundayBeforeWeekId(weekId) : weekId)).trim(),
    send_time: String(source.send_time || '16:00').trim() || '16:00',
  };
}

function resolveSendDispatch(config) {
  const today = getTodayInTimezone(config.TIMEZONE);
  const isoWeekday = getIsoWeekdayInTimezone(today, config.TIMEZONE);
  const todayIso = Utilities.formatDate(today, config.TIMEZONE, 'yyyy-MM-dd');

  if (isoWeekday === 7) {
    return {
      shouldAttempt: true,
      dayType: 'sunday',
      todayIso,
      weekId: getCurrentWeekId(),
      requiredMode: 'default',
    };
  }

  if (isoWeekday >= 1 && isoWeekday <= 4) {
    return {
      shouldAttempt: true,
      dayType: 'weekday',
      todayIso,
      weekId: getCurrentMondayWeekId(),
      requiredMode: 'postpone',
    };
  }

  return {
    shouldAttempt: false,
    dayType: 'off',
    todayIso,
    weekId: '',
    requiredMode: '',
  };
}

function evaluatePayloadForDispatch(payload, dispatch) {
  const delivery = normalizeDelivery(payload && payload.delivery, dispatch.weekId);

  if (delivery.mode === 'skip') {
    return { shouldSend: false, message: `Week ${dispatch.weekId} is marked “No email this week”; skipping delivery.` };
  }

  if (dispatch.requiredMode === 'default') {
    if (delivery.mode !== 'default') {
      return { shouldSend: false, message: `Week ${dispatch.weekId} is postponed; Sunday dispatcher is skipping it.` };
    }
    if (delivery.send_on && delivery.send_on !== dispatch.todayIso) {
      return { shouldSend: false, message: `Week ${dispatch.weekId} default send is scheduled for ${delivery.send_on}; not sending today.` };
    }
  }

  if (dispatch.requiredMode === 'postpone') {
    if (delivery.mode !== 'postpone') {
      return { shouldSend: false, message: `Week ${dispatch.weekId} is not scheduled for a weekday postponed send.` };
    }
    if (delivery.send_on !== dispatch.todayIso) {
      return { shouldSend: false, message: `Week ${dispatch.weekId} postponed send is scheduled for ${delivery.send_on}; not sending today.` };
    }
  }

  if (!payload || payload.approved !== true) {
    return { shouldSend: false, message: `Week ${dispatch.weekId} is not approved for sending yet.` };
  }

  return { shouldSend: true, message: `Week ${dispatch.weekId} is scheduled to send now.` };
}

function shouldSuppressReviewNotification(ingestResult) {
  return Boolean(
    ingestResult
    && ingestResult.action === 'skipped'
    && ingestResult.week
    && ingestResult.week.delivery
    && String(ingestResult.week.delivery.mode || '').trim().toLowerCase() === 'skip'
  );
}

function getCurrentSignageDayId() {
  return Utilities.formatDate(new Date(), getEffectiveConfig().TIMEZONE, 'yyyy-MM-dd');
}

function fetchApprovedEmailPayloads(weekId, config) {
  const url = `${config.API_BASE_URL}/api/emails/weeks/${encodeURIComponent(weekId)}/sender-output`;
  console.log(`📥 Fetching approved sender payloads from: ${url}`);
  return fetchJson(url, { method: 'GET' }, config);
}

function triggerScheduledIngest(weekId, config) {
  const url = `${config.API_BASE_URL}/api/emails/automation/weeks/${encodeURIComponent(weekId)}/scheduled-ingest`;
  console.log(`📥 Triggering scheduled ingest at: ${url}`);
  return fetchJson(url, { method: 'POST' }, config);
}

function triggerSignageRefresh(dayId, config) {
  const url = `${config.API_BASE_URL}/api/signage/automation/days/${encodeURIComponent(dayId)}/refresh`;
  console.log(`📥 Triggering signage refresh at: ${url}`);
  return fetchJson(url, { method: 'POST' }, config);
}

function reportAutomationActivity(weekId, eventType, status, message, details) {
  try {
    const config = assertConfigured({ skipRecipients: true });
    const url = `${config.API_BASE_URL}/api/emails/automation/weeks/${encodeURIComponent(weekId)}/activity`;
    fetchJson(url, {
      method: 'POST',
      payload: JSON.stringify({
        event_type: eventType,
        status,
        message,
        details: details || {}
      })
    }, config);
  } catch (error) {
    console.error(`Failed to record automation activity (${eventType}/${status}) for ${weekId}:`, error);
  }
}

function normalizeApprovedOutputs(payload, weekId) {
  if (!payload || payload.ok !== true || payload.approved !== true) {
    throw new Error(`Week ${weekId} is not approved for sending`);
  }

  const outputs = payload.outputs || {};
  const middleSchool = outputs['middle-school'];
  const upperSchool = outputs['upper-school'];

  if (!middleSchool || !middleSchool.subject || !middleSchool.html) {
    throw new Error(`Approved middle-school payload is missing for week ${weekId}`);
  }
  if (!upperSchool || !upperSchool.subject || !upperSchool.html) {
    throw new Error(`Approved upper-school payload is missing for week ${weekId}`);
  }

  return {
    middleSchool,
    upperSchool
  };
}

function ensureWeekCanSend(sentState, weekId) {
  if (sentState && sentState.sent) {
    console.warn(`⚠️ Week ${weekId} is already marked as sent by ${sentState.sent_by || 'unknown actor'} at ${sentState.sent_at || 'unknown time'}.`);
    logEmailActivity('SKIP', `Week ${weekId} already marked sent`);
    return false;
  }

  if (sentState && sentState.sending) {
    throw new Error(
      `Week ${weekId} is already claimed for sending by ${sentState.sending_by || 'unknown actor'} at ${sentState.sending_at || 'unknown time'}. ` +
      'Do not retry until the prior attempt is verified, or duplicate emails may be sent.'
    );
  }

  return true;
}

function fetchJson(url, options, config) {
  const requestOptions = Object.assign(
    {
      muteHttpExceptions: true,
      contentType: 'application/json; charset=UTF-8',
      headers: buildApiHeaders(config)
    },
    options || {}
  );

  const response = UrlFetchApp.fetch(url, requestOptions);
  const status = response.getResponseCode();
  const rawText = response.getContentText('UTF-8');

  let payload;
  try {
    payload = rawText ? JSON.parse(rawText) : {};
  } catch (error) {
    throw new Error(`API returned non-JSON response (${status})`);
  }

  if (status >= 200 && status < 300) {
    return payload;
  }

  const message = payload && payload.error ? payload.error : `API request failed with status ${status}`;
  throw new Error(message);
}

function buildApiHeaders(config) {
  return {
    'User-Agent': 'Kent Denver Sports Email Bot',
    'X-Email-Actor': config.API_ACTOR,
    'X-Automation-Key': config.AUTOMATION_API_KEY
  };
}

function getApiBaseUrl() {
  return assertConfigured({ skipRecipients: true }).API_BASE_URL;
}

function getReviewUrl(weekId) {
  return `${getApiBaseUrl()}/emails?week=${encodeURIComponent(weekId)}`;
}

function claimWeekSend(weekId, config) {
  return updateWeekSendState(weekId, 'sending', config);
}

function markWeekSent(weekId, config) {
  return updateWeekSendState(weekId, 'sent', config);
}

function updateWeekSendState(weekId, state, config) {
  const url = `${config.API_BASE_URL}/api/emails/weeks/${encodeURIComponent(weekId)}/sent`;
  const payload = fetchJson(url, {
    method: 'POST',
    payload: JSON.stringify({ week_id: weekId, state })
  }, config);
  return payload.sent || (payload.week && payload.week.sent) || null;
}

function sendEmail(recipientConfig, subject, htmlContent, config) {
  try {
    console.log(`📧 Sending email to: ${recipientConfig.to}`);
    if (recipientConfig.bcc && recipientConfig.bcc.length > 0) {
      console.log(`📧 BCC: ${recipientConfig.bcc.join(', ')}`);
    }

    const emailOptions = {
      to: recipientConfig.to,
      subject: subject,
      htmlBody: htmlContent,
      name: config.EMAIL_FROM_NAME,
      replyTo: config.REPLY_TO_EMAIL,
      charset: 'UTF-8',
      noReply: false
    };

    if (recipientConfig.bcc && recipientConfig.bcc.length > 0) {
      emailOptions.bcc = recipientConfig.bcc.join(',');
    }

    MailApp.sendEmail(emailOptions);

    console.log('✅ Email sent successfully');
    return true;
  } catch (error) {
    console.error('❌ Error sending email:', error);
    return false;
  }
}

function sendAdminReviewNotification(weekId, ingestResult, config) {
  const reviewUrl = getReviewUrl(weekId);
  const sourceSummary = ingestResult && ingestResult.source_summary ? ingestResult.source_summary : {};
  const totalEvents = Number(sourceSummary.total_events || 0);
  const athleticsEvents = Number(sourceSummary.athletics_events || 0);
  const artsEvents = Number(sourceSummary.arts_events || 0);
  const created = ingestResult && ingestResult.action === 'created';
  const subject = created
    ? `Review sports email draft for ${weekId}`
    : `Review existing sports email draft for ${weekId}`;
  const statusLine = created
    ? `A new weekly draft is ready for review with ${totalEvents} imported events.`
    : 'A weekly draft already existed for this week, so the backend left it unchanged.';
  const countsLine = created
    ? `Imported events: ${athleticsEvents} athletics, ${artsEvents} arts, ${totalEvents} total.`
    : 'Existing draft preserved. Open the review link to continue editing and approval.';

  MailApp.sendEmail({
    to: config.ADMIN_NOTIFICATION_EMAILS.join(','),
    subject,
    body:
      `${statusLine}\n\n` +
      `${countsLine}\n\n` +
      `Review and approve here:\n${reviewUrl}\n`,
    htmlBody:
      `<p>${statusLine}</p>` +
      `<p>${countsLine}</p>` +
      `<p><a href="${reviewUrl}">Open weekly review</a></p>`,
    name: config.EMAIL_FROM_NAME,
    replyTo: config.REPLY_TO_EMAIL,
    charset: 'UTF-8'
  });
}

function sendErrorNotification(errorMessage, config) {
  try {
    MailApp.sendEmail({
      to: config.ADMIN_NOTIFICATION_EMAILS.join(','),
      subject: 'Sports Email Automation Error',
      body: `The sports email automation encountered an error:\n\n${errorMessage}\n\nTime: ${new Date()}\n\nPlease check the logs and fix the issue.`,
      name: config.EMAIL_FROM_NAME,
      replyTo: config.REPLY_TO_EMAIL,
      charset: 'UTF-8'
    });
  } catch (error) {
    console.error('Failed to send error notification:', error);
  }
}

function logEmailActivity(status, message) {
  try {
    console.log(`📝 Log: ${status} - ${message}`);
  } catch (error) {
    console.error('Failed to log activity:', error);
  }
}

function setupTriggers() {
  assertConfigured();
  removeTriggers();

  ScriptApp.newTrigger('refreshDailySignage')
    .timeBased()
    .everyDays(1)
    .atHour(0)
    .create();

  ScriptApp.newTrigger('runSundayDraftCycle')
    .timeBased()
    .everyWeeks(1)
    .onWeekDay(ScriptApp.WeekDay.SUNDAY)
    .atHour(8)
    .create();

  ScriptApp.newTrigger('sendSportsEmails')
    .timeBased()
    .everyDays(1)
    .atHour(16)
    .create();

  console.log('✅ Triggers set up successfully. Signage refresh runs daily at midnight, draft review email runs Sunday at 8:00 AM, and send dispatch runs daily at 4:00 PM.');
}

function removeTriggers() {
  const triggers = ScriptApp.getProjectTriggers().slice();
  triggers.forEach(trigger => {
    if (MANAGED_TRIGGER_FUNCTIONS.indexOf(trigger.getHandlerFunction()) !== -1) {
      ScriptApp.deleteTrigger(trigger);
    }
  });

  console.log('🗑️ Managed triggers removed.');
}

function testApprovedApiAccess() {
  const config = assertConfigured();
  const today = new Date();
  const upcomingMonday = getTargetMondayDate();
  const weekId = getCurrentWeekId();

  console.log(`📅 Today: ${Utilities.formatDate(today, config.TIMEZONE, 'EEEE, MMMM dd, yyyy')}`);
  console.log(`📅 Upcoming Monday: ${Utilities.formatDate(upcomingMonday, config.TIMEZONE, 'EEEE, MMMM dd, yyyy')}`);
  console.log(`🧪 Testing approved API access for week: ${weekId}`);

  const payload = fetchApprovedEmailPayloads(weekId, config);
  console.log('Approved state:', !!payload.approved);
  console.log('Delivery plan:', JSON.stringify(payload.delivery || {}));
  const emails = normalizeApprovedOutputs(payload, weekId);

  console.log('Middle School email found:', !!emails.middleSchool);
  console.log('Upper School email found:', !!emails.upperSchool);
  console.log('Already marked sent:', !!(payload.sent && payload.sent.sent));
  console.log('Currently claimed for sending:', !!(payload.sent && payload.sent.sending));

  if (emails.middleSchool) {
    console.log('Middle School subject:', emails.middleSchool.subject);
    console.log('Middle School email length:', emails.middleSchool.html.length, 'characters');
  }
  if (emails.upperSchool) {
    console.log('Upper School subject:', emails.upperSchool.subject);
    console.log('Upper School email length:', emails.upperSchool.html.length, 'characters');
  }
}
