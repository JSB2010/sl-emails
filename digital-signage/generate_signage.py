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

def generate_event_card_html(event: Union[Game, Event], is_featured: bool = False) -> str:
    """Generate HTML for a single event card"""
    config = event.get_sport_config()
    
    if event.event_type == 'arts':
        badge_style = event.get_home_away_style()
        title = event.title
        subtitle = f"📍 {event.location}"
    else:
        badge_style = event.get_home_away_style()
        title = event.team
        subtitle = f"vs. {event.opponent} • 📍 {event.location}"
    
    # Card styling
    if is_featured:
        card_class = "featured-card"
        card_style = f"border: 3px solid {config['border_color']}; box-shadow: 0 8px 24px rgba(0,0,0,0.12);"
        top_accent_height = "20px"
    else:
        card_class = "regular-card"
        card_style = f"border: 2px solid {config['border_color']}; box-shadow: 0 4px 12px rgba(0,0,0,0.08);"
        top_accent_height = "12px"
    
    return f'''
    <div class="{card_class}" style="background: white; border-radius: 16px; {card_style} overflow: hidden; margin: 16px;">
      <div style="height: {top_accent_height}; background: {config['color']};"></div>
      <div style="padding: 24px 28px;">
        <div style="display: flex; align-items: center; margin-bottom: 12px;">
          <span style="font-size: 32px; margin-right: 12px;">{config['emoji']}</span>
          <div style="flex: 1;">
            <div style="color: #041e42; font-family: 'Crimson Pro', Georgia, serif; font-weight: 700; font-size: 22px; line-height: 1.3; margin-bottom: 4px;">{title}</div>
            <div style="color: #374151; font-family: 'Red Hat Text', Arial, sans-serif; font-size: 16px; line-height: 1.4;">{subtitle}</div>
          </div>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 16px;">
          <div style="background: {badge_style['background']}; color: {badge_style['color']}; padding: 6px 14px; border-radius: 6px; font-family: 'Red Hat Text', Arial, sans-serif; font-weight: 600; font-size: 14px;">
            {badge_style['text']}
          </div>
          <div style="color: #041e42; font-family: 'Red Hat Text', Arial, sans-serif; font-weight: 700; font-size: 20px;">
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
    
    if not events:
        # No events today
        content_html = '''
        <div style="text-align: center; padding: 100px 60px;">
          <div style="font-size: 80px; margin-bottom: 30px;">📅</div>
          <h2 style="color: #041e42; font-family: 'Crimson Pro', Georgia, serif; font-size: 48px; margin: 0 0 20px 0;">No Events Today</h2>
          <p style="color: #6b7280; font-family: 'Red Hat Text', Arial, sans-serif; font-size: 28px; margin: 0;">Check back tomorrow for upcoming games and performances!</p>
        </div>
        '''
    else:
        # Categorize events
        featured, regular = categorize_events(events)
        
        # Generate cards
        cards_html = ""
        
        if featured:
            cards_html += '<div style="margin-bottom: 30px;"><h3 style="color: #041e42; font-family: \'Crimson Pro\', Georgia, serif; font-size: 32px; margin: 0 0 20px 20px; font-weight: 700;">Featured Events</h3>'
            cards_html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 20px;">'
            for event in featured:
                cards_html += generate_event_card_html(event, is_featured=True)
            cards_html += '</div></div>'
        
        if regular:
            cards_html += '<div><h3 style="color: #041e42; font-family: \'Crimson Pro\', Georgia, serif; font-size: 28px; margin: 0 0 20px 20px; font-weight: 700;">Other Events</h3>'
            cards_html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 16px;">'
            for event in regular:
                cards_html += generate_event_card_html(event, is_featured=False)
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
            padding: 40px 60px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }}

        .header h1 {{
            font-family: 'Crimson Pro', Georgia, serif;
            font-size: 64px;
            font-weight: 700;
            margin-bottom: 8px;
        }}

        .header .date {{
            font-size: 32px;
            opacity: 0.9;
            font-weight: 500;
        }}

        .content {{
            flex: 1;
            padding: 50px 60px;
            overflow-y: auto;
        }}

        .footer {{
            background: #041e42;
            color: white;
            padding: 20px 60px;
            text-align: center;
            font-size: 18px;
        }}

        .footer a {{
            color: #93c5fd;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏫 Kent Denver Events</h1>
        <div class="date">{date_display}</div>
    </div>

    <div class="content">
        {content_html}
    </div>

    <div class="footer">
        Student Leadership Media Team • Designed by <a href="https://jacobbarkin.com">Jacob Barkin</a>
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

