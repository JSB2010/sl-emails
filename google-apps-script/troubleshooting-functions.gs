/**
 * Troubleshooting functions for the approved `/emails` sender flow.
 *
 * Add these helpers to the same Apps Script project as `sports-email-sender.gs`
 * when you want extra logging or safe dry-run diagnostics.
 */

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
  console.log('🔍 Debugging approved sender-output access...');
  console.log(`API base URL: ${getApiBaseUrl()}`);
  console.log(`Week ID: ${weekId}`);

  try {
    const payload = fetchApprovedEmailPayloads(weekId);
    logApprovedPayloadSummary(payload, weekId);
  } catch (error) {
    console.error(`❌ Failed to fetch approved sender-output for ${weekId}:`, error);
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
  const testEmail = Session.getActiveUser().getEmail();
  const weekId = getCurrentWeekId();
  console.log(`📧 Sending test email to: ${testEmail}`);
  
  const testHtml = `
    <html>
      <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #041e42;">🏈 Test Email from Sports Automation</h1>
        <p>This is a test email to verify that the Google Apps Script can send emails successfully.</p>
        <p><strong>Time sent:</strong> ${new Date()}</p>
        <p><strong>Week ID:</strong> ${weekId}</p>
        <div style="background: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
          <h3>System Status:</h3>
          <p>✅ Google Apps Script is working</p>
          <p>✅ Gmail integration is functional</p>
          <p>✅ HTML email formatting is supported</p>
        </div>
        <p>If you received this email, the automation system is ready to send sports emails!</p>
      </body>
    </html>
  `;
  
  try {
    // Use MailApp with UTF-8 charset to ensure emojis display correctly
    MailApp.sendEmail({
      to: testEmail,
      subject: '🧪 Sports Email Automation Test',
      htmlBody: testHtml,
      name: 'Kent Denver Sports Email Test',
      charset: 'UTF-8'
    });

    console.log('✅ Test email sent successfully!');
  } catch (error) {
    console.error('❌ Failed to send test email:', error);
  }
}

/**
 * Check Gmail quota and limits
 */
function checkGmailQuota() {
  console.log('📊 Checking Gmail quota information...');
  
  try {
    // Get recent emails to check if Gmail is accessible
    const threads = GmailApp.getInboxThreads(0, 1);
    console.log('✅ Gmail access: OK');
    
    // Note: Apps Script doesn't provide direct quota checking
    // But we can provide general information
    console.log('📧 Gmail Limits:');
    console.log('  - Consumer accounts: 100 emails/day');
    console.log('  - Google Workspace: 1,500 emails/day');
    console.log('  - Rate limit: ~100 emails/hour');
    
    console.log('\n💡 Tips:');
    console.log('  - Each recipient counts as one email');
    console.log('  - Quota resets at midnight Pacific Time');
    console.log('  - Failed sends still count toward quota');
    
  } catch (error) {
    console.error('❌ Gmail access error:', error);
  }
}

/**
 * List all current triggers
 */
function listTriggers() {
  console.log('⏰ Current triggers:');
  
  const triggers = ScriptApp.getProjectTriggers();
  
  if (triggers.length === 0) {
    console.log('No triggers found. Run setupTriggers() to create them.');
    return;
  }
  
  triggers.forEach((trigger, index) => {
    console.log(`\nTrigger ${index + 1}:`);
    console.log(`  Function: ${trigger.getHandlerFunction()}`);
    console.log(`  Type: ${trigger.getTriggerSource()}`);
    
    if (trigger.getTriggerSource() === ScriptApp.TriggerSource.CLOCK) {
      console.log(`  Schedule: Every ${trigger.getTriggerSourceId()}`);
    }
  });
}

/**
 * Test the target week ID calculation used for sender-output fetches.
 */
