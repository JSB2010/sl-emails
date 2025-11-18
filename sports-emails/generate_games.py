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
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

ICON_CDN_BASE = "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.5.2/svgs/solid"
KDS_PRIMARY_LOGO_URL = (
    "https://cdn-assets-cloud.frontify.com/s3/frontify-cloud-files-us/"
    "eyJwYXRoIjoiZnJvbnRpZnlcL2FjY291bnRzXC9iNFwvNzU3NDlcL3Byb2plY3RzXC8xMDUwNjZc"
    "L2Fzc2V0c1wvYTNcLzY3NDA0OTZcLzlmYTY2NGYzZjhiOGI3YjY2ZDEwZDBkZGI5NjcxNmJmLTE2"
    "NTY4ODQyNjYucG5nIn0:frontify:0G-jY-31l0MCBnvlONY7KuK6-sTagdCay7zorKYJ6_o?width=600&format=png"
)

# Sport icon and color mappings
SPORT_CONFIG = {
    'soccer': {'icon': 'futbol', 'border_color': '#0066ff', 'accent_color': '#0066ff'},
    'football': {'icon': 'football', 'border_color': '#a11919', 'accent_color': '#a11919'},
    'tennis': {'icon': 'table-tennis-paddle-ball', 'border_color': '#13cf97', 'accent_color': '#13cf97'},
    'golf': {'icon': 'golf-ball-tee', 'border_color': '#f2b900', 'accent_color': '#f2b900'},
    'cross country': {'icon': 'person-hiking', 'border_color': '#8b5cf6', 'accent_color': '#8b5cf6'},
    'field hockey': {'icon': 'hockey-puck', 'border_color': '#ec4899', 'accent_color': '#ec4899'},
    'volleyball': {'icon': 'volleyball', 'border_color': '#f59e0b', 'accent_color': '#f59e0b'},
    'basketball': {'icon': 'basketball', 'border_color': '#f97316', 'accent_color': '#f97316'},
    'lacrosse': {'icon': 'helmet-safety', 'border_color': '#10b981', 'accent_color': '#10b981'},
    'baseball': {'icon': 'baseball', 'border_color': '#3b82f6', 'accent_color': '#3b82f6'},
    'swimming': {'icon': 'person-swimming', 'border_color': '#06b6d4', 'accent_color': '#06b6d4'},
    'track': {'icon': 'person-running', 'border_color': '#8b5cf6', 'accent_color': '#8b5cf6'},
    'ice hockey': {'icon': 'hockey-puck', 'border_color': '#64748b', 'accent_color': '#64748b'},
}

# Arts event icon and color mappings
ARTS_CONFIG = {
    'dance': {'icon': 'person-walking', 'border_color': '#ec4899', 'accent_color': '#ec4899'},
    'music': {'icon': 'music', 'border_color': '#8b5cf6', 'accent_color': '#8b5cf6'},
    'theater': {'icon': 'masks-theater', 'border_color': '#f59e0b', 'accent_color': '#f59e0b'},
    'theatre': {'icon': 'masks-theater', 'border_color': '#f59e0b', 'accent_color': '#f59e0b'},
    'visual': {'icon': 'palette', 'border_color': '#06b6d4', 'accent_color': '#06b6d4'},
    'art': {'icon': 'palette', 'border_color': '#06b6d4', 'accent_color': '#06b6d4'},
    'concert': {'icon': 'music', 'border_color': '#8b5cf6', 'accent_color': '#8b5cf6'},
    'performance': {'icon': 'microphone-lines', 'border_color': '#f97316', 'accent_color': '#f97316'},
    'showcase': {'icon': 'star', 'border_color': '#eab308', 'accent_color': '#eab308'},
    'exhibit': {'icon': 'palette', 'border_color': '#06b6d4', 'accent_color': '#06b6d4'},
}

