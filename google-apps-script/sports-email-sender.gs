/**
 * Kent Denver Sports Email Automation
 *
 * Google Apps Script owns the sports email cron flow:
 * 1. Sunday 8:00 AM MT: create or confirm the weekly draft in the web app.
 * 2. Email the admin a review link to /emails?week=<YYYY-MM-DD>.
 * 3. Sunday 4:00 PM MT: send only approved payloads.
 */

const CONFIG = {
  API_BASE_URL: '',
  API_ACTOR: 'google-apps-script',
  AUTOMATION_API_KEY: '',
  ADMIN_EMAIL: 'jbarkin28@kentdenver.org',
  REQUEST_TIMEOUT_MS: 30000,
  EMAIL_FROM_NAME: 'Student Leadership',
  TIMEZONE: 'America/Denver',

  EMAIL_RECIPIENTS: {
    MIDDLE_SCHOOL: {
      to: '',
      bcc: ['allmiddleschoolstudents@kentdenver.org', 'middleschoolteachers@kentdenver.org']
    },
    UPPER_SCHOOL: {
      to: '',
      bcc: ['allupperschoolstudents@kentdenver.org', 'upperschoolteachers@kentdenver.org']
    }
  }
};

const MANAGED_TRIGGER_FUNCTIONS = ['runSundayDraftCycle', 'sendSportsEmails'];

function runSundayDraftCycle() {
  const weekId = getCurrentWeekId();

  try {
    console.log(`📥 Starting Sunday draft cycle for ${weekId}...`);
    assertAutomationApiKeyConfigured();

    const ingestResult = triggerScheduledIngest(weekId);
    sendAdminReviewNotification(weekId, ingestResult);
    logEmailActivity('DRAFT', `Weekly draft cycle ${ingestResult.action} for ${weekId}`);
  } catch (error) {
    console.error('❌ Error in runSundayDraftCycle:', error);
    sendErrorNotification(`Error running Sunday draft cycle for ${weekId}: ${error.message}`);
    logEmailActivity('ERROR', `Draft cycle failed for ${weekId}: ${error.message}`);
  }
}

function runSundayDraftCycleManual() {
  runSundayDraftCycle();
}

function sendSportsEmails() {
  let weekId = 'unknown';
  let sendClaimed = false;

  try {
    console.log('🏈 Starting automated sports email sending...');

    weekId = getCurrentWeekId();
    console.log(`📅 Looking for approved emails for week: ${weekId}`);

    const payload = fetchApprovedEmailPayloads(weekId);

    if (!ensureWeekCanSend(payload.sent, weekId)) {
      return;
    }

    const emails = normalizeApprovedOutputs(payload, weekId);
    const sendClaim = claimWeekSend(weekId);

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

    const middleSchoolSent = sendEmail(
      CONFIG.EMAIL_RECIPIENTS.MIDDLE_SCHOOL,
      emails.middleSchool.subject,
      emails.middleSchool.html
    );
    if (!middleSchoolSent) {
      throw new Error(`Failed to send middle-school email for ${weekId}`);
    }
    sentCount++;

    const upperSchoolSent = sendEmail(
      CONFIG.EMAIL_RECIPIENTS.UPPER_SCHOOL,
      emails.upperSchool.subject,
      emails.upperSchool.html
    );
    if (!upperSchoolSent) {
      throw new Error(`Failed to send upper-school email for ${weekId}`);
    }
    sentCount++;

    if (sentCount !== totalEmails) {
      throw new Error(`Expected to send ${totalEmails} emails but only sent ${sentCount}`);
    }

    const sentState = markWeekSent(weekId);

    console.log(`✅ Successfully sent ${sentCount} approved sports emails for week ${weekId}!`);
    console.log(`📝 Backend sent-state recorded: ${JSON.stringify(sentState)}`);
    logEmailActivity('SUCCESS', `Sent ${sentCount} emails for week ${weekId}`);
  } catch (error) {
    console.error('❌ Error in sendSportsEmails:', error);
    const errorMessage = sendClaimed
      ? `Error sending sports emails: ${error.message}\n\nWeek ${weekId} remains claimed as sending to prevent duplicate reruns. Verify whether any audience emails were delivered before resolving the backend sent-state.`
      : `Error sending sports emails: ${error.message}`;
    sendErrorNotification(errorMessage);
    logEmailActivity('ERROR', errorMessage);
  }
}

function sendSportsEmailsManual() {
  sendSportsEmails();
}

function getTargetMondayDate() {
  const today = new Date();
  const dayOfWeek = today.getDay();

  let daysUntilMonday;
  if (dayOfWeek === 0) {
    daysUntilMonday = 1;
  } else if (dayOfWeek === 1) {
    daysUntilMonday = 0;
  } else {
    daysUntilMonday = 8 - dayOfWeek;
  }

  const upcomingMonday = new Date(today);
  upcomingMonday.setDate(today.getDate() + daysUntilMonday);

  return upcomingMonday;
}

function getCurrentWeekId() {
  return Utilities.formatDate(getTargetMondayDate(), CONFIG.TIMEZONE, 'yyyy-MM-dd');
}

function getCurrentWeekFolder() {
  return Utilities.formatDate(getTargetMondayDate(), CONFIG.TIMEZONE, 'MMMdd').toLowerCase();
}

