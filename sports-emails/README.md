# Kent Denver Games Email Generator

This script automatically scrapes the Kent Denver athletics website and generates **two separate** weekly games emails - one for Middle School and one for Upper School - with advanced game prioritization, dynamic content variations, and professional styling.

## Quick Start

**Super Easy Way (Default - Next Week):**
```bash
python generate_games.py
```
Creates folder `oct06/` with both email files inside.

**For Current Week:**
```bash
python generate_games.py --this-week
```

**For Custom Date Range:**
```bash
python generate_games.py --start-date "2025-09-29" --end-date "2025-10-05"
```

**Custom Output Directory:**
```bash
python generate_games.py --output-dir testing
```

All commands automatically create **organized folder structure** with descriptive names:
- `sep29/games-week-middle-school-sep29.html`
- `sep29/games-week-upper-school-sep29.html`

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

## Command Line Options

```
usage: generate_games.py [-h]
                         [--this-week | --next-week | --start-date START_DATE]
                         [--end-date END_DATE] [--output-dir OUTPUT_DIR]
                         [--output-ms OUTPUT_MS] [--output-us OUTPUT_US]

Generate Kent Denver weekly games emails

options:
  -h, --help            show this help message and exit
  --this-week           Generate emails for current week (Monday-Sunday)
  --next-week           Generate emails for next week (Monday-Sunday)
  --start-date START_DATE
                        Custom start date (YYYY-MM-DD). Requires --end-date
  --end-date END_DATE   Custom end date (YYYY-MM-DD). Requires --start-date
  --output-dir OUTPUT_DIR
                        Output directory for generated files (defaults to
                        auto-generated week folder)
  --output-ms OUTPUT_MS
                        Middle school output filename with path (auto-
                        generated in output directory if not specified)
  --output-us OUTPUT_US
                        Upper school output filename with path (auto-generated
                        in output directory if not specified)
```

### Examples

```bash
# Generate for next week in auto-created folder (e.g., oct06/)
python generate_games.py

# Generate for current week in auto-created folder (e.g., sep29/)
python generate_games.py --this-week

# Custom date range in auto-created folder (e.g., sep22/)
python generate_games.py --start-date 2025-09-22 --end-date 2025-09-27

# Custom output directory
python generate_games.py --output-dir testing

# Custom filenames (still creates folder structure)
python generate_games.py --output-ms "special-ms.html" --output-us "special-us.html"
```

## ✨ Key Features

### 🎯 **Game Prioritization System**
- **Featured Games**: Large cards with enhanced styling for home games and varsity games
- **Other Games**: Compact list format for away JV/C Team games
- **Visual Hierarchy**: Clear distinction between important and secondary games
- **Smart Categorization**: Upper School prioritizes home OR varsity, Middle School prioritizes home only

### 🔄 **Dynamic Content Variations**
- **Fresh Content Every Week**: 12 different variations each for hero text, CTA text, and intro text
- **Synchronized Rotation**: All text components rotate together using ISO week numbers
- **Deterministic Selection**: Same week always produces same text combination
- **Additional Variations**: Title text, CTA button text, and CTA headers also rotate

### 🏠 **Enhanced Visual Styling**
- **Home + Varsity Games**: Gradient borders (green→yellow), enhanced shadows, special badges
- **Home Games**: Thick green borders, enhanced shadows, "HOME" badge
- **Varsity Games**: Thick yellow borders, enhanced shadows, "VARSITY" badge
- **Sport-Specific Colors**: Each sport retains its unique color for the top accent bar

### 📱 **Professional Design**
- **Mobile-First**: Enhanced responsive breakpoints and mobile-specific styling
- **Email-Safe CSS**: Table-based layouts with email client compatibility
- **Organized Folder Structure**: Automatic weekly folder creation (e.g., `sep29/`, `oct06/`)
- **Missing Day Detection**: Shows "No games scheduled" for missing weekdays

## 🔧 How It Works

1. **Scrapes** the Kent Denver athletics website for games in your date range
2. **Separates** games into Middle School and Upper School based on team names
3. **Categorizes** games into Featured (home/varsity) vs Other (away JV/C Team)
4. **Applies** dynamic text variations based on ISO week number
5. **Organizes** games by day with proper date formatting and missing day detection
6. **Applies** sport-specific styling with enhanced visual hierarchy
7. **Generates** two complete HTML emails with professional responsive design
8. **Creates** organized folder structure for easy management

## 📊 Game Categorization Logic

### School Level Separation
- **Middle School**: Games with team names containing "Middle School", "MS", "6th", "7th", "8th", "sixth", "seventh", or "eighth"
- **Upper School**: All other games (JV, Varsity, C Team, etc.)