def build_icon_html(icon_name: Optional[str], alt_text: str, size: int = 20) -> str:
    """Return inline HTML for a small icon (Font Awesome CDN or letter fallback)."""
    if icon_name:
        icon_url = f"{ICON_CDN_BASE}/{icon_name}.svg"
        return (
            f'<img src="{icon_url}" width="{size}" height="{size}" alt="{alt_text}" '
            'style="display:block;" border="0" />'
        )

    fallback_letter = (alt_text[:1] if alt_text else "?").upper()
    return (
        f'<span role="img" aria-label="{alt_text}" '
        f"style=\"display:inline-block;width:{size}px;height:{size}px;border-radius:50%;"
        "background:#041e42;color:#ffffff;font-family:'Red Hat Text', Arial, sans-serif;"
        f"font-size:{max(11, int(size*0.55))}px;line-height:{size}px;text-align:center;font-weight:700;\">"
        f"{fallback_letter}</span>"
    )

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
        """Get icon and color for the sport"""
        for sport_key, config in SPORT_CONFIG.items():
            if sport_key in self.sport:
                return config
        # Default fallback
        return {'icon': 'trophy', 'border_color': '#6b7280'}

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
        """Get icon and color for the arts event category"""
        for category_key, config in ARTS_CONFIG.items():
            if category_key in self.category:
                return config
        # Default fallback for arts events
        return {'icon': 'star', 'border_color': '#a11919'}

    def get_home_away_style(self) -> Dict[str, str]:
        """Get styling for event badge (always 'Event')"""
        return {
            'background': '#e0e7ff',
            'color': '#3730a3',
            'text': 'Event'
        }

def parse_games_from_soup(soup: BeautifulSoup, start_date: str, end_date: str) -> tuple[List[Game], Optional[datetime]]:
    """
    Parse games from BeautifulSoup object
    Returns: (list of games, latest game date found)
    """
    games = []
    latest_date = None

    # Find the games table
    games_table = soup.find('table')
    if not games_table:
        print("Warning: Could not find games table on the website")
        return [], None

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

            # Parse the date
            try:
                game_date = datetime.strptime(date_str, '%b %d %Y').date()
            except ValueError:
                # Try alternative format
                try:
                    game_date = datetime.strptime(date_str, '%b%d%Y').date()
                except ValueError:
                    print(f"Could not parse date: {date_str}")
                    continue

            # Track the latest date we've seen
            if latest_date is None or game_date > latest_date:
                latest_date = game_date

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

    return games, latest_date


def scrape_athletics_schedule_with_selenium(start_date: str, end_date: str) -> List[Game]:
    """
    Scrape athletics schedule using Selenium to handle "Load More" button
    """
    url = "https://www.kentdenver.org/athletics-wellness/schedules-and-scores"

    print("🔄 Using Selenium to load more events...")

    # Setup Chrome options for headless mode (works in GitHub Actions)
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

    driver = None
    try:
        # Initialize the Chrome driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Navigate to the page
        driver.get(url)
        time.sleep(2)  # Wait for initial load

        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        max_clicks = 50  # Safety limit to prevent infinite loops
        clicks = 0

        while clicks < max_clicks:
            # Parse current page content
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            games, latest_date = parse_games_from_soup(soup, start_date, end_date)

            # Check if we have events covering our date range
            if latest_date and latest_date >= end_dt:
                print(f"✅ Found events up to {latest_date}, which covers requested range")
                break

            # Try to find and click "Load More" button
            try:
                # Look for common "Load More" button patterns
                load_more_button = None

                # Try different selectors
                selectors = [
                    "//button[contains(text(), 'Load More')]",
                    "//a[contains(text(), 'Load More')]",
                    "//button[contains(@class, 'load-more')]",
                    "//a[contains(@class, 'load-more')]",
                    "//*[contains(text(), 'Show More')]",
                    "//*[contains(text(), 'View More')]"
                ]

                for selector in selectors:
                    try:
                        load_more_button = driver.find_element(By.XPATH, selector)
                        if load_more_button and load_more_button.is_displayed():
                            break
                    except NoSuchElementException:
                        continue

                if not load_more_button or not load_more_button.is_displayed():
                    print(f"✅ No more 'Load More' button found after {clicks} clicks")
                    break

                # Click the button
                driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
                time.sleep(0.5)
                load_more_button.click()
                clicks += 1
                print(f"   Clicked 'Load More' ({clicks} times)...")
                time.sleep(1.5)  # Wait for content to load

            except Exception as e:
                print(f"✅ Finished loading events (no more button available)")
                break

        # Final parse of all loaded content
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        games, _ = parse_games_from_soup(soup, start_date, end_date)

        return games

    except Exception as e:
        print(f"Error with Selenium scraping: {e}")
        return []
    finally:
        if driver:
            driver.quit()


