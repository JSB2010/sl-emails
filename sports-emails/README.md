# Kent Denver Games Email Generator

This script automatically scrapes the Kent Denver athletics website and generates **two separate** weekly games emails - one for Middle School and one for Upper School - with the same styling and layout as your existing `games-week.html` template.

## Quick Start

**Super Easy Way (Default - Next Week):**
```bash
python generate_games.py
```

**For Current Week:**
```bash
python generate_games.py --this-week
```

**For Next Week (Explicit):**
```bash
python generate_games.py --next-week
```

**For Custom Date Range:**
```bash
python generate_games.py --start-date "2025-09-29" --end-date "2025-10-05"
```

All commands automatically create **two files** with descriptive names like:
- `games-week-middle-school-sep22.html`
- `games-week-upper-school-sep22.html`

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage Options

### Quick Options (Most Common)
- **No arguments**: Generates emails for next week (Monday-Sunday)
- `--this-week`: Generates emails for current week (Monday-Sunday)  
- `--next-week`: Generates emails for next week (Monday-Sunday) - same as default

### Custom Options
- `--start-date YYYY-MM-DD --end-date YYYY-MM-DD`: Custom date range
- `--output-ms FILENAME`: Custom middle school filename (auto-generated if not specified)
- `--output-us FILENAME`: Custom upper school filename (auto-generated if not specified)

### Examples

```bash
# Generate for next week (default)
python generate_games.py

# Generate for current week  
python generate_games.py --this-week

# Custom date range
python generate_games.py --start-date "2025-09-29" --end-date "2025-10-05"

# Custom date range with custom filenames
python generate_games.py --start-date "2025-09-29" --end-date "2025-10-05" --output-ms "homecoming-ms.html" --output-us "homecoming-us.html"
```

## Features

- **Separate emails**: Automatically generates Middle School and Upper School emails
- **Smart game sorting**: Games with "Middle School", "6th", "7th", or "8th" go to MS email, all others to US
- **Home game emphasis**: Home games are highlighted with bold text, home icon (🏠), and green border
- **Automatic scraping**: Pulls game data directly from the Kent Denver athletics website
- **Exact styling**: Uses the same colors, fonts, and layout as your existing template
- **Sport-specific styling**: Each sport gets its own emoji and color scheme
- **Responsive design**: Works on both desktop and mobile
- **Date formatting**: Automatically formats date ranges (e.g., "September 22–28, 2025")

## How It Works

1. **Scrapes** the Kent Denver athletics website for games in your date range
2. **Separates** games into Middle School and Upper School based on team names
3. **Emphasizes** home games with bold text, home icon (🏠), and green borders
4. **Organizes** games by day with proper date formatting and calendar icons (📅)
5. **Applies** sport-specific styling (soccer = green, football = red, tennis = cyan, etc.)
6. **Generates** two complete HTML emails with the exact same styling as your original
7. **Creates** responsive cards that look great on all devices

## Game Separation Logic

- **Middle School**: Games with team names containing "Middle School", "MS", "6th", "7th", "8th", "sixth", "seventh", or "eighth"
- **Upper School**: All other games (JV, Varsity, C Team, etc.)

## Home Game Emphasis

Home games are visually emphasized with:
- **Extra bold team name** (font-weight: 900 vs 800)
- **Home icon** (🏠) next to the team name
- **Green border** around the game card
- **Green badge** for the time/location

## Sport Colors & Emojis

The script automatically assigns colors and emojis based on sport:

- ⚽ Soccer: Green gradient
- 🏈 Football: Red gradient  
- 🎾 Tennis: Cyan gradient
- ⛳ Golf: Yellow gradient
- 🏃 Cross Country: Purple gradient
- 🏑 Field Hockey: Pink gradient
- 🏐 Volleyball: Orange gradient
- And more...

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

## Files Included

- `generate_games.py` - Main script with all functionality
- `requirements.txt` - Python dependencies
- `games-week.html` - Original template for reference
- `README.md` - This documentation

## Output

The script generates professional HTML emails that are identical to your hand-crafted version but with live data from the athletics website. Each email includes:

- Hero section with school-specific title
- Game cards organized by day with calendar icons
- Sport-specific colors and emojis
- Home game emphasis with visual indicators
- Complete footer with call-to-action
- Responsive design for all devices

## Support

For questions, issues, or feature requests, contact:
- **Primary Support**: jbarkin28@kentdenver.org
- **App Development Team**: appdev@kentdenver.org

## Credits

**Designed and developed by [Jacob Barkin](https://jacobbarkin.com)**

This automated email generator was created to streamline the weekly games email process for Kent Denver School's Student Leadership Media Team.
