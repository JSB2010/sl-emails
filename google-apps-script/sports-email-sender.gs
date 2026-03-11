/**
 * Kent Denver Sports Email Automation
 * 
 * This Google Apps Script fetches approved weekly email payloads from the
 * /emails API and sends them via Gmail every Sunday at 4:00 PM.
 * 
 * Setup Instructions:
 * 1. Create a new Google Apps Script project
 * 2. Replace the default Code.gs with this code
 * 3. Set CONFIG.API_BASE_URL to the deployed host that serves /emails
 * 4. Update the EMAIL_RECIPIENTS object with actual email addresses
 * 5. Set up time-based triggers (see setupTriggers function)
 * 6. Test with sendSportsEmailsManual() first
 */

// Configuration - UPDATE THESE VALUES BEFORE LIVE SENDS
const CONFIG = {
  API_BASE_URL: '',
  API_ACTOR: 'google-apps-script',
  ADMIN_EMAIL: 'jbarkin28@kentdenver.org',
  REQUEST_TIMEOUT_MS: 30000,
  
  // BCC recipients for each school level
  EMAIL_RECIPIENTS: {
    MIDDLE_SCHOOL: {
      to: '',
      bcc: ["allmiddleschoolstudents@kentdenver.org","middleschoolteachers@kentdenver.org"] // Add additional BCC recipients if needed
    },
    UPPER_SCHOOL: {
      to: "",
      bcc: ["allupperschoolstudents@kentdenver.org","upperschoolteachers@kentdenver.org"] // Add additional BCC recipients if needed
    }
  },

  // Email settings
  EMAIL_FROM_NAME: 'Student Leadership',
  
  // Timezone for logging (Mountain Time)
  TIMEZONE: 'America/Denver'
};

/**
 * Main function that runs automatically via trigger
 * Fetches and sends sports emails
 */
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

/**
 * Manual testing function - use this to test the setup
 */
function sendSportsEmailsManual() {
  console.log('🧪 Running manual test...');
  sendSportsEmails();
}

/**
 * Get the upcoming Monday for the target send week.
 *
 * Logic:
 * - Sunday through Saturday: Generate for the next Monday
 * - Example: Sep 29 (Mon) through Oct 5 (Sun) → returns Oct 06
 * - On Monday Oct 6, still returns Oct 06 (gives flexibility for manual reruns)
 * - On Tuesday Oct 7 onwards → returns Oct 13
 */
function getTargetMondayDate() {
  const today = new Date();
  const dayOfWeek = today.getDay(); // 0=Sunday, 1=Monday, etc.

  // Calculate the next Monday
  let daysUntilMonday;
  if (dayOfWeek === 0) {
    // Sunday: next Monday is 1 day away
    daysUntilMonday = 1;
  } else if (dayOfWeek === 1) {
    // Monday: use today so manual reruns keep the current approved week
    daysUntilMonday = 0;
  } else {
    // Tuesday-Saturday: next Monday is (8 - dayOfWeek) days away
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
  const upcomingMonday = getTargetMondayDate();

  // Format as "oct06" style
  return Utilities.formatDate(upcomingMonday, CONFIG.TIMEZONE, 'MMMdd').toLowerCase();
}

/**
 * Fetch approved sender payloads from the backend API.
 */
function fetchApprovedEmailPayloads(weekId) {
  const apiBaseUrl = getApiBaseUrl();
  const url = `${apiBaseUrl}/api/emails/weeks/${encodeURIComponent(weekId)}/sender-output`;
  console.log(`📥 Fetching approved sender payloads from: ${url}`);
  return fetchJson(url, { method: 'GET' });
}

/**
 * Ensure both approved outputs are present before sending.
 */
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

/**
 * Fetch JSON from the backend API and convert non-2xx responses into errors.
 */
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
  return {
    'User-Agent': 'Kent Denver Sports Email Bot',
    'X-Email-Actor': CONFIG.API_ACTOR
  };
}

function getApiBaseUrl() {
  const rawValue = String(CONFIG.API_BASE_URL || '').trim();
  if (!rawValue) {
    throw new Error('CONFIG.API_BASE_URL must be set to the deployed /emails host before sending');
  }
  return rawValue.replace(/\/+$/, '');
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

/**
 * Send email with BCC recipients
 */
function sendEmail(recipientConfig, subject, htmlContent) {
  try {
    console.log(`📧 Sending email to: ${recipientConfig.to}`);
    if (recipientConfig.bcc && recipientConfig.bcc.length > 0) {
      console.log(`📧 BCC: ${recipientConfig.bcc.join(', ')}`);
    }

    // Use MailApp with UTF-8 support
    const emailOptions = {
      to: recipientConfig.to,
      subject: subject,
      htmlBody: htmlContent,
      name: CONFIG.EMAIL_FROM_NAME,
      replyTo: 'studentleader@kentdenver.org',
      charset: 'UTF-8',
      noReply: false
    };

    // Add BCC if there are any
    if (recipientConfig.bcc && recipientConfig.bcc.length > 0) {
      emailOptions.bcc = recipientConfig.bcc.join(',');
    }

    MailApp.sendEmail(emailOptions);

    console.log(`✅ Email sent successfully`);
    return true;
  } catch (error) {
    console.error(`❌ Error sending email:`, error);
    return false;
  }
}

/**
 * Send error notification to admin
 */
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

/**
 * Log email activity to a spreadsheet (optional but recommended)
 */
function logEmailActivity(status, message) {
  try {
    // You can create a Google Sheet to track email sending
    // Uncomment and update the spreadsheet ID if you want logging
    /*
    const spreadsheetId = 'YOUR_SPREADSHEET_ID_HERE';
    const sheet = SpreadsheetApp.openById(spreadsheetId).getActiveSheet();
    
    sheet.appendRow([
      new Date(),
      status,
      message,
      getCurrentWeekFolder()
    ]);
    */
    
    console.log(`📝 Log: ${status} - ${message}`);
  } catch (error) {
    console.error('Failed to log activity:', error);
  }
}

/**
 * Setup time-based triggers
 * Run this once to set up automatic execution
 */
function setupTriggers() {
  // Delete existing triggers first
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'sendSportsEmails') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  
  // Create new trigger for every Sunday at 4:00 PM
  ScriptApp.newTrigger('sendSportsEmails')
    .timeBased()
    .everyWeeks(1)
    .onWeekDay(ScriptApp.WeekDay.SUNDAY)
    .atHour(16) // 4:00 PM (24-hour format)
    .create();
    
  console.log('✅ Trigger set up successfully! Emails will be sent every Sunday at 4:00 PM.');
}

/**
 * Remove all triggers (for cleanup)
 */
function removeTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'sendSportsEmails') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  
  console.log('🗑️ All triggers removed.');
}

/**
 * Test function to check if approved API payloads are accessible
 */
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

