#!/usr/bin/env python3
"""
Kent Denver Digital Signage Generator

Generates a daily HTML display (2500x1650px) showing today's games and performances
for digital signage around the school.

Features:
- Fetches today's sports games and arts events
- Displays in card format similar to email design
- Updates daily via GitHub Actions
- Optimized for 2500x1650px displays

Usage:
    python generate_signage.py                    # Generate for today
    python generate_signage.py --date 2025-11-08  # Generate for specific date

Author: Jacob Barkin (jbarkin28@kentdenver.org)
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import sys
import os
import argparse
from typing import List, Dict, Union
from icalendar import Calendar

# Add parent directory to path to import from sports-emails
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sports-emails'))
from generate_games import (
    Game, Event, SPORT_CONFIG, ARTS_CONFIG,
    scrape_athletics_schedule, fetch_arts_events,
    is_varsity_game, is_middle_school_game
)

def get_date_range(date_str=None):
    """Get date in the format needed for fetching

    Args:
        date_str: Optional date string in YYYY-MM-DD format. If None, uses today.
    """
    if date_str:
        # Validate and use provided date
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            print(f"❌ Invalid date format: {date_str}")
            print("   Please use YYYY-MM-DD format (e.g., 2025-11-08)")
            sys.exit(1)
    else:
        target_date = datetime.now()

    date_str = target_date.strftime('%Y-%m-%d')
    return date_str, date_str, target_date

def fetch_events_for_date(date_str=None):
    """Fetch all games and events for the specified date

    Args:
        date_str: Optional date string in YYYY-MM-DD format. If None, uses today.
    """
    start_date, end_date, target_date = get_date_range(date_str)

    print(f"🔍 Fetching events for {start_date} ({target_date.strftime('%A, %B %d, %Y')})...")

    # Fetch sports games
    games = scrape_athletics_schedule(start_date, end_date)
    print(f"✅ Found {len(games)} sports games")

    # Fetch arts events
    arts_events = fetch_arts_events(start_date, end_date)
    print(f"✅ Found {len(arts_events)} arts events")

    # Combine all events
    all_events = games + arts_events
    print(f"📊 Total: {len(all_events)} events")

    return all_events, target_date

def categorize_events(events: List[Union[Game, Event]]):
    """Categorize events into featured and regular"""
    featured = []
    regular = []
    
    for event in events:
        if event.event_type == 'arts':
            # All arts events are featured
            featured.append(event)
        elif event.event_type == 'game':
            # Varsity games are featured
            if is_varsity_game(event.team):
                featured.append(event)
            else:
                regular.append(event)
    
    return featured, regular

def get_layout_config(total_events: int) -> dict:
    """Get optimal layout configuration based on number of events

    Returns dict with: card_size, grid_layout, section_title_size, card_height
    """
    # Screen is 2500x1650px
    # Header ~200px, Footer ~70px, Content padding ~120px
    # Available content height: ~1260px

    if total_events == 1:
        # Use same sizing as 2 events to avoid card being too large
        return {
            "emoji_size": "88px",
            "title_size": "58px",
            "subtitle_size": "38px",
            "badge_size": "30px",
            "time_size": "48px",
            "padding": "70px 80px",
            "top_accent": "28px",
            "border_width": "4px",
            "margin": "30px",
            "grid_columns": "1fr",
            "section_title_size": "48px",
            "card_height": "auto"
        }
    elif total_events == 2:
        return {
            "emoji_size": "88px",
            "title_size": "58px",
            "subtitle_size": "38px",
            "badge_size": "30px",
            "time_size": "48px",
            "padding": "70px 80px",
            "top_accent": "28px",
            "border_width": "4px",
            "margin": "30px",
            "grid_columns": "1fr",
            "section_title_size": "48px",
            "card_height": "auto"
        }
    elif total_events == 3:
        return {
            "emoji_size": "80px",
            "title_size": "52px",
            "subtitle_size": "34px",
            "badge_size": "28px",
            "time_size": "42px",
            "padding": "60px 70px",
            "top_accent": "26px",
            "border_width": "4px",
            "margin": "25px",
            "grid_columns": "repeat(3, 1fr)",
            "section_title_size": "46px",
            "card_height": "auto"
        }
    elif total_events == 4:
        return {
            "emoji_size": "76px",
            "title_size": "50px",
            "subtitle_size": "34px",
            "badge_size": "28px",
            "time_size": "44px",
            "padding": "70px 70px",
            "top_accent": "26px",
            "border_width": "4px",
            "margin": "10px",
            "grid_columns": "repeat(2, 1fr)",
            "section_title_size": "46px",
            "card_height": "auto"
        }
    elif total_events == 5:
        return {
            "emoji_size": "70px",
            "title_size": "46px",
            "subtitle_size": "30px",
            "badge_size": "26px",
            "time_size": "40px",
            "padding": "55px 55px",
            "top_accent": "24px",
            "border_width": "4px",
            "margin": "10px",
            "grid_columns": "repeat(3, 1fr)",  # Will do 3+2 layout
            "section_title_size": "44px",
            "card_height": "auto"
        }
    elif total_events == 6:
        return {
            "emoji_size": "72px",
            "title_size": "48px",
            "subtitle_size": "32px",
            "badge_size": "26px",
            "time_size": "40px",
            "padding": "60px 50px",
            "top_accent": "24px",
            "border_width": "4px",
            "margin": "8px",
            "grid_columns": "repeat(3, 1fr)",  # 3x2 grid
            "section_title_size": "44px",
            "card_height": "auto"
        }
    elif total_events == 7:
        return {
            "emoji_size": "64px",
            "title_size": "42px",
            "subtitle_size": "28px",
            "badge_size": "24px",
            "time_size": "36px",
            "padding": "45px 45px",
            "top_accent": "20px",
            "border_width": "3px",
            "margin": "8px",
            "grid_columns": "repeat(4, 1fr)",  # Will do 4+3 layout
            "section_title_size": "40px",
            "card_height": "auto"
        }
    else:  # 8+ events
        return {
            "emoji_size": "60px",
            "title_size": "40px",
            "subtitle_size": "26px",
            "badge_size": "22px",
            "time_size": "34px",
            "padding": "40px 40px",
            "top_accent": "18px",
            "border_width": "3px",
            "margin": "6px",
            "grid_columns": "repeat(4, 1fr)",  # 4x2 grid
            "section_title_size": "38px",
            "card_height": "auto"
        }

def generate_event_card_html(event: Union[Game, Event], is_featured: bool = False, layout_config: dict = None) -> str:
    """Generate HTML for a single event card with dynamic sizing"""
    config = event.get_sport_config()

    if event.event_type == 'arts':
        badge_style = event.get_home_away_style()
        title = event.title
        subtitle = f"📍 {event.location}"
    else:
        badge_style = event.get_home_away_style()
        title = event.team
        subtitle = f"vs. {event.opponent} • 📍 {event.location}"

    # Use layout config
    emoji_size = layout_config["emoji_size"]
    title_size = layout_config["title_size"]
    subtitle_size = layout_config["subtitle_size"]
    badge_size = layout_config["badge_size"]
    time_size = layout_config["time_size"]
    padding = layout_config["padding"]
    top_accent = layout_config["top_accent"]
    border_width = layout_config["border_width"]
    margin = layout_config["margin"]

    card_style = f"border: {border_width} solid {config['border_color']}; box-shadow: 0 8px 24px rgba(0,0,0,0.15);"

    return f'''
    <div class="event-card" style="background: white; border-radius: 20px; {card_style} overflow: hidden; margin: {margin}; display: flex; flex-direction: column; height: 100%;">
      <div style="height: {top_accent}; background: {config['color']}; flex-shrink: 0;"></div>
      <div style="padding: {padding}; display: flex; flex-direction: column; flex: 1; justify-content: space-between;">
        <div style="display: flex; align-items: flex-start; flex: 1;">
          <span style="font-size: {emoji_size}; margin-right: 16px; line-height: 1;">{config['emoji']}</span>
          <div style="flex: 1; display: flex; flex-direction: column; justify-content: center;">
            <div style="color: #041e42; font-family: 'Crimson Pro', Georgia, serif; font-weight: 700; font-size: {title_size}; line-height: 1.2; margin-bottom: 12px;">{title}</div>
            <div style="color: #374151; font-family: 'Red Hat Text', Arial, sans-serif; font-size: {subtitle_size}; line-height: 1.4; font-weight: 500;">{subtitle}</div>
          </div>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 30px; flex-shrink: 0;">
          <div style="background: {badge_style['background']}; color: {badge_style['color']}; padding: 12px 24px; border-radius: 10px; font-family: 'Red Hat Text', Arial, sans-serif; font-weight: 700; font-size: {badge_size};">
            {badge_style['text']}
          </div>
          <div style="color: #041e42; font-family: 'Red Hat Text', Arial, sans-serif; font-weight: 700; font-size: {time_size};">
            🕐 {event.time}
          </div>
        </div>
      </div>
    </div>
    '''

def generate_signage_html(events: List[Union[Game, Event]], target_date: datetime = None) -> str:
    """Generate the complete HTML for digital signage

    Args:
        events: List of games and events to display
        target_date: The date to display. If None, uses current date.
    """
    if target_date is None:
        target_date = datetime.now()
    date_display = target_date.strftime('%A, %B %d, %Y')

    # Kent Denver logo URL
    logo_url = "https://cdn-assets-cloud.frontify.com/s3/frontify-cloud-files-us/eyJwYXRoIjoiZnJvbnRpZnlcL2FjY291bnRzXC9iNFwvNzU3NDlcL3Byb2plY3RzXC8xMDUwNjZcL2Fzc2V0c1wvYTNcLzY3NDA0OTZcLzlmYTY2NGYzZjhiOGI3YjY2ZDEwZDBkZGI5NjcxNmJmLTE2NTY4ODQyNjYucG5nIn0:frontify:0G-jY-31l0MCBnvlONY7KuK6-sTagdCay7zorKYJ6_o?width=1464&format=webp&quality=100"

    if not events:
        # No events today
        content_html = '''
        <div style="text-align: center; padding: 150px 60px;">
          <div style="font-size: 120px; margin-bottom: 40px;">📅</div>
          <h2 style="color: #041e42; font-family: 'Crimson Pro', Georgia, serif; font-size: 64px; margin: 0 0 30px 0; font-weight: 700;">No Events Today</h2>
          <p style="color: #6b7280; font-family: 'Red Hat Text', Arial, sans-serif; font-size: 36px; margin: 0; font-weight: 500;">Check back tomorrow for upcoming games and performances!</p>
        </div>
        '''
    else:
        # Get optimal layout configuration based on total number of events
        total_events = len(events)
        layout_config = get_layout_config(total_events)

        # Categorize events
        featured, regular = categorize_events(events)

        # Combine all events for unified layout
        all_events_list = featured + regular

        # Generate cards with optimized layout
        cards_html = ""

        # Section title
        section_title_size = layout_config["section_title_size"]
        grid_columns = layout_config["grid_columns"]

        # For better visual hierarchy, show "Today's Events" instead of separating featured/regular
        # This creates a cleaner, more unified display
        cards_html += f'<div style="flex: 1; display: flex; flex-direction: column;">'
        cards_html += f'<h3 style="color: #041e42; font-family: \'Crimson Pro\', Georgia, serif; font-size: {section_title_size}; margin: 0 0 20px 20px; font-weight: 700;">Today\'s Events</h3>'

        # Special layouts for specific counts
        if total_events == 5:
            # 3+2 layout for 5 events
            cards_html += f'<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-bottom: 24px;">'
            for i in range(3):
                cards_html += generate_event_card_html(all_events_list[i], is_featured=(all_events_list[i] in featured), layout_config=layout_config)
            cards_html += '</div>'
            cards_html += f'<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; margin-bottom: 30px;">'
            for i in range(3, 5):
                cards_html += generate_event_card_html(all_events_list[i], is_featured=(all_events_list[i] in featured), layout_config=layout_config)
            cards_html += '</div>'
        elif total_events == 7:
            # 4+3 layout for 7 events
            cards_html += f'<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px;">'
            for i in range(4):
                cards_html += generate_event_card_html(all_events_list[i], is_featured=(all_events_list[i] in featured), layout_config=layout_config)
            cards_html += '</div>'
            cards_html += f'<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px;">'
            for i in range(4, 7):
                cards_html += generate_event_card_html(all_events_list[i], is_featured=(all_events_list[i] in featured), layout_config=layout_config)
            cards_html += '</div>'
        else:
            # Standard grid layout for other counts
            # Adjust gap based on event count for better space usage
            gap_size = "16px" if total_events >= 6 else "24px"
            bottom_margin = "30px"  # Balanced margin for spacing from footer (30px + 30px content padding = 60px total, matching top)

            # For 1 event, position at top like 2-event layout (no flex: 1)
            if total_events == 1:
                cards_html += f'<div style="display: grid; grid-template-columns: {grid_columns}; gap: {gap_size}; margin-bottom: {bottom_margin};">'
            else:
                cards_html += f'<div style="display: grid; grid-template-columns: {grid_columns}; gap: {gap_size}; flex: 1; margin-bottom: {bottom_margin};">'

            for event in all_events_list:
                cards_html += generate_event_card_html(event, is_featured=(event in featured), layout_config=layout_config)
            cards_html += '</div>'

        cards_html += '</div>'

        content_html = cards_html

    # Generate complete HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kent Denver Events - {date_display}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;600;700&family=Red+Hat+Text:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            width: 2500px;
            height: 1650px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            font-family: 'Red Hat Text', Arial, sans-serif;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }}

        .header {{
            background: linear-gradient(135deg, #041e42 0%, #062a5e 100%);
            color: white;
            padding: 50px 70px;
            box-shadow: 0 6px 24px rgba(0,0,0,0.2);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .header-content {{
            flex: 1;
        }}

        .header h1 {{
            font-family: 'Crimson Pro', Georgia, serif;
            font-size: 72px;
            font-weight: 700;
            margin-bottom: 12px;
            letter-spacing: -0.5px;
        }}

        .header .date {{
            font-size: 38px;
            opacity: 0.95;
            font-weight: 600;
        }}

        .header-logo {{
            height: 120px;
            width: auto;
            opacity: 0.95;
        }}

        .content {{
            flex: 1;
            padding: 40px 70px 30px 70px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }}

        .footer {{
            background: #041e42;
            color: white;
            padding: 24px 70px;
            text-align: center;
            font-size: 22px;
            font-weight: 500;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <h1>Today's Events</h1>
            <div class="date">{date_display}</div>
        </div>
        <img src="{logo_url}" alt="Kent Denver" class="header-logo">
    </div>

    <div class="content">
        {content_html}
    </div>

    <div class="footer">
        Student Leadership Media Team
    </div>
</body>
</html>'''

    return html

def main():
    """Main function to generate digital signage"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Generate Kent Denver digital signage HTML',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python generate_signage.py                    # Generate for today
  python generate_signage.py --date 2025-11-08  # Generate for November 8, 2025
        '''
    )
    parser.add_argument(
        '--date',
        type=str,
        help='Date to generate signage for (YYYY-MM-DD format). Defaults to today.',
        metavar='YYYY-MM-DD'
    )

    args = parser.parse_args()

    print("🖥️  Kent Denver Digital Signage Generator")
    print("=" * 50)

    # Fetch events for the specified date
    events, target_date = fetch_events_for_date(args.date)

    # Generate HTML
    print("\n📝 Generating HTML...")
    html = generate_signage_html(events, target_date)

    # Save to index.html
    output_path = os.path.join(os.path.dirname(__file__), 'index.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Digital signage generated: {output_path}")
    print(f"📊 Displayed {len(events)} event(s)")
    print("\n🎉 Generation complete!")

if __name__ == '__main__':
    main()

