/**
 * Kent Denver Sports Email Automation
 * 
 * This Google Apps Script automatically fetches generated sports email HTML files
 * from GitHub and sends them via Gmail every Sunday at 4:00 PM.
 * 
 * Setup Instructions:
 * 1. Create a new Google Apps Script project
 * 2. Replace the default Code.gs with this code
 * 3. Update the EMAIL_RECIPIENTS object with actual email addresses
 * 4. Set up time-based triggers (see setupTriggers function)
 * 5. Test with sendSportsEmailsManual() first
 */

// Configuration - UPDATE THESE VALUES
const CONFIG = {
  GITHUB_REPO: 'JSB2010/sl-emails',
  GITHUB_BRANCH: 'main',
  BASE_PATH: 'sports-emails',
  
  // Update these with actual email addresses
  EMAIL_RECIPIENTS: {
    MIDDLE_SCHOOL: [
      'jbarkin@community.kentdenver.org',
      // Add more recipients as needed
    ],
    UPPER_SCHOOL: [
      'jbarkin28@kentdenver.org',
      // Add more recipients as needed
    ]
  },
  
  // Email settings
  EMAIL_FROM_NAME: 'Kent Denver Athletics',
  
  // Timezone for logging (Mountain Time)
  TIMEZONE: 'America/Denver'
};

/**
 * Main function that runs automatically via trigger
 * Fetches and sends sports emails
 */
