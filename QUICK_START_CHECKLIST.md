# 🚀 Quick Start Checklist - Sports Email Automation

## ✅ What I've Done For You

I've created a complete automation system with these files:

1. **`.github/workflows/generate-sports-emails.yml`** - GitHub Actions workflow
2. **`google-apps-script/sports-email-sender.js`** - Main Google Apps Script code
3. **`google-apps-script/troubleshooting-functions.js`** - Debugging tools
4. **`AUTOMATION_SETUP_GUIDE.md`** - Detailed setup instructions

## 🎯 What You Need To Do

### Step 1: Test GitHub Actions (5 minutes)
1. Go to your GitHub repository
2. Click **Actions** tab
3. Click **"Generate Sports Emails"** workflow
4. Click **"Run workflow"** → **"Run workflow"** (green button)
5. Wait for it to complete (should be green checkmark)
6. Verify new HTML files were created in `sports-emails/` folder

### Step 2: Set Up Google Apps Script (10 minutes)
1. Go to [script.google.com](https://script.google.com)
2. Click **"New Project"**
3. Name it "Kent Denver Sports Email Sender"
4. Replace default code with contents of `google-apps-script/sports-email-sender.js`
5. **IMPORTANT**: Update email addresses in the `EMAIL_RECIPIENTS` section:
   ```javascript
   EMAIL_RECIPIENTS: {
     MIDDLE_SCHOOL: [
       'your-middle-school-list@kentdenver.org',
       // Add actual email addresses here
     ],
     UPPER_SCHOOL: [
       'your-upper-school-list@kentdenver.org', 
       // Add actual email addresses here
     ]
   }
   ```
6. Save the project (Ctrl+S)

### Step 3: Test Google Apps Script (5 minutes)
1. Select `testGitHubAccess` from function dropdown
2. Click **Run** (authorize permissions when prompted)
3. Check logs - should show it found HTML files
4. Select `sendTestEmail` from function dropdown  
5. Click **Run** - you should receive a test email

### Step 4: Set Up Automatic Triggers (2 minutes)
1. Select `setupTriggers` from function dropdown
2. Click **Run**
3. This sets up Sunday 4:00 PM automatic sending

### Step 5: Final Test (3 minutes)
1. Select `simulateEmailSending` from function dropdown
2. Click **Run**
3. Check logs to see what would be sent (without actually sending)

## 🎉 You're Done!

The system will now:
- **Every Sunday 3:00 PM**: Generate HTML files automatically
- **Every Sunday 4:00 PM**: Send emails automatically

## 🔧 Quick Customizations

### Change Email Subject Lines
In Google Apps Script, find these lines and modify:
```javascript
'Kent Denver Middle School Games This Week',
'Kent Denver Upper School Games This Week',
```

### Change Timezone
If you're not in Mountain Time, edit the GitHub Actions file:
- **Eastern Time**: Change `'0 22 * * 0'` to `'0 20 * * 0'`
- **Pacific Time**: Change `'0 22 * * 0'` to `'0 23 * * 0'`

### Add Error Notifications
Update this line in Google Apps Script:
```javascript
const adminEmail = 'your-email@kentdenver.org';
```

## 🚨 Troubleshooting

### If GitHub Actions Fails:
- Check the **Actions** tab for error details
- Make sure your Python script works manually
- Verify the athletics website is accessible

### If Google Apps Script Fails:
- Use the troubleshooting functions I created
- Check **Executions** tab in Apps Script for error logs
- Run `debugGitHubAccess()` to test file fetching

### If Emails Don't Send:
- Check Gmail quota (100 emails/day for personal accounts)
- Verify email addresses are correct
- Run `sendTestEmail()` to test basic email functionality

## 📞 Need Help?

1. **Check the logs**: Both GitHub Actions and Google Apps Script have detailed logs
2. **Use debug functions**: Run the troubleshooting functions I created
3. **Test manually**: Use `sendSportsEmailsManual()` to test outside the schedule

## 🎯 Success Indicators

You'll know it's working when:
- ✅ GitHub Actions runs successfully every Sunday at 3:00 PM
- ✅ New HTML files appear in your repository
- ✅ Google Apps Script runs successfully every Sunday at 4:00 PM  
- ✅ Recipients receive the sports emails
- ✅ You get error notifications if something breaks

---

**Time to set up**: ~25 minutes  
**Time saved per week**: ~30 minutes  
**Return on investment**: Immediate! 🎉
