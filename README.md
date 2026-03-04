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
├── digital-signage/                    # Digital signage automation (NEW!)
│   ├── generate_signage.py             # Daily signage generator
│   ├── index.html                      # Auto-updated daily display
│   └── README.md                       # Digital signage documentation
│
├── instagram-poster/                   # Instagram daily carousel generator (NEW!)
│   ├── app.py                          # Local web app (fetch + custom events + export)
│   ├── generate_instagram_poster.py    # CLI daily carousel generator script
│   ├── poster_generator.py             # Shared carousel layout/data logic
│   └── README.md                       # Instagram carousel documentation
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
│   ├── generate-sports-emails.yml      # Weekly email generation (Sundays 3PM)
│   └── update-signage.yml              # Daily signage updates (Midnight MT)
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

## 🖥️ Digital Signage (NEW!)

**Automated daily digital signage** for displays around school:
- **Midnight MT**: GitHub Actions generates today's events display
- **Auto-deploy**: Cloudflare Pages serves updated HTML automatically

**Features:**
- Shows today's sports games and arts events
- Card-based design similar to email styling
- Optimized for 2500x1650px displays
- Featured events (varsity games, arts events) highlighted
- Updates automatically every day at midnight Denver time

**Setup:** See [digital-signage/README.md](digital-signage/README.md)

## 📱 Instagram Daily Carousel (NEW!)

**Daily carousel generation** for Instagram feed posts (4:5 portrait, `1080x1350` per slide):
- Pulls events from the same athletics + arts sources used by sports emails
- Supports custom added events (robotics, admissions, speech & debate, etc.)
- Generates one day-focused slide per day in the selected week/range
- Exports current slide or all slides from a local web GUI

**Setup:** See [instagram-poster/README.md](instagram-poster/README.md)

## 📧 Manual Generation

### Sports Emails
```bash
cd sports-emails
python generate_games.py                    # Next week
python generate_games.py --this-week        # Current week
python generate_games.py --start-date 2025-10-06 --end-date 2025-10-12
```

### Digital Signage
```bash
cd digital-signage
python3 generate_signage.py                 # Generate today's display
```

### Instagram Carousel
```bash
cd instagram-poster
python3 app.py                              # Launch carousel GUI at http://127.0.0.1:5050
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
- **[digital-signage/README.md](digital-signage/README.md)** - Digital signage setup and usage
- **[google-apps-script/](google-apps-script/)** - Email sending scripts (.gs files)

## 🛠️ Technologies

- **Python 3.11+** - Email generation, web scraping, and signage generation
- **GitHub Actions** - Automated scheduling (emails + signage)
- **Google Apps Script** - Email distribution via Gmail
- **Cloudflare Pages** - Digital signage hosting and deployment
- **HTML/CSS** - Email templates and signage displays

## 👤 Author

**Jacob Barkin** (jbarkin28@kentdenver.org)  
Student Leadership Media Team

---

**Last Updated:** November 2025