def scrape_athletics_schedule(start_date: str, end_date: str) -> List[Game]:
    """
    Two-stage scraping: Try BeautifulSoup first, fall back to Selenium if needed

    Stage 1: Quick scrape with BeautifulSoup (fast)
    Stage 2: Use Selenium to click "Load More" if we need more events (thorough)
    """
    url = "https://www.kentdenver.org/athletics-wellness/schedules-and-scores"

    # STAGE 1: Try BeautifulSoup first (fast method)
    print("📥 Stage 1: Quick fetch with BeautifulSoup...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        games, latest_date = parse_games_from_soup(soup, start_date, end_date)

        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Check if we need Stage 2
        if games and latest_date and latest_date >= end_dt:
            print(f"✅ Stage 1 successful! Found {len(games)} games covering the date range")
            return games
        else:
            if not games:
                print(f"⚠️  Stage 1: No games found in date range")
            else:
                print(f"⚠️  Stage 1: Latest event is {latest_date}, but need events until {end_dt}")
            print(f"🔄 Moving to Stage 2: Selenium with 'Load More' clicking...")

    except requests.RequestException as e:
        print(f"⚠️  Stage 1 failed: {e}")
        print(f"🔄 Moving to Stage 2: Selenium with 'Load More' clicking...")

    # STAGE 2: Use Selenium to load more events
    return scrape_athletics_schedule_with_selenium(start_date, end_date)

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
    '''Generate HTML for a featured arts event card'''
    event_config = event.get_sport_config()
    category_label = event.category.title()
    icon_html = build_icon_html(event_config.get('icon'), f"{category_label} icon")

    return f'''
                              <tr>
                                <td style="padding:6px 0;">
                                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e3e7ef;border-left:4px solid {event_config['border_color']};border-radius:12px;background:#fbfbfb;">
                                    <tr>
                                      <td style="padding:16px 18px;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                          <tr>
                                            <td style="width:28px;vertical-align:top;">{icon_html}</td>
                                            <td style="padding-left:10px;">
                                              <div style="font-size:12px;letter-spacing:.18em;color:#6b7280;text-transform:uppercase;">{category_label} • {event.time}</div>
                                              <div style="margin:6px 0 4px 0;color:#041e42;font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;font-size:18px;line-height:22px;font-weight:600;">{event.title}</div>
                                              <p style="margin:0;color:#4b5563;font-size:14px;line-height:20px;">{event.location}</p>
                                            </td>
                                          </tr>
                                        </table>
                                      </td>
                                    </tr>
                                  </table>
                                </td>
                              </tr>'''

def generate_featured_game_card_html(game: Game) -> str:
    '''Generate HTML for a featured game card (single column)'''
    sport_config = game.get_sport_config()
    icon_html = build_icon_html(sport_config.get('icon'), f"{game.sport.title()} icon")
    detail_parts = [game.time, "Home" if game.is_home else "Away"]
    if is_varsity_game(game.team):
        detail_parts.append("Varsity")
    time_line = " • ".join(detail_parts)

    return f'''
                              <tr>
                                <td style="padding:6px 0;">
                                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e3e7ef;border-left:4px solid {sport_config['border_color']};border-radius:12px;background:#fbfbfb;">
                                    <tr>
                                      <td style="padding:16px 18px;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                          <tr>
                                            <td style="width:28px;vertical-align:top;">{icon_html}</td>
                                            <td style="padding-left:10px;">
                                              <div style="font-size:12px;letter-spacing:.18em;color:#6b7280;text-transform:uppercase;">{time_line}</div>
                                              <div style="margin:6px 0 4px 0;color:#041e42;font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;font-size:18px;line-height:22px;font-weight:600;">{game.team}</div>
                                              <p style="margin:0;color:#4b5563;font-size:14px;line-height:20px;">vs. {game.opponent}</p>
                                              <p style="margin:6px 0 0 0;color:#6b7280;font-size:13px;line-height:18px;">{game.location}</p>
                                            </td>
                                          </tr>
                                        </table>
                                      </td>
                                    </tr>
                                  </table>
                                </td>
                              </tr>'''

def generate_other_event_list_item_html(event: Event) -> str:
    '''Generate HTML for an arts event in the compact list format'''
    category_label = event.category.title()
    icon_html = build_icon_html(event.get_sport_config().get('icon'), f"{category_label} icon")

    return f'''
                              <tr>
                                <td style="padding:12px 0;border-top:1px solid #edf0f5;">
                                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                      <td style="width:28px;vertical-align:top;">{icon_html}</td>
                                      <td style="font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;font-weight:600;font-size:16px;line-height:20px;color:#041e42;padding-left:10px;">{event.title}</td>
                                      <td style="text-align:right;color:#6b7280;font-size:12px;letter-spacing:.18em;text-transform:uppercase;">{event.time}</td>
                                    </tr>
                                    <tr>
                                      <td></td>
                                      <td colspan="2" style="padding-top:4px;color:#4b5563;font-size:13px;line-height:18px;">{category_label} • {event.location}</td>
                                    </tr>
                                  </table>
                                </td>
                              </tr>'''

def generate_other_game_list_item_html(game: Game) -> str:
    '''Generate HTML for a game in the compact list format'''
    detail_parts = [f"vs. {game.opponent}", "Home" if game.is_home else "Away"]
    detail_line = " • ".join(detail_parts)
    icon_html = build_icon_html(game.get_sport_config().get('icon'), f"{game.sport.title()} icon")

    return f'''
                              <tr>
                                <td style="padding:12px 0;border-top:1px solid #edf0f5;">
                                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                      <td style="width:28px;vertical-align:top;">{icon_html}</td>
                                      <td style="font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;font-weight:600;font-size:16px;line-height:20px;color:#041e42;padding-left:10px;">{game.team}</td>
                                      <td style="text-align:right;color:#6b7280;font-size:12px;letter-spacing:.18em;text-transform:uppercase;">{game.time}</td>
                                    </tr>
                                    <tr>
                                      <td></td>
                                      <td colspan="2" style="padding-top:4px;color:#4b5563;font-size:13px;line-height:18px;">{detail_line} • {game.location}</td>
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
            "Sun Devil students are busy on the courts, fields, and stages this week with {sport_count} events on the calendar.",
            "It's a full campus schedule with {sport_count} chances to watch our athletes compete and our performers share their work.",
            "From rehearsals to walkthroughs, students have prepared for {sport_count} games and performances this week.",
            "Take a look at the {sport_count} competitions and shows happening around Kent Denver and stop by when you can.",
            "Our community comes together for {sport_count} athletic and arts events this week, and every clap or quiet audience helps.",
            "Here is what is happening: {sport_count} events that highlight how our students balance practices, classes, and creativity.",
            "We have {sport_count} upcoming games and performances that reflect the time our students have invested this season.",
            "It is another busy stretch on campus with {sport_count} events where Sun Devils play, perform, and support one another.",
            "Fields, courts, rehearsal rooms, and stages are active this week with {sport_count} student-led events.",
            "Thanks for checking the schedule; {sport_count} competitions and performances await over the next few days."
        ]
    else:
        # Hero texts when there are ONLY sports (no arts events)
        hero_texts = [
            "Sun Devil teams have {sport_count} games this week, and we appreciate every familiar face on the sidelines.",
            "It's a steady slate of {sport_count} matchups across campus and around Colorado.",
            "Here is a look at {sport_count} contests our athletes have been preparing for this week.",
            "Practice has been focused, and now {sport_count} games are on deck.",
            "This week features {sport_count} competitions that show how hard our teams have been working.",
            "We have {sport_count} games ahead, and every cheer or quick check in makes a difference.",
            "It is another busy stretch for Kent Denver athletics with {sport_count} scheduled matchups.",
            "Keep an eye on these {sport_count} games and drop by if you are nearby.",
            "Our athletes step into {sport_count} contests this week, and encouragement goes a long way.",
            "Sharing this list of {sport_count} games helps rides, cheering sections, and coverage come together."
        ]

    # CTA text variations - Different sets for sports-only vs sports+arts
    if has_arts_events:
        # CTA texts when there are BOTH sports and arts events
        cta_texts = [
            "Stay for a quarter, a song, or one scene when you can; students notice familiar faces.",
            "If you know someone performing or competing, share the schedule so they have company in the stands.",
            "Offer a ride, snap a quick photo, or send a text afterward to let students know you saw their work.",
            "Spread the word about these games and shows so classmates and families can plan together.",
            "Check with coaches or directors if you have time to help with scorekeeping, tickets, or simple setup.",
            "Bring someone who has never been to a Kent Denver event and show them what an ordinary week looks like.",
            "If travel keeps you away, send a note of encouragement or share a highlight with the team or ensemble.",
            "A simple clap or quiet cheer is enough; the goal is to let students know their effort is seen.",
            "Consider staying a few minutes after an event to thank staff or help reset equipment.",
            "Share photos or quick recaps so performers and athletes feel the community following along."
        ]
    else:
        # CTA texts when there are ONLY sports (no arts events)
        cta_texts = [
            "Stop by for a half, an inning, or even a few serves; athletes notice support.",
            "Share the schedule with teammates' families so carpools and cheering sections are easy to build.",
            "Offer a ride or help gather gear after games if you have a few minutes.",
            "If you cannot attend, send a quick note to the team wishing them luck.",
            "Check with coaches about small volunteer needs like scoreboard help or snacks.",
            "Bring a classmate or neighbor who has not seen Sun Devil athletics yet.",
            "Post or forward final scores so the community stays informed.",
            "A calm word on the sideline can help students reset between plays.",
            "Stick around to thank officials and staff who make these games possible.",
            "Wear school colors during the week so athletes know the community is thinking about them."
        ]

    # Intro text variations - Different sets for sports-only vs sports+arts
    if has_arts_events:
        # Intro texts when there are BOTH sports and arts events
        intro_texts = [
            "These are the games and performances on the calendar this week, grouped by day for quick reference.",
            "Use this list to plan carpools, coordinate call times, or simply know where students will be.",
            "Times and locations can shift, so double check details with the team or ensemble before leaving.",
            "Feel free to forward this rundown to grandparents, siblings, or friends who want to follow along.",
            "We include both athletics and arts so you can see how the week fits together.",
            "Bookmark this note if you are tracking rehearsals, contests, and travel in one place.",
            "Thank you for being flexible when events are added or weather creates last minute changes.",
            "Let us know if you spot a correction so we can keep the shared schedule accurate.",
            "Showing up for even one of these events helps keep the community connected.",
            "If you take photos or capture sound, please share them with the students and coaches afterward."
        ]
    else:
        # Intro texts when there are ONLY sports (no arts events)
        intro_texts = [
            "These are the games on the calendar this week, organized by day for easy planning.",
            "Use this schedule to line up rides, meals, and meetups around each matchup.",
            "Times and locations can change, so confirm details with the coaching staff before leaving.",
            "Forward this email to families or classmates who might want to follow along.",
            "We highlight every level so you can see how the week flows from middle school to varsity.",
            "Bookmark this note if you are tracking practice wrap ups, travel plans, and game times.",
            "Thanks for being patient when weather or brackets require quick adjustments.",
            "Send updates our way if you notice a typo or a result that should be added.",
            "Showing up for even a portion of a game helps students feel supported.",
            "If you capture photos or film, share them with the team so everyone can relive the moment."
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
        "Plan Your Week",
        "Share The Schedule",
        "Bring A Friend",
        "Offer A Ride",
        "Check Directions",
        "Mark Your Calendar",
        "Send Encouragement",
        "Help On Game Day",
        "Stay For A Bit",
        "Pitch In"
    ]

    # CTA header variations (10) - More creative and Kent Denver specific
    cta_headers = [
        "Thanks For Showing Up",
        "Bring Someone Along",
        "Small Crowds Matter",
        "Faces In The Stands",
        "Support On And Off Campus",
        "Quiet Cheers Count",
        "Neighbors In The Seats",
        "Help When You Can",
        "Keep The Updates Coming",
        "Sun Devils Notice"
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
    total_events = len(all_events)
    home_events = sum(1 for event in all_events if getattr(event, 'is_home', False))
    away_events = total_events - home_events
    arts_events_count = sum(1 for event in all_events if isinstance(event, Event))

    summary_metrics = [
        {'label': 'Events Scheduled', 'value': total_events, 'color': '#041e42'}
    ]
    if home_events:
        summary_metrics.append({'label': 'Home On Campus', 'value': home_events, 'color': '#13cf97'})
    if away_events:
        summary_metrics.append({'label': 'Travel / Away', 'value': away_events, 'color': '#a11919'})
    if arts_events_count:
        summary_metrics.append({'label': 'Performances', 'value': arts_events_count, 'color': '#0066ff'})

    metric_width = max(25, int(100 / len(summary_metrics))) if summary_metrics else 25
    summary_cells = ''.join(
        f'''
                <td class="stack" width="{metric_width}%" valign="top" style="padding:8px;">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" height="140" style="height:140px;border:1px solid #e1e4eb;border-radius:12px;background:#ffffff;">
                    <tr>
                      <td height="140" style="height:140px;padding:16px 14px;text-align:left;">
                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="height:100%;">
                          <tr>
                            <td style="font-size:12px;letter-spacing:.18em;color:{metric['color']};text-transform:uppercase;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-weight:600;">
                              {metric['label']}
                            </td>
                          </tr>
                          <tr>
                            <td style="padding-top:10px;color:#041e42;font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;font-size:24px;line-height:28px;font-weight:600;">
                              {metric['value']}
                            </td>
                          </tr>
                        </table>
                      </td>
                    </tr>
                  </table>
                </td>'''
        for metric in summary_metrics
    )

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
      @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@600;700&family=Red+Hat+Text:wght@400;500;600&display=swap');

      body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
      table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
      img {{ -ms-interpolation-mode: bicubic; border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; }}
      table {{ border-collapse: collapse !important; }}
      body {{ margin: 0 !important; padding: 0 !important; background-color: #f5f5f5; color: #1f2933; font-family: 'Red Hat Text', 'Helvetica Neue', Arial, sans-serif; }}

      .hero-title {{ font-family: 'Crimson Pro', Georgia, 'Times New Roman', serif; font-size: 30px; line-height: 34px; }}
      .day-title {{ font-family: 'Crimson Pro', Georgia, 'Times New Roman', serif; }}
      .inner {{ width: 92%; max-width: 720px; margin: 0 auto; }}
      .stack {{ display: table-cell; vertical-align: top; }}
      .pad {{ padding: 28px 0; }}
      a {{ color: #041e42; text-decoration: underline; }}

      #outlook a {{ padding: 0; }}
      .ReadMsgBody {{ width: 100%; }}
      .ExternalClass {{ width: 100%; }}
      .ExternalClass, .ExternalClass p, .ExternalClass span, .ExternalClass font, .ExternalClass td, .ExternalClass div {{ line-height: 100%; }}
      #bodyTable {{ margin: 0; padding: 0; width: 100% !important; line-height: 100% !important; }}

      @media only screen and (max-width: 600px) {{
        .stack {{ display: block !important; width: 100% !important; }}
        .pad {{ padding: 18px 0 !important; }}
        .inner {{ width: 94% !important; max-width: 94% !important; }}
        .hero-title {{ font-size: 26px !important; line-height: 32px !important; }}
      }}
    </style>
    <!--[if mso]>
    <style type="text/css">
      .fallback-font {{ font-family: Arial, sans-serif !important; }}
    </style>
    <![endif]-->
  </head>
  <body style="margin:0;padding:0;background:#f5f5f5;">
    <!-- Preheader (hidden) -->
    <div style="display:none;visibility:hidden;opacity:0;color:transparent;height:0;width:0;overflow:hidden;mso-hide:all;font-size:1px;line-height:1px;max-height:0px;max-width:0px;">
      {school_level + " " if school_level else ""}Games this week {date_range} — {sports_list}. Thanks for supporting our students.
    </div>

    <!-- Full-bleed outer wrapper -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;">
      <tr>
        <td align="center">

          <!-- HERO -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;">
            <tr>
              <td>
                <table role="presentation" class="inner" align="center" width="720" cellpadding="0" cellspacing="0" style="width:92%;max-width:720px;margin:0 auto;">
                  <tr>
                    <td class="pad" style="padding:30px 0 18px 0;">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e1e4eb;border-radius:18px;background:#ffffff;">
                        <tr>
                          <td style="padding:28px 32px 24px 32px;">
                            <img src="{KDS_PRIMARY_LOGO_URL}" alt="Kent Denver School" width="140" style="display:block;margin-bottom:12px;" border="0" />
                            <div style="font-size:11px;letter-spacing:.28em;color:#0066ff;text-transform:uppercase;margin-bottom:6px;">Weekly Update</div>
                            <h1 class="hero-title fallback-font" style="margin:0 0 10px 0;color:#041e42;font-weight:700;">
                              {text_variations['title_text']}{title_suffix}
                            </h1>
                            <p style="margin:0;color:#4b5563;font-size:15px;line-height:24px;">
                              {text_variations['hero_text'].format(sport_count=sport_count)}
                            </p>
                            <div style="margin-top:18px;">
                              <span style="display:inline-block;padding:8px 14px;border-radius:999px;background:#f2b900;color:#041e42;font-size:12px;font-weight:600;letter-spacing:.2em;text-transform:uppercase;">
                                {date_range}
                              </span>
                            </div>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>

          <!-- SNAPSHOT -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;">
            <tr>
              <td>
                <table role="presentation" class="inner" align="center" width="720" cellpadding="0" cellspacing="0" style="width:92%;max-width:720px;margin:0 auto;">
                  <tr>
                    <td class="pad" style="padding:0 0 22px 0;">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                        <tr>
{summary_cells}
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>

          <!-- INTRO TEXT -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;">
            <tr>
              <td>
                <table role="presentation" class="inner" align="center" width="720" cellpadding="0" cellspacing="0" style="width:92%;max-width:720px;margin:0 auto;">
                  <tr>
                    <td class="pad" style="padding:0 0 26px 0;">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e1e4eb;border-radius:14px;background:#ffffff;">
                        <tr>
                          <td style="padding:20px 24px;">
                            <h2 style="margin:0 0 6px 0;color:#041e42;font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;font-weight:600;font-size:22px;line-height:26px;">
                              This week at a glance
                            </h2>
                            <p style="margin:0;color:#4b5563;font-size:14px;line-height:22px;">
                              {text_variations['intro_text']}
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

        # Add subtle spacing between days
        if i > 0:
            html += '''
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;">
            <tr>
              <td>
                <table role="presentation" class="inner" align="center" width="720" cellpadding="0" cellspacing="0" style="width:92%;max-width:720px;margin:0 auto;">
                  <tr>
                    <td style="padding:8px 0;"></td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
'''

        html += f'''
          <!-- {formatted_date.upper()} -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;">
            <tr>
              <td>
                <table role="presentation" class="inner" align="center" width="720" cellpadding="0" cellspacing="0" style="width:92%;max-width:720px;margin:0 auto;">
                  <tr>
                    <td class="pad" style="padding:6px 0 0 0;">
                      <div style="font-size:12px;letter-spacing:.22em;color:#9297a3;text-transform:uppercase;">{date_obj.strftime('%A')}</div>
                      <h3 class="day-title" style="margin:4px 0 14px 0;color:#041e42;font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;font-weight:600;font-size:20px;line-height:24px;">
                        {formatted_date}
                      </h3>
                    </td>
                  </tr>
                  <tr>
                    <td class="pad" style="padding:0 0 26px 0;">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e1e4eb;border-radius:14px;background:#ffffff;">
                        <tr>
                          <td style="padding:18px 22px;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
'''

        if not has_games:
            html += '''
                              <tr>
                                <td>
                                  <p style="margin:4px 0;color:#6b7280;font-size:14px;line-height:20px;">No events scheduled.</p>
                                </td>
                              </tr>
'''
        else:
            if featured_games:
                html += '''
                              <tr>
                                <td style="padding-bottom:8px;">
                                  <div style="font-size:12px;letter-spacing:.28em;color:#a11919;text-transform:uppercase;">Spotlight</div>
                                </td>
                              </tr>
'''
                for item in featured_games:
                    if isinstance(item, Event):
                        html += generate_featured_event_card_html(item)
                    else:
                        html += generate_featured_game_card_html(item)

            if other_games:
                label = "Schedule" if not featured_games else "Also on the schedule"
                html += f'''
                              <tr>
                                <td style="padding:{'14px' if featured_games else '0'} 0 6px 0;">
                                  <div style="font-size:12px;letter-spacing:.22em;color:#9297a3;text-transform:uppercase;">{label}</div>
                                </td>
                              </tr>
'''
                for item in other_games:
                    if isinstance(item, Event):
                        html += generate_other_event_list_item_html(item)
                    else:
                        html += generate_other_game_list_item_html(item)

        html += '''                            </table>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
'''

    # Call to Action and Footer
    html += f'''

          <!-- CALL TO ACTION -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;">
            <tr>
              <td>
                <table role="presentation" class="inner" align="center" width="720" cellpadding="0" cellspacing="0" style="width:92%;max-width:720px;margin:0 auto;">
                  <tr>
                    <td class="pad" style="padding:0 0 28px 0;">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-radius:14px;border:1px solid #e1e4eb;background:#ffffff;">
                        <tr>
                          <td style="padding:20px 24px;">
                            <div style="font-size:12px;letter-spacing:.22em;color:#13cf97;text-transform:uppercase;">{text_variations['cta_button_text']}</div>
                            <div style="margin:10px 0 6px 0;color:#041e42;font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;font-weight:600;font-size:22px;line-height:26px;">
                              {text_variations['cta_header_text']}
                            </div>
                            <p style="margin:0;color:#4b5563;font-size:14px;line-height:22px;">
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
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;">
            <tr>
              <td>
                <table role="presentation" class="inner" align="center" width="720" cellpadding="0" cellspacing="0" style="width:92%;max-width:720px;margin:0 auto;">
                  <tr>
                    <td class="pad" style="padding:0 0 40px 0;">
                      <p style="margin:0 0 8px 0;color:#4b5563;font-size:13px;line-height:20px;">
                        For complete schedules, directions, and updates, <a href="https://www.kentdenver.org/athletics-wellness/schedules-and-scores" style="color:#041e42;text-decoration:underline;">visit our athletics page</a>.
                      </p>
                      <p style="margin:0;color:#9aa1ab;font-size:12px;line-height:18px;">
                        — Student Leadership Media Team
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
  </body>
</html>'''

    return html

if __name__ == '__main__':
    main()
