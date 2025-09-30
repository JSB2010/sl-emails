# 🏈 Sports Email Automation Setup Guide

This guide will help you set up the complete automation system that generates and sends sports emails every Sunday.

## 📋 Overview

**Sunday 3:00 PM (Mountain Time)**: GitHub Actions runs your Python script and commits HTML files  
**Sunday 4:00 PM (Mountain Time)**: Google Apps Script fetches the files and sends emails

## 🚀 Part 1: GitHub Actions Setup

### Step 1: Enable GitHub Actions
1. Go to your repository on GitHub
2. Click on the **Actions** tab
3. If Actions are disabled, click **"I understand my workflows, go ahead and enable them"**

### Step 2: Test the Workflow
The workflow file has already been created at `.github/workflows/generate-sports-emails.yml`

**To test it manually:**
1. Go to **Actions** tab in your GitHub repository
2. Click on **"Generate Sports Emails"** workflow
3. Click **"Run workflow"** button
4. Click the green **"Run workflow"** button to start it

### Step 3: Verify It Works
After running the workflow:
1. Check that new HTML files were created in the `sports-emails/` folder
2. Look for a new commit with message like "🏈 Auto-generate sports emails for week of..."
3. The workflow will automatically run every Sunday at 3:00 PM Mountain Time

## 📧 Part 2: Google Apps Script Setup

### Step 1: Create New Apps Script Project
1. Go to [script.google.com](https://script.google.com)
2. Click **"New Project"**
3. Name it "Kent Denver Sports Email Sender"

### Step 2: Add the Code
1. Delete the default `myFunction()` code
2. Copy the entire contents of `google-apps-script/sports-email-sender.js`
3. Paste it into the Code.gs file
4. Click **Save** (Ctrl+S)

### Step 3: Configure Email Recipients
In the code, find the `EMAIL_RECIPIENTS` section and update with real email addresses:

```javascript
EMAIL_RECIPIENTS: {
  MIDDLE_SCHOOL: [
    'middle-school-athletics@kentdenver.org',
    'coach1@kentdenver.org',
    // Add more recipients
  ],
  UPPER_SCHOOL: [
    'upper-school-athletics@kentdenver.org', 
    'coach2@kentdenver.org',
    // Add more recipients
  ]
}
```

### Step 4: Test the Script
1. In the Apps Script editor, select `testGitHubAccess` from the function dropdown
2. Click **Run** (you'll need to authorize permissions)
3. Check the **Execution transcript** to see if it can fetch files from GitHub

### Step 5: Set Up the Trigger
1. In the Apps Script editor, select `setupTriggers` from the function dropdown
2. Click **Run**
3. This creates a trigger to run every Sunday at 4:00 PM

### Step 6: Test Email Sending
1. Select `sendSportsEmailsManual` from the function dropdown
2. Click **Run**
3. Check that emails are sent successfully

## ⚙️ Configuration Options

### Timezone Adjustment
The GitHub Actions workflow is set for **Mountain Time**. If you're in a different timezone:

1. Edit `.github/workflows/generate-sports-emails.yml`
2. Change the cron schedule:
   - Current: `'0 22 * * 0'` (3:00 PM Mountain = 10:00 PM UTC)
   - For Eastern Time: `'0 20 * * 0'` (3:00 PM Eastern = 8:00 PM UTC)
   - For Pacific Time: `'0 23 * * 0'` (3:00 PM Pacific = 11:00 PM UTC)

### Email Customization
In the Google Apps Script, you can customize:
- **Subject lines**: Update the subject in `sendEmailToRecipients` calls
- **From name**: Change `EMAIL_FROM_NAME` in CONFIG
- **Reply-to address**: Update `replyTo` in the email options

## 🔍 Monitoring & Troubleshooting

### GitHub Actions Monitoring
1. Go to **Actions** tab in your repository
2. Click on any workflow run to see details
3. Green checkmark = success, red X = failure
4. Click on failed runs to see error details

### Google Apps Script Monitoring
1. In Apps Script editor, go to **Executions** (left sidebar)
2. See all recent runs and their status
3. Click on any execution to see detailed logs

### Common Issues & Solutions

**GitHub Actions Issues:**
- **No games found**: Check if Kent Denver athletics website is accessible
- **Permission denied**: Make sure repository has Actions enabled
- **Python errors**: Check if `requirements.txt` has all needed packages

**Google Apps Script Issues:**
- **File not found**: GitHub Actions might not have run yet, or files weren't generated
- **Gmail quota exceeded**: You can send 100 emails/day (consumer) or 1,500/day (Workspace)
- **Authorization errors**: Re-run the authorization process

## 📊 Optional: Email Activity Logging

To track email sending history:

1. Create a new Google Sheet
2. Add headers: Date, Status, Message, Week Folder
3. Copy the sheet ID from the URL
4. In the Apps Script, uncomment the logging section in `logEmailActivity()`
5. Replace `YOUR_SPREADSHEET_ID_HERE` with your sheet ID

## 🚨 Error Notifications

The system will email you if something goes wrong. Update the admin email:

```javascript
const adminEmail = 'your-email@kentdenver.org';
```

## 🧪 Testing Checklist

Before going live:

- [ ] GitHub Actions workflow runs successfully
- [ ] HTML files are generated and committed
- [ ] Google Apps Script can fetch files from GitHub
- [ ] Test emails are sent successfully
- [ ] Email recipients are correct
- [ ] Triggers are set up for Sunday 4:00 PM
- [ ] Error notifications work

## 📅 Going Live

Once everything is tested:

1. The GitHub Actions will automatically run every Sunday at 3:00 PM
2. The Google Apps Script will automatically run every Sunday at 4:00 PM
3. You'll receive error notifications if anything fails
4. Check the logs periodically to ensure everything is working

## 🛠️ Manual Override

If you need to send emails manually:
1. Go to your Apps Script project
2. Select `sendSportsEmailsManual` function
3. Click **Run**

If you need to generate files manually:
1. Go to GitHub Actions
2. Click "Run workflow" on the "Generate Sports Emails" workflow

---

**Need help?** Check the execution logs in both GitHub Actions and Google Apps Script for detailed error messages.
