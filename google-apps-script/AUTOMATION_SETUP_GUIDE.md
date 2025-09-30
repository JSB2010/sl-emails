# 🏈 Sports Email Automation Setup Guide

Complete automation system that generates and sends sports emails every Sunday.

## 📋 Overview

**Sunday 3:00 PM (Mountain Time)**: GitHub Actions generates HTML files and commits them
**Sunday 4:00 PM (Mountain Time)**: Google Apps Script fetches files and sends emails

## 📅 How Week Selection Works

The system generates emails for the **next occurring Monday**:
- **Sep 29 (Mon) - Oct 5 (Sun)**: Generates emails for week of Oct 6
- **Oct 6 (Mon)**: Still generates for Oct 6 (gives flexibility for manual reruns)
- **Oct 7 (Tue) - Oct 12 (Sun)**: Generates emails for week of Oct 13

## 🚀 Quick Start (25 minutes total)

### Step 1: Enable GitHub Actions & Test (5 min)
1. Go to your repository → **Settings** → **Actions** → **General**
2. Under **Workflow permissions**, select **"Read and write permissions"**
3. Click **Save**
4. Go to **Actions** tab → **"Generate Sports Emails"** workflow
5. Click **"Run workflow"** → **"Run workflow"** (green button)
6. Wait for green checkmark
7. Verify new HTML files in `sports-emails/` folder

### Step 2: Set Up Google Apps Script (10 min)
1. Go to [script.google.com](https://script.google.com)
2. Click **"New Project"** → Name it "Kent Denver Sports Email Sender"
3. Delete default code
4. Copy entire contents of `google-apps-script/sports-email-sender.js`
5. Paste into Code.gs and **Save** (Ctrl+S)
6. **IMPORTANT**: Update email recipients in the `EMAIL_RECIPIENTS` section:

```javascript
EMAIL_RECIPIENTS: {
  MIDDLE_SCHOOL: ['your-email@kentdenver.org'],
  UPPER_SCHOOL: ['your-email@kentdenver.org']
}
```

### Step 3: Test & Enable Automation (5 min)
1. Select `testGitHubAccess` from function dropdown → **Run** (authorize when prompted)
2. Check logs - should find both HTML files
3. Select `sendTestEmail` → **Run** (check your inbox)
4. Select `setupTriggers` → **Run** (enables Sunday 4:00 PM automation)

### Step 4: Done! ✅
The system will now run automatically every Sunday at 3:00 PM (generate) and 4:00 PM (send).

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
