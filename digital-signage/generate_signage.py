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

Author: Jacob Barkin (jbarkin28@kentdenver.org)
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import sys
import os
from typing import List, Dict, Union
from icalendar import Calendar

# Add parent directory to path to import from sports-emails
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sports-emails'))
from generate_games import (
    Game, Event, SPORT_CONFIG, ARTS_CONFIG,
    scrape_athletics_schedule, fetch_arts_events,
    is_varsity_game, is_middle_school_game
)

def get_today_date_range():
    """Get today's date in the format needed for fetching"""
    today = datetime.now()
    date_str = today.strftime('%Y-%m-%d')
    return date_str, date_str

def fetch_todays_events():
    """Fetch all games and events for today"""
    start_date, end_date = get_today_date_range()
    
    print(f"🔍 Fetching events for {start_date}...")
    
    # Fetch sports games
    games = scrape_athletics_schedule(start_date, end_date)
    print(f"✅ Found {len(games)} sports games")
    
    # Fetch arts events
    arts_events = fetch_arts_events(start_date, end_date)
    print(f"✅ Found {len(arts_events)} arts events")
    
    # Combine all events
    all_events = games + arts_events
    print(f"📊 Total: {len(all_events)} events")
    
    return all_events

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

def generate_event_card_html(event: Union[Game, Event], is_featured: bool = False, card_size: str = "normal") -> str:
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

    # Dynamic sizing based on number of events
    if card_size == "large":
        # For 1-2 events - make them really big
        emoji_size = "64px"
        title_size = "42px"
        subtitle_size = "28px"
        badge_size = "24px"
        time_size = "36px"
        padding = "48px 56px"
        top_accent = "28px"
        border_width = "4px"
        margin = "24px"
    elif card_size == "medium":
        # For 3-4 events
        emoji_size = "48px"
        title_size = "32px"
        subtitle_size = "22px"
        badge_size = "20px"
        time_size = "28px"
        padding = "36px 42px"
        top_accent = "24px"
        border_width = "3px"
        margin = "20px"
    else:
        # For 5+ events - normal size
        emoji_size = "40px"
        title_size = "26px"
        subtitle_size = "18px"
        badge_size = "16px"
        time_size = "24px"
        padding = "28px 32px"
        top_accent = "20px"
        border_width = "3px" if is_featured else "2px"
        margin = "16px"

    card_style = f"border: {border_width} solid {config['border_color']}; box-shadow: 0 8px 24px rgba(0,0,0,0.15);"

    return f'''
    <div class="event-card" style="background: white; border-radius: 20px; {card_style} overflow: hidden; margin: {margin};">
      <div style="height: {top_accent}; background: {config['color']};"></div>
      <div style="padding: {padding};">
        <div style="display: flex; align-items: center; margin-bottom: 16px;">
          <span style="font-size: {emoji_size}; margin-right: 16px;">{config['emoji']}</span>
          <div style="flex: 1;">
            <div style="color: #041e42; font-family: 'Crimson Pro', Georgia, serif; font-weight: 700; font-size: {title_size}; line-height: 1.2; margin-bottom: 8px;">{title}</div>
            <div style="color: #374151; font-family: 'Red Hat Text', Arial, sans-serif; font-size: {subtitle_size}; line-height: 1.3; font-weight: 500;">{subtitle}</div>
          </div>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 20px;">
          <div style="background: {badge_style['background']}; color: {badge_style['color']}; padding: 10px 20px; border-radius: 8px; font-family: 'Red Hat Text', Arial, sans-serif; font-weight: 700; font-size: {badge_size};">
            {badge_style['text']}
          </div>
          <div style="color: #041e42; font-family: 'Red Hat Text', Arial, sans-serif; font-weight: 700; font-size: {time_size};">
            🕐 {event.time}
          </div>
        </div>
      </div>
    </div>
    '''

def generate_signage_html(events: List[Union[Game, Event]]) -> str:
    """Generate the complete HTML for digital signage"""
    today = datetime.now()
    date_display = today.strftime('%A, %B %d, %Y')

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
        # Determine card size based on total number of events
        total_events = len(events)
        if total_events <= 2:
            card_size = "large"
            grid_columns = "1fr"
            section_title_size = "48px"
        elif total_events <= 4:
            card_size = "medium"
            grid_columns = "repeat(2, 1fr)"
            section_title_size = "42px"
        else:
            card_size = "normal"
            grid_columns = "repeat(auto-fit, minmax(500px, 1fr))"
            section_title_size = "38px"

        # Categorize events
        featured, regular = categorize_events(events)

        # Generate cards
        cards_html = ""

        if featured:
            cards_html += f'<div style="margin-bottom: 40px;"><h3 style="color: #041e42; font-family: \'Crimson Pro\', Georgia, serif; font-size: {section_title_size}; margin: 0 0 30px 20px; font-weight: 700;">Featured Events</h3>'
            cards_html += f'<div style="display: grid; grid-template-columns: {grid_columns}; gap: 24px;">'
            for event in featured:
                cards_html += generate_event_card_html(event, is_featured=True, card_size=card_size)
            cards_html += '</div></div>'

        if regular:
            cards_html += f'<div><h3 style="color: #041e42; font-family: \'Crimson Pro\', Georgia, serif; font-size: {section_title_size}; margin: 0 0 30px 20px; font-weight: 700;">Other Events</h3>'
            cards_html += f'<div style="display: grid; grid-template-columns: {grid_columns}; gap: 24px;">'
            for event in regular:
                cards_html += generate_event_card_html(event, is_featured=False, card_size=card_size)
            cards_html += '</div></div>'

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
            padding: 60px 70px;
            overflow-y: auto;
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
    print("🖥️  Kent Denver Digital Signage Generator")
    print("=" * 50)

    # Fetch today's events
    events = fetch_todays_events()

    # Generate HTML
    print("\n📝 Generating HTML...")
    html = generate_signage_html(events)

    # Save to index.html
    output_path = os.path.join(os.path.dirname(__file__), 'index.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Digital signage generated: {output_path}")
    print(f"📊 Displayed {len(events)} event(s)")
    print("\n🎉 Generation complete!")

if __name__ == '__main__':
    main()

