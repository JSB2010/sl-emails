/**
 * Troubleshooting Functions for Sports Email Automation
 * 
 * Add these functions to your Google Apps Script project for easier debugging
 * and testing. These are separate from the main automation code.
 */

/**
 * Test if we can access GitHub and what files are available
 */
function debugGitHubAccess() {
  console.log('🔍 Debugging GitHub access...');
  
  const folderName = getCurrentWeekFolder();
  console.log(`Current week folder: ${folderName}`);
  
  // Test different week folders in case current week doesn't exist
  const testFolders = [
    folderName,
    'sep29', // Known existing folder
    'sep22'  // Another known existing folder
  ];
  
  testFolders.forEach(folder => {
    console.log(`\n📁 Testing folder: ${folder}`);
    
    const baseUrl = `https://raw.githubusercontent.com/JSB2010/sl-emails/main/sports-emails`;
    const msUrl = `${baseUrl}/${folder}/games-week-middle-school-${folder}.html`;
    const usUrl = `${baseUrl}/${folder}/games-week-upper-school-${folder}.html`;
    
    console.log(`MS URL: ${msUrl}`);
    console.log(`US URL: ${usUrl}`);
    
    // Test middle school file
    try {
      const msResponse = UrlFetchApp.fetch(msUrl);
      console.log(`MS File Status: ${msResponse.getResponseCode()}`);
      if (msResponse.getResponseCode() === 200) {
        console.log(`MS File Size: ${msResponse.getContentText().length} characters`);
      }
    } catch (error) {
      console.log(`MS File Error: ${error.message}`);
    }
    
    // Test upper school file
    try {
      const usResponse = UrlFetchApp.fetch(usUrl);
      console.log(`US File Status: ${usResponse.getResponseCode()}`);
      if (usResponse.getResponseCode() === 200) {
        console.log(`US File Size: ${usResponse.getContentText().length} characters`);
      }
    } catch (error) {
      console.log(`US File Error: ${error.message}`);
    }
  });
}

/**
 * Send a test email to yourself
 */
function sendTestEmail() {
  const testEmail = Session.getActiveUser().getEmail();
  console.log(`📧 Sending test email to: ${testEmail}`);
  
  const testHtml = `
    <html>
      <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #041e42;">🏈 Test Email from Sports Automation</h1>
        <p>This is a test email to verify that the Google Apps Script can send emails successfully.</p>
        <p><strong>Time sent:</strong> ${new Date()}</p>
        <p><strong>Week folder:</strong> ${getCurrentWeekFolder()}</p>
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
 * Test the week folder calculation
 */
function testWeekFolderCalculation() {
  console.log('📅 Testing week folder calculation...');
  console.log('Logic: Generate for the next occurring Monday');
  console.log('(On Monday, still generates for that Monday - gives flexibility for reruns)\n');

  const today = new Date();
  console.log(`Today: ${today}`);
  console.log(`Day of week: ${today.getDay()} (0=Sunday, 1=Monday, etc.)`);

  // Test the current calculation
  const currentFolder = getCurrentWeekFolder();
  console.log(`Current folder: ${currentFolder}`);

  // Calculate and show next Monday
  const dayOfWeek = today.getDay();
  const daysUntilMonday = dayOfWeek === 0 ? 1 : (8 - dayOfWeek);
  const upcomingMonday = new Date(today);
  upcomingMonday.setDate(today.getDate() + daysUntilMonday);
  console.log(`Upcoming Monday: ${upcomingMonday.toDateString()}`);

  // Test for different days to see the pattern
  console.log('\n📊 Folder for different dates:');
  for (let i = 0; i < 14; i++) {
    const testDate = new Date(today);
    testDate.setDate(today.getDate() + i);

    // Calculate upcoming Monday from this test date
    const testDayOfWeek = testDate.getDay();
    const testDaysUntilMonday = testDayOfWeek === 0 ? 1 : (8 - testDayOfWeek);
    const testUpcomingMonday = new Date(testDate);
    testUpcomingMonday.setDate(testDate.getDate() + testDaysUntilMonday);

    const folderName = Utilities.formatDate(testUpcomingMonday, 'America/Denver', 'MMMdd').toLowerCase();
    const dayName = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][testDayOfWeek];

    console.log(`  ${dayName} ${testDate.toDateString()} → ${folderName}`);
  }
}

/**
 * Simulate the full email sending process without actually sending
 */
function simulateEmailSending() {
  console.log('🎭 Simulating email sending process...');
  
  try {
    const folderName = getCurrentWeekFolder();
    console.log(`📁 Week folder: ${folderName}`);
    
    // Fetch emails
    console.log('📥 Fetching emails from GitHub...');
    const emails = fetchSportsEmails(folderName);
    
    console.log(`Middle School email: ${emails.middleSchool ? 'Found' : 'Not found'}`);
    console.log(`Upper School email: ${emails.upperSchool ? 'Found' : 'Not found'}`);
    
    if (emails.middleSchool) {
      console.log(`  MS email length: ${emails.middleSchool.length} characters`);
      console.log(`  MS email preview: ${emails.middleSchool.substring(0, 100)}...`);
    }
    
    if (emails.upperSchool) {
      console.log(`  US email length: ${emails.upperSchool.length} characters`);
      console.log(`  US email preview: ${emails.upperSchool.substring(0, 100)}...`);
    }
    
    // Simulate sending (without actually sending)
    console.log('\n📧 Would send emails to:');
    if (emails.middleSchool) {
      console.log(`  Middle School: ${CONFIG.EMAIL_RECIPIENTS.MIDDLE_SCHOOL.length} recipients`);
      CONFIG.EMAIL_RECIPIENTS.MIDDLE_SCHOOL.forEach(email => console.log(`    - ${email}`));
    }
    
    if (emails.upperSchool) {
      console.log(`  Upper School: ${CONFIG.EMAIL_RECIPIENTS.UPPER_SCHOOL.length} recipients`);
      CONFIG.EMAIL_RECIPIENTS.UPPER_SCHOOL.forEach(email => console.log(`    - ${email}`));
    }
    
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