function sendSportsEmails() {
  try {
    console.log('🏈 Starting automated sports email sending...');
    
    // Get current week folder name (e.g., "oct06")
    const folderName = getCurrentWeekFolder();
    console.log(`📁 Looking for emails in folder: ${folderName}`);
    
    // Fetch HTML files from GitHub
    const emails = fetchSportsEmails(folderName);
    
    if (!emails.middleSchool && !emails.upperSchool) {
      console.error('❌ No email files found! Check if GitHub Actions generated the files.');
      sendErrorNotification('No email files found for this week');
      return;
    }
    
    // Send emails
    let sentCount = 0;
    
    if (emails.middleSchool) {
      const success = sendEmailToRecipients(
        CONFIG.EMAIL_RECIPIENTS.MIDDLE_SCHOOL,
        'Kent Denver Middle School Games This Week',
        emails.middleSchool
      );
      if (success) sentCount++;
    }
    
    if (emails.upperSchool) {
      const success = sendEmailToRecipients(
        CONFIG.EMAIL_RECIPIENTS.UPPER_SCHOOL,
        'Kent Denver Upper School Games This Week',
        emails.upperSchool
      );
      if (success) sentCount++;
    }
    
    console.log(`✅ Successfully sent ${sentCount} sports emails!`);
    
    // Log success to a spreadsheet (optional)
    logEmailActivity('SUCCESS', `Sent ${sentCount} emails for week ${folderName}`);
    
  } catch (error) {
    console.error('❌ Error in sendSportsEmails:', error);
    sendErrorNotification(`Error sending sports emails: ${error.message}`);
    logEmailActivity('ERROR', error.message);
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
 * Get the upcoming Monday's folder name (e.g., "oct06")
 *
 * Logic:
 * - Sunday through Saturday: Generate for the next Monday
 * - Example: Sep 29 (Mon) through Oct 5 (Sun) → generates "oct06"
 * - On Monday Oct 6, still generates "oct06" (gives flexibility for manual reruns)
 * - On Tuesday Oct 7 onwards → generates "oct13"
 */
function getCurrentWeekFolder() {
  const today = new Date();
  const dayOfWeek = today.getDay(); // 0=Sunday, 1=Monday, etc.

  // Calculate the next Monday
  let daysUntilMonday;
  if (dayOfWeek === 0) {
    // Sunday: next Monday is 1 day away
    daysUntilMonday = 1;
  } else {
    // Monday-Saturday: next Monday is (8 - dayOfWeek) days away
    daysUntilMonday = 8 - dayOfWeek;
  }

  const upcomingMonday = new Date(today);
  upcomingMonday.setDate(today.getDate() + daysUntilMonday);

  // Format as "oct06" style
  return Utilities.formatDate(upcomingMonday, CONFIG.TIMEZONE, 'MMMdd').toLowerCase();
}

/**
 * Fetch sports email HTML files from GitHub
 */
function fetchSportsEmails(folderName) {
  const baseUrl = `https://raw.githubusercontent.com/${CONFIG.GITHUB_REPO}/${CONFIG.GITHUB_BRANCH}/${CONFIG.BASE_PATH}`;
  
  const middleSchoolFile = `${folderName}/games-week-middle-school-${folderName}.html`;
  const upperSchoolFile = `${folderName}/games-week-upper-school-${folderName}.html`;
  
  return {
    middleSchool: fetchGitHubFile(`${baseUrl}/${middleSchoolFile}`),
    upperSchool: fetchGitHubFile(`${baseUrl}/${upperSchoolFile}`)
  };
}

/**
 * Fetch a single file from GitHub
 */
function fetchGitHubFile(url) {
  try {
    console.log(`📥 Fetching: ${url}`);

    const response = UrlFetchApp.fetch(url, {
      method: 'GET',
      headers: {
        'User-Agent': 'Kent Denver Sports Email Bot'
      },
      contentType: 'text/html; charset=UTF-8'
    });

    if (response.getResponseCode() === 200) {
      console.log(`✅ Successfully fetched file`);
      // Explicitly get content as UTF-8
      return response.getContentText('UTF-8');
    } else {
      console.warn(`⚠️ File not found (${response.getResponseCode()}): ${url}`);
      return null;
    }
  } catch (error) {
    console.error(`❌ Error fetching ${url}:`, error);
    return null;
  }
}

/**
 * Send email to multiple recipients
 */
function sendEmailToRecipients(recipients, subject, htmlContent) {
  try {
    recipients.forEach(recipient => {
      console.log(`📧 Sending email to: ${recipient}`);

      // Use MailApp instead of GmailApp for better UTF-8 support
      MailApp.sendEmail({
        to: recipient,
        subject: subject,
        htmlBody: htmlContent,
        name: CONFIG.EMAIL_FROM_NAME,
        replyTo: 'noreply@kentdenver.org',
        charset: 'UTF-8', // Explicitly set UTF-8 encoding
        noReply: false
      });
    });

    console.log(`✅ Sent emails to ${recipients.length} recipients`);
    return true;
  } catch (error) {
    console.error(`❌ Error sending emails:`, error);
    return false;
  }
}

/**
 * Send error notification to admin
 */
function sendErrorNotification(errorMessage) {
  try {
    // Update with your email address for error notifications
    const adminEmail = 'jbarkin28@kentdenver.org';

    MailApp.sendEmail({
      to: adminEmail,
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
 * Test function to check if GitHub files are accessible
 */
function testGitHubAccess() {
  const today = new Date();
  const dayOfWeek = today.getDay();

  // Calculate upcoming Monday using same logic as getCurrentWeekFolder
  let daysUntilMonday;
  if (dayOfWeek === 0) {
    daysUntilMonday = 1;
  } else {
    daysUntilMonday = 8 - dayOfWeek;
  }

  const upcomingMonday = new Date(today);
  upcomingMonday.setDate(today.getDate() + daysUntilMonday);
  const folderName = getCurrentWeekFolder();

  console.log(`📅 Today: ${Utilities.formatDate(today, CONFIG.TIMEZONE, 'EEEE, MMMM dd, yyyy')}`);
  console.log(`📅 Upcoming Monday: ${Utilities.formatDate(upcomingMonday, CONFIG.TIMEZONE, 'EEEE, MMMM dd, yyyy')}`);
  console.log(`🧪 Testing GitHub access for folder: ${folderName}`);

  const emails = fetchSportsEmails(folderName);

  console.log('Middle School email found:', !!emails.middleSchool);
  console.log('Upper School email found:', !!emails.upperSchool);

  if (emails.middleSchool) {
    console.log('Middle School email length:', emails.middleSchool.length, 'characters');
  }
  if (emails.upperSchool) {
    console.log('Upper School email length:', emails.upperSchool.length, 'characters');
  }
}
