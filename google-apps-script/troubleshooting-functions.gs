/**
 * Troubleshooting functions for the approved `/emails` sender flow.
 *
 * Add these helpers to the same Apps Script project as `sports-email-sender.gs`
 * when you want extra logging or safe dry-run diagnostics.
 */

function debugConfiguration() {
  const result = validateConfiguration();
  console.log(`Configuration valid: ${result.ok}`);
  if (!result.ok) {
    console.log(`Missing properties: ${result.missing.join(', ')}`);
  }
  console.log(`API base URL: ${result.config.API_BASE_URL}`);
  console.log(`Notification recipients: ${result.config.ADMIN_NOTIFICATION_EMAILS.join(', ')}`);
  logRecipientConfig('Middle School', result.config.EMAIL_RECIPIENTS.MIDDLE_SCHOOL);
  logRecipientConfig('Upper School', result.config.EMAIL_RECIPIENTS.UPPER_SCHOOL);
}

/**
 * Test whether the protected Sunday ingest endpoint is reachable for the current week.
 */
function debugScheduledIngestAccess() {
  const config = assertConfigured({ skipRecipients: true });
  const weekId = getCurrentWeekId();
  console.log('🔍 Debugging scheduled ingest access...');
  console.log(`API base URL: ${getApiBaseUrl()}`);
  console.log(`Week ID: ${weekId}`);

  try {
    const payload = triggerScheduledIngest(weekId, config);
    console.log(`Action: ${payload.action}`);
    console.log(`Reason: ${payload.reason}`);
    console.log(`Week in response: ${payload.week && payload.week.week_id}`);
    console.log(`Imported events: ${(payload.source_summary && payload.source_summary.total_events) || 0}`);
  } catch (error) {
    console.error(`❌ Failed to trigger scheduled ingest for ${weekId}:`, error);
  }
}

/**
 * Test whether the approved sender-output API is reachable for the current week.
 */
function debugApprovedApiAccess() {
  debugApprovedApiAccessForWeek(getCurrentWeekId());
}

/**
 * Inspect sender-output for a specific week ID (YYYY-MM-DD).
 */
function debugApprovedApiAccessForWeek(weekId) {
  const config = assertConfigured();
  console.log('🔍 Debugging approved sender-output access...');
  console.log(`API base URL: ${getApiBaseUrl()}`);
  console.log(`Week ID: ${weekId}`);

  try {
    const payload = fetchApprovedEmailPayloads(weekId, config);
    logApprovedPayloadSummary(payload, weekId);
  } catch (error) {
    console.error(`❌ Failed to fetch approved sender-output for ${weekId}:`, error);
  }
}

/**
 * Test whether Apps Script can authenticate to the backend without sending email
 * or changing any week state.
 */
function debugBackendConnection() {
  console.log('🔍 Debugging backend automation connection...');

  try {
    const baseConfig = getBaseScriptConfig();
    const pingPayload = pingBackend(baseConfig);
    console.log(`Backend ping status: ${pingPayload.status || '(no status)'}`);
    console.log(`Backend service: ${pingPayload.service || '(unknown)'}`);
    console.log(`Backend checked at: ${pingPayload.checked_at || '(unknown)'}`);

    const settingsPayload = fetchAutomationSettings(baseConfig);
    const remoteConfig = settingsPayload && settingsPayload.config ? settingsPayload.config : {};
    console.log(`Automation settings reachable: ${!!(settingsPayload && settingsPayload.ok)}`);
    console.log(`Timezone: ${remoteConfig.timezone || '(unset)'}`);
    console.log(`Notification recipients: ${parseEmailList(remoteConfig.admin_notification_emails).length}`);

    const recipients = remoteConfig.email_recipients || {};
    logRecipientConfig('Middle School', recipients.middle_school || {});
    logRecipientConfig('Upper School', recipients.upper_school || {});
    console.log('✅ Backend automation connection succeeded. No email was sent.');
  } catch (error) {
    console.error('❌ Backend automation connection failed:', error);
  }
}

function logApprovedPayloadSummary(payload, weekId) {
  console.log('Backend ok:', !!(payload && payload.ok));
  console.log('Week approved:', !!(payload && payload.approved));
  console.log('Already marked sent:', !!(payload && payload.sent && payload.sent.sent));
  console.log('Currently claimed for sending:', !!(payload && payload.sent && payload.sent.sending));

  if (!payload || payload.approved !== true) {
    console.log(`ℹ️ Week ${weekId} is not approved yet, so sender-output is not ready for delivery.`);
    return;
  }

  const emails = normalizeApprovedOutputs(payload, weekId);
  console.log('Middle School subject:', emails.middleSchool.subject);
  console.log('Middle School email length:', emails.middleSchool.html.length, 'characters');
  console.log('Upper School subject:', emails.upperSchool.subject);
  console.log('Upper School email length:', emails.upperSchool.html.length, 'characters');
}

