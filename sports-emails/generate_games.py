#!/usr/bin/env python3
"""
Kent Denver Events Email Generator

Automatically scrapes the Kent Denver athletics website and arts events calendar to generate
professional weekly emails with advanced event prioritization, dynamic content variations,
and responsive design.

Features:
- Combined sports games and arts events in one email
- Event prioritization system (featured vs other events)
- Dynamic text variations that rotate weekly (12 variations each)
- Event-specific styling with enhanced visual hierarchy
- Mobile-responsive design with email client compatibility
- Automatic folder organization by week
- Missing day detection and smart section titles
- iCal feed parsing for arts events

Usage:
    python generate_games.py                                    # Next week in auto folder
    python generate_games.py --this-week                        # Current week
    python generate_games.py --start-date 2025-09-22 --end-date 2025-09-27
    python generate_games.py --output-dir testing               # Custom directory

Author: Jacob Barkin (jbarkin28@kentdenver.org)
Version: 3.0 - Added arts events integration via iCal feed
"""

import argparse
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from typing import List, Dict, Optional, Union
import sys
import os
from icalendar import Calendar

# Sport emoji and color mappings
SPORT_CONFIG = {
    'soccer': {'emoji': '⚽', 'color': 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', 'border_color': '#22c55e'},
    'football': {'emoji': '🏈', 'color': 'linear-gradient(135deg, #dc2626 0%, #991b1b 100%)', 'border_color': '#dc2626'},
    'tennis': {'emoji': '🎾', 'color': 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)', 'border_color': '#06b6d4'},
    'golf': {'emoji': '⛳', 'color': 'linear-gradient(135deg, #eab308 0%, #ca8a04 100%)', 'border_color': '#eab308'},
    'cross country': {'emoji': '🏃', 'color': 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)', 'border_color': '#8b5cf6'},
    'field hockey': {'emoji': '🏑', 'color': 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)', 'border_color': '#ec4899'},
    'volleyball': {'emoji': '🏐', 'color': 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', 'border_color': '#f59e0b'},
    'basketball': {'emoji': '🏀', 'color': 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)', 'border_color': '#f97316'},
    'lacrosse': {'emoji': '🥍', 'color': 'linear-gradient(135deg, #10b981 0%, #059669 100%)', 'border_color': '#10b981'},
    'baseball': {'emoji': '⚾', 'color': 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)', 'border_color': '#3b82f6'},
    'swimming': {'emoji': '🏊', 'color': 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)', 'border_color': '#06b6d4'},
    'track': {'emoji': '🏃', 'color': 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)', 'border_color': '#8b5cf6'},
    'ice hockey': {'emoji': '🏒', 'color': 'linear-gradient(135deg, #64748b 0%, #475569 100%)', 'border_color': '#64748b'},
}

# Arts event emoji and color mappings
ARTS_CONFIG = {
    'dance': {'emoji': '💃', 'color': 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)', 'border_color': '#ec4899'},
    'music': {'emoji': '🎵', 'color': 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)', 'border_color': '#8b5cf6'},
    'theater': {'emoji': '🎭', 'color': 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', 'border_color': '#f59e0b'},
    'theatre': {'emoji': '🎭', 'color': 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', 'border_color': '#f59e0b'},
    'visual': {'emoji': '🎨', 'color': 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)', 'border_color': '#06b6d4'},
    'art': {'emoji': '🎨', 'color': 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)', 'border_color': '#06b6d4'},
    'concert': {'emoji': '🎶', 'color': 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)', 'border_color': '#8b5cf6'},
    'performance': {'emoji': '🎵', 'color': 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)', 'border_color': '#f97316'},
    'showcase': {'emoji': '✨', 'color': 'linear-gradient(135deg, #eab308 0%, #ca8a04 100%)', 'border_color': '#eab308'},
    'exhibit': {'emoji': '🖼️', 'color': 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)', 'border_color': '#06b6d4'},
}

class Game:
    def __init__(self, team: str, opponent: str, date: str, time: str, location: str,
                 is_home: bool, sport: str):
        self.team = team
        self.opponent = opponent
        self.date = date
        self.time = time
        self.location = location
        self.is_home = is_home
        self.sport = sport.lower()
        self.event_type = 'game'  # To distinguish from arts events

    def get_sport_config(self) -> Dict[str, str]:
        """Get emoji and color for the sport"""
        for sport_key, config in SPORT_CONFIG.items():
            if sport_key in self.sport:
                return config
        # Default fallback
        return {'emoji': '🏆', 'color': 'linear-gradient(135deg, #6b7280 0%, #4b5563 100%)', 'border_color': '#6b7280'}

    def get_home_away_style(self) -> Dict[str, str]:
        """Get styling for home/away badge"""
        if self.is_home:
            return {
                'background': '#dcfce7',
                'color': '#166534',
                'text': 'Home'
            }
        else:
            return {
                'background': '#fef3c7',
                'color': '#92400e',
                'text': 'Away'
            }

class Event:
    """Class for arts and performance events"""
    def __init__(self, title: str, date: str, time: str, location: str, category: str):
        self.title = title
        self.date = date
        self.time = time
        self.location = location
        self.category = category.lower()
        self.event_type = 'arts'  # To distinguish from games
        # For compatibility with game functions
        self.team = title
        self.is_home = True  # Arts events are always "home"
        self.sport = category.lower()

    def get_sport_config(self) -> Dict[str, str]:
        """Get emoji and color for the arts event category"""
        for category_key, config in ARTS_CONFIG.items():
            if category_key in self.category:
                return config
        # Default fallback for arts events
        return {'emoji': '🎪', 'color': 'linear-gradient(135deg, #a11919 0%, #7c1414 100%)', 'border_color': '#a11919'}

    def get_home_away_style(self) -> Dict[str, str]:
        """Get styling for event badge (always 'Event')"""
        return {
            'background': '#e0e7ff',
            'color': '#3730a3',
            'text': 'Event'
        }

def scrape_athletics_schedule(start_date: str, end_date: str) -> List[Game]:
    """
    Scrape the Kent Denver athletics website for games in the specified date range
    """
    url = "https://www.kentdenver.org/athletics-wellness/schedules-and-scores"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        games = []
        
        # Find the games table
        games_table = soup.find('table')
        if not games_table:
            print("Warning: Could not find games table on the website")
            return []
        
        # Parse each game row
        rows = games_table.find_all('tr')[1:]  # Skip header row
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 6:
                continue
                
            try:
                team = cells[0].get_text(strip=True)
                opponent_cell = cells[1].get_text(strip=True)
                date_str = cells[2].get_text(strip=True)
                time_str = cells[3].get_text(strip=True)
                location = cells[4].get_text(strip=True)
                advantage = cells[5].get_text(strip=True)
                
                # Parse opponent (remove "vs." prefix)
                opponent = opponent_cell.replace('vs.', '').strip()

                # Handle date ranges (e.g., "Oct202025-Oct212025" for multi-day events)
                # Take the first date from the range
                if '-' in date_str and len(date_str) > 15:
                    # This is likely a date range, take the first date
                    date_str = date_str.split('-')[0].strip()

                # Fix date format - handle cases like "Sep222025" -> "Sep 22 2025" or "Oct32025" -> "Oct 3 2025"
                if len(date_str) >= 8 and date_str[3:].isdigit():
                    # Format like "Sep222025" or "Oct32025" - need to add spaces
                    month = date_str[:3]
                    rest = date_str[3:]
                    if len(rest) == 6:  # DDYYYY (like "222025")
                        day = rest[:2]
                        year = rest[2:]
                        date_str = f"{month} {day} {year}"
                    elif len(rest) == 5:  # DYYYY (like "32025")
                        day = rest[:1]
                        year = rest[1:]
                        date_str = f"{month} {day} {year}"
                    elif len(rest) == 7:  # DDDYYYY (like "1032025" - this shouldn't happen but just in case)
                        day = rest[:2]
                        year = rest[2:]
                        date_str = f"{month} {day} {year}"

                # Check if game is in our date range
                try:
                    game_date = datetime.strptime(date_str, '%b %d %Y').date()
                except ValueError:
                    # Try alternative format
                    try:
                        game_date = datetime.strptime(date_str, '%b%d%Y').date()
                    except ValueError:
                        print(f"Could not parse date: {date_str}")
                        continue

                start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                if start_dt <= game_date <= end_dt:
                    # Determine sport from team name
                    sport = extract_sport_from_team(team)
                    is_home = advantage.lower() == 'home'
                    
                    game = Game(
                        team=team,
                        opponent=opponent,
                        date=date_str,
                        time=time_str,
                        location=location,
                        is_home=is_home,
                        sport=sport
                    )
                    games.append(game)
                    
            except Exception as e:
                print(f"Error parsing game row: {e}")
                continue
        
        return games
        
    except requests.RequestException as e:
        print(f"Error fetching athletics schedule: {e}")
        return []

def extract_sport_from_team(team_name: str) -> str:
    """Extract sport name from team name"""
    team_lower = team_name.lower()

    for sport in SPORT_CONFIG.keys():
        if sport in team_lower:
            return sport

    # Additional mappings for common variations
    if 'xc' in team_lower or 'cross country' in team_lower:
        return 'cross country'
    elif 'track' in team_lower:
        return 'track'

    return 'other'

def extract_arts_category(event_title: str) -> str:
    """Extract arts category from event title"""
    title_lower = event_title.lower()

    # Check for specific categories
    for category in ARTS_CONFIG.keys():
        if category in title_lower:
            return category

    # Default to 'performance' if no specific category found
    return 'performance'

def fetch_arts_events(start_date: str, end_date: str) -> List[Event]:
    """
    Fetch arts events from Kent Denver iCal feed for the specified date range
    """
    ical_url = "https://www.kentdenver.org/cf_calendar/feed.cfm?type=ical&feedID=8017725D73BE4200B7C10FDFFBB83FAF"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(ical_url, headers=headers)
        response.raise_for_status()

        # Parse iCal data
        cal = Calendar.from_ical(response.content)
        events = []

        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

        for component in cal.walk():
            if component.name == "VEVENT":
                try:
                    # Extract event details
                    summary = str(component.get('summary', 'Untitled Event'))
                    location = str(component.get('location', 'TBA'))

                    # Handle date/time
                    dtstart = component.get('dtstart')
                    if dtstart:
                        event_dt = dtstart.dt

                        # Handle both date and datetime objects
                        if isinstance(event_dt, datetime):
                            event_date = event_dt.date()
                            event_time = event_dt.strftime('%I:%M %p').lstrip('0')
                        else:
                            event_date = event_dt
                            event_time = 'All Day'

                        # Check if event is in our date range
                        if start_dt <= event_date <= end_dt:
                            # Format date to match Game format
                            date_str = event_date.strftime('%b %d %Y')

                            # Determine category
                            category = extract_arts_category(summary)

                            event = Event(
                                title=summary,
                                date=date_str,
                                time=event_time,
                                location=location,
                                category=category
                            )
                            events.append(event)

                except Exception as e:
                    print(f"Error parsing arts event: {e}")
                    continue

        return events

    except requests.RequestException as e:
        print(f"Error fetching arts events: {e}")
        return []

def format_date_range(start_date: str, end_date: str) -> str:
    """Format date range for display (e.g., 'September 22–27, 2025')"""
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    if start_dt.month == end_dt.month and start_dt.year == end_dt.year:
        return f"{start_dt.strftime('%B')} {start_dt.day}–{end_dt.day}, {start_dt.year}"
    elif start_dt.year == end_dt.year:
        return f"{start_dt.strftime('%B %d')}–{end_dt.strftime('%B %d')}, {start_dt.year}"
    else:
        return f"{start_dt.strftime('%B %d, %Y')}–{end_dt.strftime('%B %d, %Y')}"

def group_games_by_date(games: List[Union[Game, Event]]) -> Dict[str, List[Union[Game, Event]]]:
    """Group games and events by date"""
    games_by_date = {}

    for game in games:
        date_key = game.date
        if date_key not in games_by_date:
            games_by_date[date_key] = []
        games_by_date[date_key].append(game)

    return games_by_date

def generate_featured_event_card_html(event: Event) -> str:
    """Generate HTML for a featured arts event card"""
    event_config = event.get_sport_config()
    event_badge_style = event.get_home_away_style()

    # Arts events always get featured styling
    top_accent = f"background:{event_config['color']};"
    card_border = "border:2px solid #a11919;"  # Kent Denver red border for arts
    card_shadow = "box-shadow:0 6px 20px rgba(161,25,25,0.15);"
    inner_radius = "border-radius:12px;-webkit-border-radius:12px;-moz-border-radius:12px;"

    return f'''
    <td class="stack featured-card" width="50%" valign="top" style="padding:10px 12px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" class="featured-game" style="{inner_radius}{card_border}background:#ffffff;{card_shadow}">
        <tr><td style="height:16px;{top_accent}border-top-left-radius:12px;border-top-right-radius:12px;"></td></tr>
        <tr>
          <td class="featured-card-content" style="padding:20px 22px 18px 22px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:10px;">
              <tr>
                <td style="width:32px;vertical-align:middle;">
                  <span style="font-size:24px;">{event_config['emoji']}</span>
                </td>
                <td style="vertical-align:middle;">
                  <div style="display:inline-block;padding:6px 12px;border-radius:6px;background:{event_badge_style['background']};color:{event_badge_style['color']};font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-weight:700;font-size:12px;letter-spacing:.3px;text-transform:uppercase;">{event.time} • {event_badge_style['text']}</div>
                </td>
              </tr>
            </table>
            <div class="featured-team-name" style="color:#041e42;font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;font-weight:800;font-size:22px;line-height:26px;margin-bottom:6px;">{event.title}</div>
            <p style="margin:6px 0 0 0;color:#6b7280;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-size:14px;line-height:20px;">
              📍 {event.location}
            </p>
          </td>
        </tr>
      </table>
    </td>'''

def generate_featured_game_card_html(game: Game) -> str:
    """Generate HTML for a featured game card (larger, more prominent)"""
    sport_config = game.get_sport_config()
    home_away_style = game.get_home_away_style()

    # Determine if this is a varsity game for additional styling
    is_varsity = is_varsity_game(game.team)

    # Enhanced styling for featured games with prominent visual effects
    # Always use sport-specific color for top accent
    top_accent = f"background:{sport_config['color']};"

    if game.is_home and is_varsity:
        team_style = "font-weight:900;"  # Extra bold for home varsity
        # Use wrapper div approach for gradient border with proper radius alignment
        card_border = ""  # No border on inner table
        card_shadow = "box-shadow:0 8px 25px rgba(34,197,94,0.15), 0 3px 10px rgba(234,179,8,0.1);"
        badge_html = '<div style="display:inline-block;margin-left:8px;padding:2px 8px;border-radius:12px;-webkit-border-radius:12px;-moz-border-radius:12px;background:#22c55e;background:linear-gradient(135deg, #22c55e, #eab308);color:white;font-family:\'Red Hat Text\', Arial, sans-serif;font-weight:700;font-size:10px;letter-spacing:.5px;text-transform:uppercase;">HOME • VARSITY</div>'
        # Special wrapper for gradient border with email client fallbacks
        wrapper_style = "background:#22c55e;background:linear-gradient(135deg, #22c55e, #eab308);padding:3px;border-radius:12px;-webkit-border-radius:12px;-moz-border-radius:12px;"
        inner_radius = "border-radius:9px;-webkit-border-radius:9px;-moz-border-radius:9px;"  # Slightly smaller to account for padding
    elif game.is_home:
        team_style = "font-weight:900;"  # Extra bold for home games
        card_border = "border:3px solid #22c55e;"  # Thick green border for home games
        card_shadow = "box-shadow:0 6px 20px rgba(34,197,94,0.15);"
        badge_html = '<div style="display:inline-block;margin-left:8px;padding:2px 8px;border-radius:12px;-webkit-border-radius:12px;-moz-border-radius:12px;background:#22c55e;color:white;font-family:\'Red Hat Text\', Arial, sans-serif;font-weight:700;font-size:10px;letter-spacing:.5px;text-transform:uppercase;">HOME</div>'
        wrapper_style = ""
        inner_radius = "border-radius:12px;-webkit-border-radius:12px;-moz-border-radius:12px;"
    elif is_varsity:
        team_style = "font-weight:900;"  # Extra bold for varsity
        card_border = "border:3px solid #eab308;"  # Thick yellow border for varsity
        card_shadow = "box-shadow:0 6px 20px rgba(234,179,8,0.15);"
        badge_html = '<div style="display:inline-block;margin-left:8px;padding:2px 8px;border-radius:12px;-webkit-border-radius:12px;-moz-border-radius:12px;background:#eab308;color:white;font-family:\'Red Hat Text\', Arial, sans-serif;font-weight:700;font-size:10px;letter-spacing:.5px;text-transform:uppercase;">VARSITY</div>'
        wrapper_style = ""
        inner_radius = "border-radius:12px;-webkit-border-radius:12px;-moz-border-radius:12px;"
    else:
        team_style = "font-weight:800;"  # Normal bold
        card_border = "border:1px solid #e6eaf2;"  # Normal border
        card_shadow = ""
        badge_html = ""
        wrapper_style = ""
        inner_radius = "border-radius:12px;-webkit-border-radius:12px;-moz-border-radius:12px;"

    # Use wrapper div for gradient border on home+varsity games
    if wrapper_style:
        return f'''
    <td class="stack featured-card" width="50%" valign="top" style="padding:10px 12px;">
      <div style="{wrapper_style}">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" class="featured-game" style="{inner_radius}background:#ffffff;{card_shadow}">
          <tr><td style="height:16px;{top_accent}border-top-left-radius:9px;border-top-right-radius:9px;"></td></tr>
          <tr>
            <td class="featured-card-content" style="padding:20px 22px 18px 22px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:10px;">
                <tr>
                  <td style="width:32px;vertical-align:middle;">
                    <span style="font-size:24px;">{sport_config['emoji']}</span>
                  </td>
                  <td style="vertical-align:middle;">
                    <div style="display:inline-block;padding:6px 12px;border-radius:6px;background:{home_away_style['background']};color:{home_away_style['color']};font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-weight:700;font-size:12px;letter-spacing:.3px;text-transform:uppercase;">{game.time} • {home_away_style['text']}</div>
                  </td>
                </tr>
              </table>
              <div class="featured-team-name" style="color:#041e42;font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;{team_style}font-size:22px;line-height:26px;margin-bottom:6px;">{game.team}{badge_html}</div>
              <p style="margin:0;color:#374151;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-size:16px;line-height:22px;font-weight:600;">
                vs. <strong style="color:#041e42;">{game.opponent}</strong>
              </p>
              <p style="margin:6px 0 0 0;color:#6b7280;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-size:14px;line-height:20px;">
                📍 {game.location}
              </p>
            </td>
          </tr>
        </table>
      </div>
    </td>'''
    else:
        return f'''
    <td class="stack featured-card" width="50%" valign="top" style="padding:10px 12px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" class="featured-game" style="{inner_radius}{card_border}background:#ffffff;{card_shadow}">
        <tr><td style="height:16px;{top_accent}border-top-left-radius:12px;border-top-right-radius:12px;"></td></tr>
        <tr>
          <td class="featured-card-content" style="padding:20px 22px 18px 22px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:10px;">
              <tr>
                <td style="width:32px;vertical-align:middle;">
                  <span style="font-size:24px;">{sport_config['emoji']}</span>
                </td>
                <td style="vertical-align:middle;">
                  <div style="display:inline-block;padding:6px 12px;border-radius:6px;background:{home_away_style['background']};color:{home_away_style['color']};font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-weight:700;font-size:12px;letter-spacing:.3px;text-transform:uppercase;">{game.time} • {home_away_style['text']}</div>
                </td>
              </tr>
            </table>
            <div class="featured-team-name" style="color:#041e42;font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;{team_style}font-size:22px;line-height:26px;margin-bottom:6px;">{game.team}{badge_html}</div>
            <p style="margin:0;color:#374151;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-size:16px;line-height:22px;font-weight:600;">
              vs. <strong style="color:#041e42;">{game.opponent}</strong>
            </p>
            <p style="margin:6px 0 0 0;color:#6b7280;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-size:14px;line-height:20px;">
              📍 {game.location}
            </p>
          </td>
        </tr>
      </table>
    </td>'''

def generate_other_event_list_item_html(event: Event) -> str:
    """Generate HTML for an arts event in the compact list format"""
    event_config = event.get_sport_config()
    event_badge_style = event.get_home_away_style()

    return f'''
    <tr>
      <td style="padding:12px 18px;border-bottom:1px solid #f3f4f6;border-left:4px solid {event_config['border_color']};">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="width:24px;vertical-align:middle;">
              <span style="font-size:16px;">{event_config['emoji']}</span>
            </td>
            <td style="vertical-align:middle;padding-left:8px;">
              <div style="color:#041e42;font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;font-weight:700;font-size:16px;line-height:20px;margin-bottom:2px;">{event.title}</div>
              <p style="margin:0;color:#374151;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-size:13px;line-height:18px;">
                📍 {event.location}
              </p>
            </td>
            <td style="text-align:right;vertical-align:middle;width:80px;">
              <div style="display:inline-block;padding:3px 8px;border-radius:4px;background:{event_badge_style['background']};color:{event_badge_style['color']};font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-weight:700;font-size:10px;letter-spacing:.2px;text-transform:uppercase;">{event.time}</div>
            </td>
          </tr>
        </table>
      </td>
    </tr>'''

def generate_other_game_list_item_html(game: Game) -> str:
    """Generate HTML for a game in the compact list format"""
    sport_config = game.get_sport_config()
    home_away_style = game.get_home_away_style()

    # Simpler styling for list items
    if game.is_home:
        home_indicator = " 🏠"
        team_style = "font-weight:700;"
    else:
        home_indicator = ""
        team_style = "font-weight:600;"

    return f'''
    <tr>
      <td style="padding:12px 18px;border-bottom:1px solid #f3f4f6;border-left:4px solid {sport_config['border_color']};">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="width:24px;vertical-align:middle;">
              <span style="font-size:16px;">{sport_config['emoji']}</span>
            </td>
            <td style="vertical-align:middle;padding-left:8px;">
              <div style="color:#041e42;font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;{team_style}font-size:16px;line-height:20px;margin-bottom:2px;">{game.team}{home_indicator}</div>
              <p style="margin:0;color:#374151;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-size:13px;line-height:18px;">
                vs. <strong>{game.opponent}</strong> • 📍 {game.location}
              </p>
            </td>
            <td style="text-align:right;vertical-align:middle;width:80px;">
              <div style="display:inline-block;padding:3px 8px;border-radius:4px;background:{home_away_style['background']};color:{home_away_style['color']};font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-weight:700;font-size:10px;letter-spacing:.2px;text-transform:uppercase;">{game.time}</div>
            </td>
          </tr>
        </table>
      </td>
    </tr>'''

def is_middle_school_game(team_name: str) -> bool:
    """Determine if a game is for middle school based on team name"""
    team_lower = team_name.lower()

    # Check for explicit middle school indicators
    middle_school_indicators = [
        'middle school', 'ms', '6th', '7th', '8th',
        'sixth', 'seventh', 'eighth'
    ]

    return any(indicator in team_lower for indicator in middle_school_indicators)

def separate_games_by_school(games: List[Game]) -> tuple[List[Game], List[Game]]:
    """Separate games into middle school and upper school lists"""
    middle_school_games = []
    upper_school_games = []

    for game in games:
        if is_middle_school_game(game.team):
            middle_school_games.append(game)
        else:
            upper_school_games.append(game)

    return middle_school_games, upper_school_games

def get_current_week():
    """Get the Monday and Sunday of the current week"""
    today = datetime.now()

    # Find Monday of current week
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)

    # Find Sunday of current week
    sunday = monday + timedelta(days=6)

    return monday.strftime('%Y-%m-%d'), sunday.strftime('%Y-%m-%d')

def get_next_week():
    """Get the Monday and Sunday of next week"""
    today = datetime.now()

    # Find Monday of current week
    days_since_monday = today.weekday()
    current_monday = today - timedelta(days=days_since_monday)

    # Find Monday of next week
    next_monday = current_monday + timedelta(days=7)

    # Find Sunday of next week
    next_sunday = next_monday + timedelta(days=6)

    return next_monday.strftime('%Y-%m-%d'), next_sunday.strftime('%Y-%m-%d')

def is_varsity_game(team_name: str) -> bool:
    """Determine if a game is varsity level based on team name"""
    team_lower = team_name.lower()

    # Check for explicit varsity indicators
    varsity_indicators = ['varsity', 'var']

    # If it explicitly says varsity, it's varsity
    if any(indicator in team_lower for indicator in varsity_indicators):
        return True

    # If it has JV, C Team, or grade level indicators, it's not varsity
    non_varsity_indicators = ['jv', 'junior varsity', 'c team', '6th', '7th', '8th', 'middle school', 'ms']
    if any(indicator in team_lower for indicator in non_varsity_indicators):
        return False

    # For middle school games, nothing is "varsity"
    if is_middle_school_game(team_name):
        return False

    # If no specific level is mentioned and it's upper school, assume varsity
    return True

def is_featured_game(game: Union[Game, Event], is_middle_school: bool) -> bool:
    """Determine if a game or event should be featured (prioritized)"""
    # Arts events are always featured
    if isinstance(game, Event):
        return True

    if is_middle_school:
        # For middle school, only prioritize home games
        return game.is_home
    else:
        # For upper school, prioritize home games OR varsity games
        return game.is_home or is_varsity_game(game.team)

def categorize_games_by_priority(games: List[Union[Game, Event]], is_middle_school: bool) -> tuple[List[Union[Game, Event]], List[Union[Game, Event]]]:
    """Separate games and events into featured and other categories"""
    featured_games = []
    other_games = []

    for game in games:
        if is_featured_game(game, is_middle_school):
            featured_games.append(game)
        else:
            other_games.append(game)

    return featured_games, other_games

def get_missing_weekdays(games_by_date: Dict[str, List[Game]], start_date: str, end_date: str) -> List[str]:
    """Find weekdays (Mon-Fri) that have no games but are between days that do have games"""
    # Convert game dates to datetime objects
    game_dates = []
    for date_str in games_by_date.keys():
        try:
            game_date = datetime.strptime(date_str, '%b %d %Y')
            game_dates.append(game_date)
        except ValueError:
            continue

    if len(game_dates) < 2:
        return []  # Need at least 2 game days to find missing days between them

    game_dates.sort()
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')

    missing_weekdays = []

    # Check each day in the range
    current_date = start_dt
    while current_date <= end_dt:
        # Only check weekdays (Monday=0 to Friday=4)
        if current_date.weekday() < 5:
            # Check if this date has games
            date_str = current_date.strftime('%b %d %Y')
            if date_str not in games_by_date:
                # Check if this date is between game days (not at the very beginning or end)
                is_between_games = False
                for i in range(len(game_dates) - 1):
                    if game_dates[i] < current_date < game_dates[i + 1]:
                        is_between_games = True
                        break

                if is_between_games:
                    missing_weekdays.append(date_str)

        current_date += timedelta(days=1)

    return missing_weekdays

def get_dynamic_text_variations(start_date: str, has_arts_events: bool = False) -> Dict[str, str]:
    """
    Get dynamic text variations based on the week and whether there are arts events

    TEXT VARIATION LOGIC:
    - Uses ISO week number (1-53) from the Monday start date as the selection key
    - All text components (hero, CTA, intro) rotate IN SYNC using the same week number
    - Uses modulo operation to cycle through available variations
    - Example: Week 40 with 8 hero texts uses hero_texts[40 % 8] = hero_texts[0]
    - Example: Week 41 with 8 hero texts uses hero_texts[41 % 8] = hero_texts[1]

    SYNCHRONIZATION:
    - All components use the same week_number, so they rotate together
    - Week 1: All use variation 0, Week 2: All use variation 1, etc.
    - This ensures consistent "tone" across all text in a single email

    DETERMINISTIC:
    - Same week always produces same text combination
    - Reproducible across multiple runs for the same date range

    ARTS EVENTS:
    - If has_arts_events=True, uses text variations that mention both sports and performances
    - If has_arts_events=False, uses text variations that only mention sports
    """
    # Use the Monday date to determine which variation to use
    monday_date = datetime.strptime(start_date, '%Y-%m-%d')
    week_number = monday_date.isocalendar()[1]  # ISO week number

    # Hero text variations - Different sets for sports-only vs sports+arts
    if has_arts_events:
        # Hero texts when there are BOTH sports and arts events
        hero_texts = [
            "The Sun Devil spirit shines bright this week! Our Kent Denver students are ready to compete and perform across {sport_count} sports and arts events. Go Devils! 🔥😈🎭",
            "From the Rocky Mountains to the playing fields and stages, our Sun Devils are bringing their competitive and creative spirit this week! 🏔️⚡🎨",
            "Kent Denver's finest are taking the field and the stage! Join us as we support {sport_count} sports and performances packed with talent and determination. 🔥🏆🎭",
            "Excellence is our standard! This week features {sport_count} sports and arts events where Sun Devil talent shines brightest. 😈🏆🎵",
            "Altitude advantage meets Sun Devil attitude! Our teams and performers are ready to soar across {sport_count} sports and arts events this week. Mile High, Sun Devil High! 🏔️🔥🎭",
            "Exciting action and performances are coming your way! Kent Denver's Sun Devils are bringing their best to {sport_count} sports and arts events this week. ❤️⚡🎨",
            "The Sun Devil legacy continues! This week's {sport_count} sports and performances showcase why Kent Denver develops champions and artists. Come witness greatness! 🏆🔥🎭",
            "Horns up, spirits high! Our Sun Devils are ready to compete and perform across {sport_count} sports and arts events with heart and determination. Join us! 😈⚡🎵",
            "Excellence is our tradition, victory and artistry are our goals! This week's {sport_count} sports and performances showcase the depth of Sun Devil pride. 🌊🔥🎭",
            "From sunrise to sunset, our Sun Devils shine! Kent Denver's athletic and artistic talent is on display across {sport_count} sports and arts events this week. ✨😈🎨",
            "The mountains may be high, but Sun Devil spirits soar higher! Join us for {sport_count} sports and performances of Colorado excellence. 🏔️🔥🎭",
            "Built through dedication, strengthened by Sun Devil spirit! This week's {sport_count} sports and arts events will showcase your passion for Kent Denver! 🔥⚡🎵"
        ]
    else:
        # Hero texts when there are ONLY sports (no arts events)
        hero_texts = [
            "The Sun Devil spirit shines bright this week! Our Kent Denver athletes are ready to compete across {sport_count} sports. Go Devils! 🔥😈",
            "From the Rocky Mountains to the playing fields, our Sun Devils are bringing their competitive spirit to {sport_count} sports this week! 🏔️⚡",
            "Kent Denver's finest are taking the field! Join us as we support {sport_count} sports packed with talent and determination. 🔥🏆",
            "Excellence is our standard! This week features {sport_count} sports where Sun Devil talent shines brightest. 😈🏆",
            "Altitude advantage meets Sun Devil attitude! Our teams are ready to soar across {sport_count} sports this week. Mile High, Sun Devil High! 🏔️🔥",
            "Exciting action is coming your way! Kent Denver's Sun Devils are bringing their best to {sport_count} sports this week. ❤️⚡",
            "The Sun Devil legacy continues! This week's {sport_count} sports showcase why Kent Denver develops champions. Come witness greatness! 🏆🔥",
            "Horns up, spirits high! Our Sun Devils are ready to compete across {sport_count} sports with heart and determination. Join us! 😈⚡",
            "Excellence is our tradition, victory is our goal! This week's {sport_count} sports showcase the depth of Sun Devil pride. 🌊🔥",
            "From sunrise to sunset, our Sun Devils shine! Kent Denver's athletic talent is on display across {sport_count} sports this week. ✨😈",
            "The mountains may be high, but Sun Devil spirits soar higher! Join us for {sport_count} sports of Colorado athletic excellence. 🏔️🔥",
            "Built through dedication, strengthened by Sun Devil spirit! This week's {sport_count} sports will showcase your passion for Kent Denver athletics! 🔥⚡"
        ]

    # CTA text variations - Different sets for sports-only vs sports+arts
    if has_arts_events:
        # CTA texts when there are BOTH sports and arts events
        cta_texts = [
            "Show your Sun Devil pride! Come cheer and applaud as our athletes and performers represent Kent Denver across every sport, stage, and grade level.",
            "The Sun Devil community needs YOU! Join us and help our teams and performers feel the power of true Kent Denver spirit.",
            "From the mountains to the fields and stages, Sun Devils stick together! Your presence energizes our athletes and artists and shows your school pride.",
            "Horns up, voices loud! Pack the stands and fill the seats to show our student-athletes and performers what it means to have Sun Devil nation behind them.",
            "Feel the excitement, share the spirit! Your cheers and applause are the boost that helps our Sun Devils perform their best. Come join us!",
            "Red and blue runs through our school, victory and artistry are our shared goals! Support our teams and performers and be part of the Kent Denver tradition.",
            "The altitude is high, but Sun Devil spirits soar higher! Join your fellow Sun Devils and create an amazing atmosphere at games and performances.",
            "Champions and artists are supported by community! Be the encouragement that helps our Sun Devils reach new heights of excellence.",
            "Your energy matters, your passion shows! Come witness greatness on fields and stages and help write the next chapter of Sun Devil excellence.",
            "From morning games to evening performances, our Sun Devils need their community! Join us and feel the rush of Kent Denver pride.",
            "The strength is in the details, and you are that strength! Your support creates the home advantage and inspiring atmosphere that makes a difference.",
            "Wear red, dream big, cheer loud! Come celebrate the heart, dedication, and talent of Kent Denver's finest student-athletes and performers!"
        ]
    else:
        # CTA texts when there are ONLY sports (no arts events)
        cta_texts = [
            "Show your Sun Devil pride! Come cheer as our athletes compete for Kent Denver across every sport and grade level.",
            "The Sun Devil community needs YOU! Join us and help our teams feel the power of true Kent Denver spirit.",
            "From the mountains to the fields, Sun Devils stick together! Your presence energizes our athletes and shows your school pride.",
            "Horns up, voices loud! Pack the stands and show our student-athletes what it means to have Sun Devil nation behind them.",
            "Feel the excitement, share the spirit! Your cheers are the boost that helps our Sun Devils perform their best. Come join us!",
            "Red and blue runs through our school, victory is our shared goal! Support our teams and be part of the Kent Denver tradition.",
            "The altitude is high, but Sun Devil spirits soar higher! Join your fellow Sun Devils and create an amazing atmosphere.",
            "Champions are supported by community! Be the encouragement that helps our Sun Devils reach new heights of excellence.",
            "Your energy matters, your passion shows! Come witness greatness and help write the next chapter of Sun Devil athletics.",
            "From morning games to evening victories, our Sun Devils need their community! Join us and feel the rush of Kent Denver pride.",
            "The strength is in the details, and you are that strength! Your support creates the home advantage that makes a difference.",
            "Wear red, dream big, cheer loud! Come celebrate the heart, dedication, and talent of Kent Denver's finest student-athletes!"
        ]

    # Intro text variations - Different sets for sports-only vs sports+arts
    if has_arts_events:
        # Intro texts when there are BOTH sports and arts events
        intro_texts = [
            "The Sun Devil spirit is shining bright! Mark your calendars for exciting competitions and performances across every sport, art form, and grade level at Kent Denver.",
            "Get ready for great matchups and captivating performances as our talented Sun Devil athletes and artists take center stage this week.",
            "The mountains echo with excitement! Get ready to witness Kent Denver's finest athletes and performers compete and create with determination this week.",
            "From morning to evening, our Sun Devils are ready to represent our school with pride across multiple sports, performances, and divisions.",
            "Witness the excellence that happens when Sun Devil determination meets Colorado spirit in these exciting athletic and artistic events.",
            "Our student-athletes and performers are bringing their best to represent the Kent Denver tradition with dedication and school pride.",
            "Feel the excitement in the air as Sun Devil athletics and arts bring together our community for outstanding moments of competition and creativity.",
            "Rally behind our teams and performers as they compete and create with heart, supported by passion and that strong Sun Devil spirit.",
            "The stage is set for excellence! Our Sun Devil athletes and artists are ready to deliver performances that make our school proud.",
            "From courts to fields to stages, our students are ready to compete and perform in every arena with the heart of true Kent Denver Sun Devils.",
            "Join the Sun Devil community as we unite to support student-athletes and performers who represent excellence in every competition and performance.",
            "This week brings athletic and artistic excellence in action as our Sun Devils compete and perform with the dedication that makes Kent Denver special."
        ]
    else:
        # Intro texts when there are ONLY sports (no arts events)
        intro_texts = [
            "The Sun Devil spirit is shining bright! Mark your calendars for exciting competitions across every sport and grade level at Kent Denver.",
            "Get ready for great matchups as our talented Sun Devil athletes take center stage in competitions that showcase their skills.",
            "The mountains echo with excitement! Get ready to witness Kent Denver's finest athletes compete with determination this week.",
            "From morning to evening, our Sun Devils are ready to represent our school with pride across multiple sports and divisions.",
            "Witness the excellence that happens when Sun Devil determination meets Colorado spirit in these exciting athletic events.",
            "Our student-athletes are bringing their best to represent the Kent Denver tradition with dedication and school pride.",
            "Feel the excitement in the air as Sun Devil athletics brings together our community for outstanding moments of competition.",
            "Rally behind our teams as they compete with heart, supported by passion and that strong Sun Devil spirit.",
            "The stage is set for excellence! Our Sun Devil athletes are ready to deliver performances that make our school proud.",
            "From courts to fields, our athletes are ready to compete in every arena with the heart of true Kent Denver Sun Devils.",
            "Join the Sun Devil community as we unite to support student-athletes who represent excellence in every competition.",
            "This week brings athletic excellence in action as our Sun Devils compete with the dedication that makes Kent Denver special."
        ]

    # Main title variations (8) - Simple and professional
    title_variations = [
        "Games This Week",
        "This Week's Games",
        "Kent Denver Athletics",
        "Sun Devil Sports",
        "Weekly Games",
        "Athletic Events",
        "Sports This Week",
        "Sun Devil Schedule"
    ]

    # CTA button text variations (10) - Kent Denver specific with appropriate tone
    cta_button_texts = [
        "Show Sun Devil Pride",
        "Join The Community",
        "Share The Spirit",
        "Horns Up, Hearts Out",
        "Support The Team",
        "Rally The Devils",
        "Wear Red & Blue",
        "Answer The Call",
        "Stand With Us",
        "Embrace The Tradition"
    ]

    # CTA header variations (10) - More creative and Kent Denver specific
    cta_headers = [
        "Horns Up, Kent Denver! 🔥😈",
        "Sun Devil Spirit! 🔥⚡",
        "Red & Blue Ready! ❤️💙",
        "Mile High Devils! 🏔️🔥",
        "Show Your Pride! 😈⚡",
        "Sun Devil Strong! 💪🔥",
        "Rise Up, Sun Devils! 🔥😈",
        "School Spirit Awaits! ✨😈",
        "Wear Red, Dream Big! ❤️🏆",
        "Sun Devil Legacy! 🔥�"
    ]

    # Use week number to select variations (modulo to cycle through options)
    hero_text = hero_texts[week_number % len(hero_texts)]
    cta_text = cta_texts[week_number % len(cta_texts)]
    intro_text = intro_texts[week_number % len(intro_texts)]
    title_text = title_variations[week_number % len(title_variations)]
    cta_button_text = cta_button_texts[week_number % len(cta_button_texts)]
    cta_header_text = cta_headers[week_number % len(cta_headers)]

    return {
        'hero_text': hero_text,
        'cta_text': cta_text,
        'intro_text': intro_text,
        'title_text': title_text,
        'cta_button_text': cta_button_text,
        'cta_header_text': cta_header_text
    }

def main():
    parser = argparse.ArgumentParser(
        description='Generate Kent Denver weekly games emails',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                                    # Generate emails for next week in folder (e.g., oct06/)
  %(prog)s --this-week                        # Generate emails for current week in folder (e.g., sep29/)
  %(prog)s --next-week                        # Generate emails for next week (explicit)
  %(prog)s --start-date 2025-09-22 --end-date 2025-09-27
                                              # Generate emails for custom date range in folder (e.g., sep22/)
        '''
    )

    # Date range options (mutually exclusive)
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument('--this-week', action='store_true',
                           help='Generate emails for current week (Monday-Sunday)')
    date_group.add_argument('--next-week', action='store_true',
                           help='Generate emails for next week (Monday-Sunday)')
    date_group.add_argument('--start-date',
                           help='Custom start date (YYYY-MM-DD). Requires --end-date')

    parser.add_argument('--end-date',
                       help='Custom end date (YYYY-MM-DD). Requires --start-date')
    parser.add_argument('--output-dir',
                       help='Output directory for generated files (defaults to auto-generated week folder)')
    parser.add_argument('--output-ms',
                       help='Middle school output filename with path (auto-generated in output directory if not specified)')
    parser.add_argument('--output-us',
                       help='Upper school output filename with path (auto-generated in output directory if not specified)')

    args = parser.parse_args()

    # Determine date range
    if args.start_date and args.end_date:
        start_date, end_date = args.start_date, args.end_date
        date_source = "custom range"
    elif args.start_date or args.end_date:
        parser.error("--start-date and --end-date must be used together")
    elif args.this_week:
        start_date, end_date = get_current_week()
        date_source = "current week"
    elif args.next_week:
        start_date, end_date = get_next_week()
        date_source = "next week"
    else:
        # Default to next week if no options specified
        start_date, end_date = get_next_week()
        date_source = "next week (default)"

    # Generate folder name and default filenames if not specified
    monday_date = datetime.strptime(start_date, '%Y-%m-%d')
    date_str = monday_date.strftime('%b%d').lower()

    # Determine output directory
    if args.output_dir:
        folder_name = args.output_dir
    else:
        folder_name = date_str

    # Create folder if it doesn't exist
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"Created folder: {folder_name}")

    if not args.output_ms:
        args.output_ms = os.path.join(folder_name, f'games-week-middle-school-{date_str}.html')
    if not args.output_us:
        args.output_us = os.path.join(folder_name, f'games-week-upper-school-{date_str}.html')

    print(f"🏈 Generating events emails for {date_source}: {start_date} to {end_date}")

    print("🔍 Scraping games from Kent Denver athletics website...")
    games = scrape_athletics_schedule(start_date, end_date)
    print(f"✅ Found {len(games)} sports games")

    print("🎭 Fetching arts events from Kent Denver calendar...")
    arts_events = fetch_arts_events(start_date, end_date)
    print(f"✅ Found {len(arts_events)} arts events")

    # Combine games and arts events
    all_events = games + arts_events

    if not all_events:
        print("❌ No games or events found for the specified date range.")
        print("   Please check:")
        print("   - Date range is correct")
        print("   - Kent Denver websites are accessible")
        print("   - Events are published on the websites")
        sys.exit(1)

    print(f"✅ Total: {len(all_events)} events (games + arts)")

    # Separate events by school level
    middle_school_events, upper_school_events = separate_games_by_school(all_events)

    print(f"📚 Middle School: {len(middle_school_events)} events")
    print(f"🎓 Upper School: {len(upper_school_events)} events")

    # Generate date range string
    date_range = format_date_range(start_date, end_date)

    # Generate Middle School email
    if middle_school_events:
        ms_events_by_date = group_games_by_date(middle_school_events)
        ms_categories = set(event.sport for event in middle_school_events)
        ms_categories_list = ', '.join(cat.title() for cat in sorted(ms_categories))

        print(f"📝 Generating Middle School email for {len(ms_events_by_date)} days with {len(ms_categories)} categories...")
        ms_html_content = generate_html_email(ms_events_by_date, date_range, ms_categories_list,
                                            start_date, end_date, "Middle School")

        with open(args.output_ms, 'w', encoding='utf-8') as f:
            f.write(ms_html_content)

        print(f"✅ Middle School email generated: {args.output_ms}")
    else:
        print("⚠️  No Middle School events found")

    # Generate Upper School email
    if upper_school_events:
        us_events_by_date = group_games_by_date(upper_school_events)
        us_categories = set(event.sport for event in upper_school_events)
        us_categories_list = ', '.join(cat.title() for cat in sorted(us_categories))

        print(f"📝 Generating Upper School email for {len(us_events_by_date)} days with {len(us_categories)} categories...")
        us_html_content = generate_html_email(us_events_by_date, date_range, us_categories_list,
                                            start_date, end_date, "Upper School")

        with open(args.output_us, 'w', encoding='utf-8') as f:
            f.write(us_html_content)

        print(f"✅ Upper School email generated: {args.output_us}")
    else:
        print("⚠️  No Upper School events found")

    print(f"\n🎉 Email generation complete! Files saved in: {folder_name}/")
    print(f"📧 Ready to send professional emails with sports games and arts events!")

def generate_html_email(games_by_date: Dict[str, List[Game]], date_range: str,
                       sports_list: str, start_date: str, end_date: str, school_level: str = "") -> str:
    """Generate the complete HTML email"""

    # Check if there are any arts events
    all_events = [game for games in games_by_date.values() for game in games]
    has_arts_events = any(isinstance(event, Event) for event in all_events)

    # Get dynamic text variations based on whether there are arts events
    text_variations = get_dynamic_text_variations(start_date, has_arts_events)
    sport_count = len(set(game.sport for games in games_by_date.values() for game in games))

    # HTML header and hero section
    title_suffix = f" — {school_level}" if school_level else ""
    # Determine title based on whether there are arts events
    title_type = "Games and Performances This Week" if has_arts_events else "Games This Week"

    html = f'''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en" style="margin:0;padding:0;">
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="x-apple-disable-message-reformatting" />
    <meta name="format-detection" content="telephone=no,address=no,email=no,date=no,url=no" />
    <meta name="has-arts-events" content="{str(has_arts_events).lower()}" />
    <title>Kent Denver — {title_type} ({date_range}){title_suffix}</title>
    <!--[if !mso]><!-->
    <link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@700;800&family=Red+Hat+Text:wght@400;700&display=swap" rel="stylesheet">
    <!--<![endif]-->
    <style>
      /* Client-specific Styles */
      #outlook a {{ padding: 0; }}
      .ReadMsgBody {{ width: 100%; }}
      .ExternalClass {{ width: 100%; }}
      .ExternalClass, .ExternalClass p, .ExternalClass span, .ExternalClass font, .ExternalClass td, .ExternalClass div {{ line-height: 100%; }}
      table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
      #bodyTable {{ margin: 0; padding: 0; width: 100% !important; line-height: 100% !important; }}

      /* Outlook-specific fixes */
      .mso-hide {{ mso-hide: all; }}

      /* Gmail and Apple Mail fixes */
      u + .body .gmail-fix {{ display: none; }}

      /* Dark mode support */
      @media (prefers-color-scheme: dark) {{
        .dark-mode-bg {{ background-color: #1a1a1a !important; }}
        .dark-mode-text {{ color: #ffffff !important; }}
      }}

      /* Mobile Styles */
      @media only screen and (max-width: 600px) {{
        .stack {{ display: block !important; width: 100% !important; }}
        .pad {{ padding: 16px !important; }}
        .hero-title {{ font-size: 28px !important; line-height: 34px !important; }}
        .inner {{ width: 92% !important; }}
        .game-time {{ font-size: 12px !important; }}
        .mobile-center {{ text-align: center !important; }}
        .mobile-hide {{ display: none !important; }}
        .featured-card {{ padding: 8px 6px !important; }}
        .featured-card-content {{ padding: 16px 14px 12px 14px !important; }}
        .featured-team-name {{ font-size: 18px !important; line-height: 22px !important; }}
        .section-title {{ font-size: 16px !important; }}
        .day-title {{ font-size: 20px !important; line-height: 24px !important; }}
      }}

      /* Enhanced Typography */
      .featured-game {{
        transition: transform 0.2s ease, box-shadow 0.2s ease;
      }}

      /* Better spacing for readability */
      .section-spacing {{ margin-bottom: 20px; }}
      .day-spacing {{ margin-bottom: 16px; }}

      /* Dark Mode Support */
      @media (prefers-color-scheme: dark) {{
        .dark-mode-bg {{ background-color: #1a1a1a !important; }}
        .dark-mode-text {{ color: #ffffff !important; }}
      }}
    </style>
    <!--[if mso]>
    <style type="text/css">
      .fallback-font {{ font-family: Arial, sans-serif !important; }}
    </style>
    <![endif]-->
  </head>
  <body style="margin:0;padding:0;background:#f8f8f8;">
    <!-- Preheader (hidden) -->
    <div style="display:none;visibility:hidden;opacity:0;color:transparent;height:0;width:0;overflow:hidden;mso-hide:all;font-size:1px;line-height:1px;max-height:0px;max-width:0px;">
      {school_level + " " if school_level else ""}Games this week {date_range} — {sports_list}. Go Sun Devils! 🔥😈
    </div>

    <!-- Full-bleed outer wrapper -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f8f8f8;">
      <tr>
        <td align="center">

          <!-- HERO -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#041e42;">
            <tr>
              <td>
                <table role="presentation" class="inner" align="center" width="1000" cellpadding="0" cellspacing="0" style="width:94%;max-width:1000px;margin:0 auto;">
                  <tr>
                    <td class="pad" style="padding:30px 0 22px 0;">
                      <h1 class="hero-title fallback-font" style="margin:0;color:#ffffff;font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;font-weight:800;font-size:34px;line-height:40px;">
                        {text_variations['title_text']}{title_suffix}
                      </h1>
                      <table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:8px;">
                        <tr>
                          <td style="background:#ffffff;color:#041e42;border-radius:4px;padding:6px 10px;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-weight:700;font-size:13px;">
                            {date_range}
                          </td>
                        </tr>
                      </table>
                      <p style="margin:12px 0 0 0;color:#d7e3ff;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-size:16px;line-height:24px;">
                        {text_variations['hero_text'].format(sport_count=sport_count)}
                      </p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>

          <!-- INTRO TEXT -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;">
            <tr>
              <td>
                <table role="presentation" class="inner" align="center" width="1000" cellpadding="0" cellspacing="0" style="width:94%;max-width:1000px;margin:0 auto;">
                  <tr>
                    <td class="pad" style="padding:22px 0 10px 0;">
                      <h2 style="margin:0 0 6px 0;color:#041e42;font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;font-weight:700;font-size:22px;line-height:28px;">
                        This week's schedule
                      </h2>
                      <p style="margin:0;color:#373737;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-size:14px;line-height:22px;">
                        {text_variations['intro_text']}
                      </p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
'''

    # Generate content for each day with prioritized sections
    sorted_dates = sorted(games_by_date.keys(), key=lambda x: datetime.strptime(x, '%b %d %Y'))
    missing_weekdays = get_missing_weekdays(games_by_date, start_date, end_date)
    is_middle_school = school_level == "Middle School"

    # Combine game dates and missing dates, then sort
    all_dates = sorted_dates + missing_weekdays
    all_dates_sorted = sorted(all_dates, key=lambda x: datetime.strptime(x, '%b %d %Y'))

    for i, date_str in enumerate(all_dates_sorted):
        # Check if this is a day with games or a missing day
        has_games = date_str in games_by_date

        if has_games:
            games_for_date = games_by_date[date_str]
            # Categorize games by priority
            featured_games, other_games = categorize_games_by_priority(games_for_date, is_middle_school)
        else:
            games_for_date = []
            featured_games, other_games = [], []

        # Format date for display
        date_obj = datetime.strptime(date_str, '%b %d %Y')
        formatted_date = date_obj.strftime('%A, %B %d')

        # Add day separator if not first day
        if i > 0:
            html += '''
          <!-- DAY SEPARATOR -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f8f8f8;">
            <tr>
              <td>
                <table role="presentation" class="inner" align="center" width="1000" cellpadding="0" cellspacing="0" style="width:94%;max-width:1000px;margin:0 auto;">
                  <tr>
                    <td style="padding:12px 0;">
                      <div style="height:3px;background:linear-gradient(90deg, #041e42 0%, #a11919 50%, #041e42 100%);border-radius:2px;opacity:0.3;"></div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
'''

        # Day header
        html += f'''
          <!-- {formatted_date.upper()} GAMES -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f8f8f8;">
            <tr>
              <td>
                <table role="presentation" class="inner" align="center" width="1000" cellpadding="0" cellspacing="0" style="width:94%;max-width:1000px;margin:0 auto;">
                  <tr>
                    <td class="pad" style="padding:18px 0 8px 0;">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:12px;">
                        <tr>
                          <td style="width:36px;vertical-align:middle;">
                            <span style="font-size:24px;">📅</span>
                          </td>
                          <td style="vertical-align:middle;">
                            <h3 class="day-title" style="margin:0;color:#041e42;font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;font-weight:800;font-size:22px;line-height:26px;">
                              {formatted_date}
                            </h3>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
'''

        # Handle days with no games
        if not has_games:
            html += '''
                  <tr>
                    <td class="pad" style="padding:0 0 16px 0;">
                      <div style="text-align:center;padding:24px;border-radius:8px;background:#f9fafb;border:1px solid #e5e7eb;">
                        <span style="font-size:18px;margin-right:8px;">🗓️</span>
                        <span style="color:#6b7280;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-size:15px;line-height:20px;">No games scheduled</span>
                      </div>
                    </td>
                  </tr>
'''

        # Featured Games/Events Section (no header for more compact design)
        if featured_games:

            # Generate featured cards in rows of 2
            for j in range(0, len(featured_games), 2):
                html += '                  <tr>\n'

                # First featured item in row
                item = featured_games[j]
                if isinstance(item, Event):
                    html += generate_featured_event_card_html(item)
                else:
                    html += generate_featured_game_card_html(item)

                # Second featured item in row (or spacer if odd number)
                if j + 1 < len(featured_games):
                    item2 = featured_games[j + 1]
                    if isinstance(item2, Event):
                        html += generate_featured_event_card_html(item2)
                    else:
                        html += generate_featured_game_card_html(item2)
                else:
                    html += '                    <td class="stack" width="50%" valign="top" style="padding:10px 12px;"></td>'

                html += '\n                  </tr>\n'

        # Other Games/Events Section (no header for more compact design)
        if other_games:
            # Add spacing only if there are featured games above
            spacing_style = "padding:16px 0 8px 0;" if featured_games else "padding:0 0 8px 0;"
            html += f'''
                  <tr>
                    <td colspan="2" style="{spacing_style}">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-radius:8px;border:1px solid #e6eaf2;background:#ffffff;">
'''

            # Generate other games/events as list items
            for item in other_games:
                if isinstance(item, Event):
                    html += generate_other_event_list_item_html(item)
                else:
                    html += generate_other_game_list_item_html(item)

            html += '''
                      </table>
                    </td>
                  </tr>
'''

        html += '''                </table>
              </td>
            </tr>
          </table>
'''

    # Call to Action and Footer
    html += f'''

          <!-- CALL TO ACTION -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;">
            <tr>
              <td>
                <table role="presentation" class="inner" align="center" width="1000" cellpadding="0" cellspacing="0" style="width:94%;max-width:1000px;margin:0 auto;">
                  <tr>
                    <td class="pad" style="padding:22px 0 18px 0;">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-radius:18px;border:1px solid #e6eaf2;background:#ffffff;">
                        <tr><td style="height:14px;background:#13cf97;border-top-left-radius:18px;border-top-right-radius:18px;"></td></tr>
                        <tr>
                          <td style="padding:20px 22px 18px 22px;">
                            <table role="presentation" cellpadding="0" cellspacing="0">
                              <tr>
                                <td style="padding:6px 10px;border-radius:4px;background:#e7fff6;color:#041e42;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-weight:700;font-size:12px;letter-spacing:.3px;text-transform:uppercase;">
                                  {text_variations['cta_button_text']}
                                </td>
                              </tr>
                            </table>
                            <div style="margin-top:10px;color:#041e42;font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;font-weight:800;font-size:24px;line-height:28px;">
                              {text_variations['cta_header_text']}
                            </div>
                            <p style="margin:10px 0 0 0;color:#373737;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-size:15px;line-height:24px;">
                              {text_variations['cta_text']}
                            </p>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>

          <!-- SIGN-OFF -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#041e42;">
            <tr>
              <td>
                <table role="presentation" class="inner" align="center" width="1000" cellpadding="0" cellspacing="0" style="width:94%;max-width:1000px;margin:0 auto;">
                  <tr>
                    <td class="pad" style="padding:18px 0 26px 0;">
                      <p style="margin:0 0 8px 0;color:#ffffff;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-size:14px;line-height:20px;">
                        For complete schedules, directions, and updates, <a href="https://www.kentdenver.org/athletics-wellness/schedules-and-scores" style="color:#d7e3ff;text-decoration:underline;">visit our athletics page</a>.
                      </p>
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                          <td style="text-align:left;">
                            <p style="margin:0;color:#d1d7e6;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-size:13px;line-height:19px;">
                              — Student Leadership Media Team
                            </p>
                          </td>
                          <td style="text-align:right;">
                            <p style="margin:0;color:#a1a8b8;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-size:11px;line-height:16px;">
                              Designed by <a href="https://jacobbarkin.com" style="color:#a1a8b8;text-decoration:underline;">Jacob Barkin</a>
                            </p>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>

        </td>
      </tr>
    </table>
  </body>
</html>'''

    return html

if __name__ == '__main__':
    main()
