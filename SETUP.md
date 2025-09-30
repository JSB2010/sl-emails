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
4. Copy entire contents of `google-apps-script/sports-email-sender.gs`
5. Paste into Code.gs and **Save** (Ctrl+S)
6. **Email recipients are already configured:**
   - Middle School: `allmiddleschoolstudents@kentdenver.org`
   - Upper School: `allupperschoolstudents@kentdenver.org`
   - Emails are sent as BCC to protect privacy
   - From name: "Student Leadership"

### Step 3: Test & Enable Automation (5 min)
1. Select `testGitHubAccess` from function dropdown → **Run** (authorize when prompted)
2. Check logs - should find both HTML files with correct subjects
3. Select `sendTestEmail` → **Run** (check your inbox - emojis should display correctly!)
4. **IMPORTANT**: Select `setupTriggers` → **Run** (enables Sunday 4:00 PM automation)

### Step 4: Done! ✅
- ✅ GitHub Actions cron job: Already configured (Sundays 3:00 PM MT)
- ✅ Google Apps Script trigger: Set up when you ran `setupTriggers()`
- ✅ Email recipients: Configured for all students
- ✅ Subject line: Auto-generated with date range
- ✅ From name: "Student Leadership"

The system will now run automatically every Sunday!

## ⚙️ Configuration Options

### Timezone Adjustment
The GitHub Actions workflow is set for **Mountain Time**. If you're in a different timezone:

1. Edit `.github/workflows/generate-sports-emails.yml`
2. Change the cron schedule:
   - Current: `'0 22 * * 0'` (3:00 PM Mountain = 10:00 PM UTC)
   - For Eastern Time: `'0 20 * * 0'` (3:00 PM Eastern = 8:00 PM UTC)
   - For Pacific Time: `'0 23 * * 0'` (3:00 PM Pacific = 11:00 PM UTC)

### Email Configuration
Current settings:
- **Subject line**: Auto-generated as "Games This Week: {date range}" from HTML title
- **From name**: "Student Leadership" (configured in CONFIG)
- **Recipients**:
  - Middle School: `allmiddleschoolstudents@kentdenver.org`
  - Upper School: `allupperschoolstudents@kentdenver.org`
- **BCC**: Can add additional recipients in `EMAIL_RECIPIENTS.bcc` array
- **Reply-to**: `noreply@kentdenver.org`

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
- **Permission denied**: Make sure repository has Actions enabled and write permissions
- **Python errors**: Check if `requirements.txt` has all needed packages

**Google Apps Script Issues:**
- **File not found**: GitHub Actions might not have run yet, or files weren't generated
- **Gmail quota exceeded**: You can send 100 emails/day (consumer) or 1,500/day (Workspace)
- **Authorization errors**: Re-run the authorization process
- **Emojis showing as ������**: FIXED! The script now uses `MailApp` with UTF-8 encoding

### Emoji Fix Details
The emoji corruption issue was caused by character encoding problems. The fix:
- Changed from `GmailApp.sendEmail()` to `MailApp.sendEmail()`
- Added explicit `charset: 'UTF-8'` parameter
- Fetch GitHub files with UTF-8 encoding: `response.getContentText('UTF-8')`

## 📊 Optional: Email Activity Logging

To track email sending history:

1. Create a new Google Sheet
2. Add headers: Date, Status, Message, Week Folder
3. Copy the sheet ID from the URL
4. In the Apps Script, uncomment the logging section in `logEmailActivity()`
5. Replace `YOUR_SPREADSHEET_ID_HERE` with your sheet ID

## 🚨 Error Notifications

The system will email you if something goes wrong. The admin email is already set to `jbarkin28@kentdenver.org`.

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