/**
 * Send a test email to yourself
 */
function sendTestEmail() {
  const config = assertConfigured({ skipRecipients: true });
  const testEmail = Session.getActiveUser().getEmail();
  const weekId = getCurrentWeekId();
  console.log(`📧 Sending test email to: ${testEmail}`);

  const testHtml = `
    <html>
      <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #041e42;">Test Email from Sports Automation</h1>
        <p>This is a test email to verify that the Google Apps Script can send emails successfully.</p>
        <p><strong>Time sent:</strong> ${new Date()}</p>
        <p><strong>Week ID:</strong> ${weekId}</p>
        <div style="background: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
          <h3>System Status:</h3>
          <p>Google Apps Script is working</p>
          <p>Gmail integration is functional</p>
          <p>HTML email formatting is supported</p>
        </div>
        <p>If you received this email, the automation system is ready to send sports emails.</p>
      </body>
    </html>
  `;

  try {
    MailApp.sendEmail({
      to: testEmail,
      subject: 'Sports Email Automation Test',
      htmlBody: testHtml,
      name: config.EMAIL_FROM_NAME,
      replyTo: config.REPLY_TO_EMAIL,
      charset: 'UTF-8'
    });

    console.log('✅ Test email sent successfully!');
  } catch (error) {
    console.error('❌ Failed to send test email:', error);
  }
}

function listTriggers() {
  console.log('⏰ Current triggers:');

  const triggers = ScriptApp.getProjectTriggers();

  if (triggers.length === 0) {
    console.log('No triggers found. Run setupTriggers() to create them.');
    return;
  }

  triggers.forEach((trigger, index) => {
    console.log(`Trigger ${index + 1}: ${trigger.getHandlerFunction()} (${trigger.getTriggerSource()})`);
  });
}

function simulateSundayDraftCycle() {
  console.log('🎭 Simulating Sunday draft cycle...');

  try {
    const config = assertConfigured({ skipRecipients: true });
    const weekId = getCurrentWeekId();
    console.log(`📅 Week ID: ${weekId}`);

    const result = triggerScheduledIngest(weekId, config);
    console.log(`Action: ${result.action}`);
    console.log(`Reason: ${result.reason}`);
    console.log(`Review URL: ${getReviewUrl(weekId)}`);
    console.log(`Imported events: ${(result.source_summary && result.source_summary.total_events) || 0}`);
    console.log('✅ Draft cycle simulation complete.');
  } catch (error) {
    console.error('❌ Draft cycle simulation failed:', error);
  }
}

function simulateEmailSending() {
  console.log('🎭 Simulating email sending process...');

  try {
    const config = assertConfigured();
    const weekId = getCurrentWeekId();
    console.log(`📅 Week ID: ${weekId}`);

    console.log('📥 Fetching approved sender-output from the backend API...');
    const payload = fetchApprovedEmailPayloads(weekId, config);
    const emails = normalizeApprovedOutputs(payload, weekId);

    console.log(`Middle School subject: ${emails.middleSchool.subject}`);
    console.log(`Upper School subject: ${emails.upperSchool.subject}`);
    console.log(`Middle School email length: ${emails.middleSchool.html.length} characters`);
    console.log(`Upper School email length: ${emails.upperSchool.html.length} characters`);

    console.log('📧 Would send emails to:');
    logRecipientConfig('Middle School', config.EMAIL_RECIPIENTS.MIDDLE_SCHOOL);
    logRecipientConfig('Upper School', config.EMAIL_RECIPIENTS.UPPER_SCHOOL);

    console.log('✅ Simulation complete.');
  } catch (error) {
    console.error('❌ Simulation failed:', error);
  }
}

function logRecipientConfig(label, recipientConfig) {
  const bccList = recipientConfig.bcc || [];
  const directCount = recipientConfig.to ? 1 : 0;
  console.log(`${label}: ${directCount + bccList.length} configured recipient target(s)`);
  console.log(`  To: ${recipientConfig.to || '(none set)'}`);
  if (bccList.length > 0) {
    bccList.forEach(email => console.log(`  BCC: ${email}`));
  }
}