### Priority Classification
- **Upper School Featured**: Home games OR Varsity games (gets large cards)
- **Upper School Other**: Away JV/C Team games (gets compact list)
- **Middle School Featured**: Home games only (gets large cards)
- **Middle School Other**: Away games (gets compact list)

### Varsity Detection
Automatically detects varsity games by checking for:
- "Varsity" in team name
- "V " prefix (e.g., "V Soccer")
- Absence of "JV", "C Team", "Middle School" indicators

## 🎨 Visual Design System

### Sport Colors & Emojis
The script automatically assigns colors and emojis based on sport:

- ⚽ Soccer: Green (#22c55e)
- 🏈 Football: Red (#dc2626)
- 🎾 Tennis: Cyan (#06b6d4)
- ⛳ Golf: Yellow (#eab308)
- 🏃 Cross Country: Purple (#8b5cf6)
- 🏑 Field Hockey: Pink (#ec4899)
- 🏐 Volleyball: Orange (#f97316)
- 🏀 Basketball: Orange (#f97316)
- 🏊 Swimming: Blue (#3b82f6)
- 🤸 Gymnastics: Purple (#8b5cf6)
- And more...

### Enhanced Game Cards
- **Featured Games**: Large cards with sport-specific top accent + priority borders
- **Home + Varsity**: Gradient borders (green→yellow) with "HOME • VARSITY" badge
- **Home Only**: Green borders with "HOME" badge
- **Varsity Only**: Yellow borders with "VARSITY" badge
- **Other Games**: Compact single-row list format with full-width layout

### Dynamic Text Variations (12 each)
- **Hero Text**: Main header content with sport count integration
- **CTA Text**: Call-to-action messaging encouraging attendance
- **Intro Text**: Introductory paragraph setting the tone
- **Title Text**: Main page title variations ("Games This Week", "Sun Devil Athletics", etc.)
- **CTA Button**: Button text variations ("Support Our Teams", "Show Your Spirit", etc.)
- **CTA Header**: Motivational headers ("Go Sun Devils!", "Sun Devil Pride!", etc.)

## Email Client Compatibility

The generated emails are optimized for maximum compatibility across email clients:

- **Desktop**: Outlook 2016+, Apple Mail, Thunderbird, Gmail web
- **Mobile**: iOS Mail, Android Gmail, Outlook mobile
- **Web**: Gmail, Outlook.com, Yahoo Mail, Apple iCloud Mail

**Email-Friendly Features:**
- XHTML 1.0 Transitional DOCTYPE for maximum compatibility
- Table-based layouts instead of flexbox/grid
- Inline CSS with MSO (Microsoft Outlook) specific styles
- Conservative border-radius values (4px-8px)
- Proper font fallbacks for web fonts
- Mobile-responsive design with media queries
- Dark mode support where available

## Troubleshooting

If the script doesn't find any games:
1. Check that the date range is correct
2. Verify the Kent Denver athletics website is accessible
3. The website structure may have changed - you may need to update the scraping logic

If emails don't display correctly:
1. Test in multiple email clients (Gmail, Outlook, Apple Mail)
2. Check that images and fonts are loading properly
3. Verify the HTML validates as XHTML 1.0 Transitional

## 📁 File Structure

```
sports-emails/
├── generate_games.py      # Main script with all functionality
├── requirements.txt       # Python dependencies
├── README.md             # This documentation
├── .gitignore           # Git ignore file for test folders
├── sep29/               # Auto-generated weekly folders
│   ├── games-week-middle-school-sep29.html
│   └── games-week-upper-school-sep29.html
└── oct06/
    ├── games-week-middle-school-oct06.html
    └── games-week-upper-school-oct06.html
```

## 📧 Email Output Features

The script generates professional HTML emails with:

### Content Structure
- **Dynamic hero section** with rotating titles and messaging
- **Featured game cards** with enhanced styling for priority games
- **Compact game lists** for secondary games with full-width layout
- **Missing day detection** showing "No games scheduled" when appropriate
- **Smart section titles** ("Games" vs "Other Games" based on context)

### Technical Features
- **Email client compatibility** across desktop, mobile, and web clients
- **Responsive design** with mobile-first breakpoints
- **Sport-specific styling** with consistent color schemes
- **Professional typography** using Red Hat Text and Crimson Pro fonts
- **Accessibility features** with proper semantic HTML structure

## Support

For questions, issues, or feature requests, contact:
- **Primary Support**: jbarkin28@kentdenver.org
- **App Development Team**: appdev@kentdenver.org

## Credits

**Designed and developed by [Jacob Barkin](https://jacobbarkin.com)**

This automated email generator was created to streamline the weekly games email process for Kent Denver School's Student Leadership Media Team.
