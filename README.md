# Kent Denver Student Leadership Emails

Automated email generation and distribution system for Kent Denver School athletics and events.

## 📁 Repository Structure

```
sl-emails/
├── sports-emails/                      # Sports email automation
│   ├── generate_games.py               # Python script to scrape and generate emails
│   ├── requirements.txt                # Python dependencies
│   ├── README.md                       # Sports email documentation
│   └── [week folders]/                 # Generated HTML files (e.g., sep29/, sep22/)
│
├── homecoming-week/                    # Homecoming event emails
│   ├── homecoming-ms.html              # Middle school homecoming email
│   ├── homecoming-us.html              # Upper school homecoming email
│   └── pep-rally.html                  # Pep rally email
│
├── google-apps-script/                 # Google Apps Script for email sending
│   ├── sports-email-sender.gs          # Main automation script
│   └── troubleshooting-functions.gs    # Debug utilities
│
├── .github/workflows/                  # GitHub Actions automation
│   └── generate-sports-emails.yml      # Weekly email generation (Sundays 3PM)
│
├── README.md                           # This file
└── SETUP.md                            # Complete setup instructions

```

## 🏈 Sports Email Automation

**Automated weekly sports emails** sent every Sunday:
- **3:00 PM MT**: GitHub Actions generates HTML files from athletics website
- **4:00 PM MT**: Google Apps Script sends emails to recipients

**Features:**
- Automatic game scraping from Kent Denver athletics website
- Prioritized display (home games, varsity games)
- Sport-specific styling and emojis (UTF-8 encoded)
- Mobile-responsive design
- Separate emails for Middle School and Upper School
- Auto-generated subject lines with date ranges
- BCC delivery to protect student privacy

**Setup:** See [SETUP.md](SETUP.md)

## 📧 Manual Email Generation

### Sports Emails
```bash
cd sports-emails
python generate_games.py                    # Next week
python generate_games.py --this-week        # Current week
python generate_games.py --start-date 2025-10-06 --end-date 2025-10-12
```

### Homecoming Emails
Pre-generated HTML files in `homecoming-week/` - ready to copy and send.

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/JSB2010/sl-emails.git
   cd sl-emails
   ```

2. **Set up sports email automation**
   - Follow [SETUP.md](SETUP.md)
   - Takes ~20 minutes total

3. **Generate emails manually** (optional)
   ```bash
   cd sports-emails
   pip install -r requirements.txt
   python generate_games.py
   ```

## 🎨 Email Design

All emails follow Kent Denver branding:
- **Colors**: KDS Blue (#041e42), KDS Red (#a11919)
- **Fonts**: Red Hat Text (body), Crimson Pro (headers)
- **Style**: Professional, mobile-responsive, email-client compatible

## 📝 Documentation

- **[SETUP.md](SETUP.md)** - Complete automation setup guide
- **[sports-emails/README.md](sports-emails/README.md)** - Sports email generator details
- **[google-apps-script/](google-apps-script/)** - Email sending scripts (.gs files)

## 🛠️ Technologies

- **Python 3.11+** - Email generation and web scraping
- **GitHub Actions** - Automated scheduling
- **Google Apps Script** - Email distribution via Gmail
- **HTML/CSS** - Email templates

## 👤 Author

**Jacob Barkin** (jbarkin28@kentdenver.org)  
Student Leadership Media Team

---

**Last Updated:** September 2025