function fetchApprovedEmailPayloads(weekId) {
  const apiBaseUrl = getApiBaseUrl();
  const url = `${apiBaseUrl}/api/emails/weeks/${encodeURIComponent(weekId)}/sender-output`;
  console.log(`📥 Fetching approved sender payloads from: ${url}`);
  return fetchJson(url, { method: 'GET' });
}

function triggerScheduledIngest(weekId) {
  const apiBaseUrl = getApiBaseUrl();
  const url = `${apiBaseUrl}/api/emails/automation/weeks/${encodeURIComponent(weekId)}/scheduled-ingest`;
  console.log(`📥 Triggering scheduled ingest at: ${url}`);
  return fetchJson(url, { method: 'POST' });
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

function fetchJson(url, options) {
  const requestOptions = Object.assign(
    {
      muteHttpExceptions: true,
      contentType: 'application/json; charset=UTF-8',
      headers: buildApiHeaders()
    },
    options || {}
  );

  if (!requestOptions.headers['X-Email-Actor'] && CONFIG.API_ACTOR) {
    requestOptions.headers['X-Email-Actor'] = CONFIG.API_ACTOR;
  }

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

function buildApiHeaders() {
  const headers = {
    'User-Agent': 'Kent Denver Sports Email Bot',
    'X-Email-Actor': CONFIG.API_ACTOR
  };

  if (String(CONFIG.AUTOMATION_API_KEY || '').trim()) {
    headers['X-Automation-Key'] = String(CONFIG.AUTOMATION_API_KEY).trim();
  }

  return headers;
}

function getApiBaseUrl() {
  const rawValue = String(CONFIG.API_BASE_URL || '').trim();
  if (!rawValue) {
    throw new Error('CONFIG.API_BASE_URL must be set to the deployed /emails host before sending');
  }
  return rawValue.replace(/\/+$/, '');
}

function getReviewUrl(weekId) {
  return `${getApiBaseUrl()}/emails?week=${encodeURIComponent(weekId)}`;
}

function assertAutomationApiKeyConfigured() {
  if (!String(CONFIG.AUTOMATION_API_KEY || '').trim()) {
    throw new Error('CONFIG.AUTOMATION_API_KEY must be set before running the Sunday draft cycle');
  }
}

function claimWeekSend(weekId) {
  return updateWeekSendState(weekId, 'sending');
}

function markWeekSent(weekId) {
  return updateWeekSendState(weekId, 'sent');
}

function updateWeekSendState(weekId, state) {
  const apiBaseUrl = getApiBaseUrl();
  const url = `${apiBaseUrl}/api/emails/weeks/${encodeURIComponent(weekId)}/sent`;
  const payload = fetchJson(url, {
    method: 'POST',
    payload: JSON.stringify({ week_id: weekId, state })
  });
  return payload.sent || (payload.week && payload.week.sent) || null;
}

function sendEmail(recipientConfig, subject, htmlContent) {
  try {
    console.log(`📧 Sending email to: ${recipientConfig.to}`);
    if (recipientConfig.bcc && recipientConfig.bcc.length > 0) {
      console.log(`📧 BCC: ${recipientConfig.bcc.join(', ')}`);
    }

    const emailOptions = {
      to: recipientConfig.to,
      subject: subject,
      htmlBody: htmlContent,
      name: CONFIG.EMAIL_FROM_NAME,
      replyTo: 'studentleader@kentdenver.org',
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

function sendAdminReviewNotification(weekId, ingestResult) {
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
    to: CONFIG.ADMIN_EMAIL,
    subject,
    body:
      `${statusLine}\n\n` +
      `${countsLine}\n\n` +
      `Review and approve here:\n${reviewUrl}\n`,
    htmlBody:
      `<p>${statusLine}</p>` +
      `<p>${countsLine}</p>` +
      `<p><a href="${reviewUrl}">Open weekly review</a></p>`,
    name: CONFIG.EMAIL_FROM_NAME,
    charset: 'UTF-8'
  });
}

function sendErrorNotification(errorMessage) {
  try {
    MailApp.sendEmail({
      to: CONFIG.ADMIN_EMAIL,
      subject: '🚨 Sports Email Automation Error',
      body: `The sports email automation encountered an error:\n\n${errorMessage}\n\nTime: ${new Date()}\n\nPlease check the logs and fix the issue.`,
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
  removeTriggers();

  ScriptApp.newTrigger('runSundayDraftCycle')
    .timeBased()
    .everyWeeks(1)
    .onWeekDay(ScriptApp.WeekDay.SUNDAY)
    .atHour(8)
    .create();

  ScriptApp.newTrigger('sendSportsEmails')
    .timeBased()
    .everyWeeks(1)
    .onWeekDay(ScriptApp.WeekDay.SUNDAY)
    .atHour(16)
    .create();

  console.log('✅ Triggers set up successfully. Draft review email runs Sunday at 8:00 AM and approved sends run Sunday at 4:00 PM.');
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
  const today = new Date();
  const upcomingMonday = getTargetMondayDate();
  const weekId = getCurrentWeekId();

  console.log(`📅 Today: ${Utilities.formatDate(today, CONFIG.TIMEZONE, 'EEEE, MMMM dd, yyyy')}`);
  console.log(`📅 Upcoming Monday: ${Utilities.formatDate(upcomingMonday, CONFIG.TIMEZONE, 'EEEE, MMMM dd, yyyy')}`);
  console.log(`🧪 Testing approved API access for week: ${weekId}`);

  const payload = fetchApprovedEmailPayloads(weekId);
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