function testWeekIdCalculation() {
  console.log('📅 Testing week ID calculation...');
  console.log('Logic: use the Monday week ID targeted by /api/emails/weeks/<week-id>/sender-output');
  console.log('(On Monday, still uses that Monday - gives flexibility for manual reruns)\n');

  const today = new Date();
  console.log(`Today: ${today}`);
  console.log(`Day of week: ${today.getDay()} (0=Sunday, 1=Monday, etc.)`);

  // Test the current calculation
  const currentWeekId = getCurrentWeekId();
  console.log(`Current week ID: ${currentWeekId}`);

  // Calculate and show next Monday
  const dayOfWeek = today.getDay();
  const daysUntilMonday = dayOfWeek === 0 ? 1 : (8 - dayOfWeek);
  const upcomingMonday = new Date(today);
  upcomingMonday.setDate(today.getDate() + daysUntilMonday);
  console.log(`Upcoming Monday: ${upcomingMonday.toDateString()}`);

  // Test for different days to see the pattern
  console.log('\n📊 Week IDs for different dates:');
  for (let i = 0; i < 14; i++) {
    const testDate = new Date(today);
    testDate.setDate(today.getDate() + i);

    // Calculate upcoming Monday from this test date
    const testDayOfWeek = testDate.getDay();
    const testDaysUntilMonday = testDayOfWeek === 0 ? 1 : (8 - testDayOfWeek);
    const testUpcomingMonday = new Date(testDate);
    testUpcomingMonday.setDate(testDate.getDate() + testDaysUntilMonday);

    const weekId = Utilities.formatDate(testUpcomingMonday, 'America/Denver', 'yyyy-MM-dd');
    const dayName = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][testDayOfWeek];

    console.log(`  ${dayName} ${testDate.toDateString()} → ${weekId}`);
  }
}

/**
 * Simulate the full email sending process without actually sending
 */
function simulateEmailSending() {
  console.log('🎭 Simulating email sending process...');
  
  try {
    const weekId = getCurrentWeekId();
    console.log(`📅 Week ID: ${weekId}`);
    
    console.log('📥 Fetching approved sender-output from the backend API...');
    const payload = fetchApprovedEmailPayloads(weekId);
    const emails = normalizeApprovedOutputs(payload, weekId);

    console.log(`Middle School subject: ${emails.middleSchool.subject}`);
    console.log(`Upper School subject: ${emails.upperSchool.subject}`);
    console.log(`Middle School email length: ${emails.middleSchool.html.length} characters`);
    console.log(`Upper School email length: ${emails.upperSchool.html.length} characters`);
    
    // Simulate sending (without actually sending)
    console.log('\n📧 Would send emails to:');
    logRecipientConfig('Middle School', CONFIG.EMAIL_RECIPIENTS.MIDDLE_SCHOOL);
    logRecipientConfig('Upper School', CONFIG.EMAIL_RECIPIENTS.UPPER_SCHOOL);
    
    console.log('\n✅ Simulation complete! Everything looks ready.');
    
  } catch (error) {
    console.error('❌ Simulation failed:', error);
  }
}

/**
 * Check if it's currently Sunday (when emails should be sent)
 */
function checkIfSunday() {
  const now = new Date();
  const day = now.getDay();
  const hour = now.getHours();
  
  console.log(`Current time: ${now}`);
  console.log(`Day of week: ${day} (0=Sunday)`);
  console.log(`Hour: ${hour} (24-hour format)`);
  
  if (day === 0) {
    console.log('✅ Today is Sunday!');
    if (hour >= 16) {
      console.log('✅ It\'s after 4:00 PM - emails should be sent');
    } else {
      console.log(`⏰ It's before 4:00 PM (currently ${hour}:xx) - emails will be sent later`);
    }
  } else {
    const daysUntilSunday = (7 - day) % 7;
    console.log(`📅 Today is not Sunday. Next Sunday is in ${daysUntilSunday} days.`);
  }
}

/**
 * Emergency function to send emails immediately (bypass schedule)
 */
function emergencySendEmails() {
  console.log('🚨 EMERGENCY EMAIL SEND - Bypassing normal schedule');
  
  const confirm = Browser.msgBox(
    'Emergency Email Send',
    'Are you sure you want to send sports emails immediately? This will send to all configured recipients.',
    Browser.Buttons.YES_NO
  );
  
  if (confirm === 'yes') {
    console.log('✅ User confirmed emergency send');
    sendSportsEmails();
  } else {
    console.log('❌ User cancelled emergency send');
  }
}

function logRecipientConfig(label, recipientConfig) {
  const bccList = recipientConfig.bcc || [];
  const directCount = recipientConfig.to ? 1 : 0;
  console.log(`  ${label}: ${directCount + bccList.length} configured recipient target(s)`);
  console.log(`    To: ${recipientConfig.to || '(none set)'}`);
  if (bccList.length > 0) {
    bccList.forEach(email => console.log(`    BCC: ${email}`));
  }
}
