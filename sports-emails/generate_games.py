#!/usr/bin/env python3
"""
Kent Denver Games Email Generator

This script scrapes the Kent Denver athletics website and generates a weekly games email
with the same styling and layout as the existing games-week.html template.

Usage:
    python generate_games_email.py --start-date "2025-09-22" --end-date "2025-09-27"
"""

import argparse
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from typing import List, Dict, Optional
import sys
import os

# Sport emoji and color mappings
SPORT_CONFIG = {
    'soccer': {'emoji': '⚽', 'color': 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)'},
    'football': {'emoji': '🏈', 'color': 'linear-gradient(135deg, #dc2626 0%, #991b1b 100%)'},
    'tennis': {'emoji': '🎾', 'color': 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)'},
    'golf': {'emoji': '⛳', 'color': 'linear-gradient(135deg, #eab308 0%, #ca8a04 100%)'},
    'cross country': {'emoji': '🏃', 'color': 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)'},
    'field hockey': {'emoji': '🏑', 'color': 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)'},
    'volleyball': {'emoji': '🏐', 'color': 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'},
    'basketball': {'emoji': '🏀', 'color': 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)'},
    'lacrosse': {'emoji': '🥍', 'color': 'linear-gradient(135deg, #10b981 0%, #059669 100%)'},
    'baseball': {'emoji': '⚾', 'color': 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)'},
    'swimming': {'emoji': '🏊', 'color': 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)'},
    'track': {'emoji': '🏃', 'color': 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)'},
    'ice hockey': {'emoji': '🏒', 'color': 'linear-gradient(135deg, #64748b 0%, #475569 100%)'},
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
        
    def get_sport_config(self) -> Dict[str, str]:
        """Get emoji and color for the sport"""
        for sport_key, config in SPORT_CONFIG.items():
            if sport_key in self.sport:
                return config
        # Default fallback
        return {'emoji': '🏆', 'color': 'linear-gradient(135deg, #6b7280 0%, #4b5563 100%)'}
    
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

def group_games_by_date(games: List[Game]) -> Dict[str, List[Game]]:
    """Group games by date"""
    games_by_date = {}
    
    for game in games:
        date_key = game.date
        if date_key not in games_by_date:
            games_by_date[date_key] = []
        games_by_date[date_key].append(game)
    
    return games_by_date

def generate_game_card_html(game: Game) -> str:
    """Generate HTML for a single game card"""
    sport_config = game.get_sport_config()
    home_away_style = game.get_home_away_style()

    # Emphasize home games with bold team name and home icon
    if game.is_home:
        team_style = "font-weight:900;"  # Extra bold for home games
        home_indicator = " 🏠"  # Home icon
        card_border = "border:2px solid #dcfce7;"  # Subtle green border for home games
    else:
        team_style = "font-weight:800;"  # Normal bold for away games
        home_indicator = ""
        card_border = "border:1px solid #e6eaf2;"  # Normal border

    return f'''
    <td class="stack" width="50%" valign="top" style="padding:8px 10px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-radius:8px;{card_border}background:#ffffff;">
        <tr><td style="height:12px;background:{sport_config['color']};border-top-left-radius:8px;border-top-right-radius:8px;"></td></tr>
        <tr>
          <td style="padding:16px 18px 14px 18px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:8px;">
              <tr>
                <td style="width:28px;vertical-align:middle;">
                  <span style="font-size:20px;">{sport_config['emoji']}</span>
                </td>
                <td style="vertical-align:middle;">
                  <div style="display:inline-block;padding:4px 10px;border-radius:4px;background:{home_away_style['background']};color:{home_away_style['color']};font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-weight:700;font-size:11px;letter-spacing:.3px;text-transform:uppercase;">{game.time} • {home_away_style['text']}</div>
                </td>
              </tr>
            </table>
            <div style="color:#041e42;font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;{team_style}font-size:19px;line-height:23px;margin-bottom:4px;">{game.team}{home_indicator}</div>
            <p style="margin:0;color:#374151;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-size:15px;line-height:20px;font-weight:600;">
              vs. <strong style="color:#041e42;">{game.opponent}</strong>
            </p>
            <p style="margin:4px 0 0 0;color:#6b7280;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-size:13px;line-height:18px;">
              📍 {game.location}
            </p>
          </td>
        </tr>
      </table>
    </td>'''

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
    parser.add_argument('--output-ms',
                       help='Middle school output filename with path (auto-generated in week folder if not specified)')
    parser.add_argument('--output-us',
                       help='Upper school output filename with path (auto-generated in week folder if not specified)')

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

    # Create folder for the week
    folder_name = date_str
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"Created folder: {folder_name}")

    if not args.output_ms:
        args.output_ms = os.path.join(folder_name, f'games-week-middle-school-{date_str}.html')
    if not args.output_us:
        args.output_us = os.path.join(folder_name, f'games-week-upper-school-{date_str}.html')

    print(f"Generating games emails for {date_source}: {start_date} to {end_date}")

    print(f"Scraping games from {start_date} to {end_date}...")
    games = scrape_athletics_schedule(start_date, end_date)

    if not games:
        print("No games found for the specified date range.")
        sys.exit(1)

    print(f"Found {len(games)} total games")

    # Separate games by school level
    middle_school_games, upper_school_games = separate_games_by_school(games)

    print(f"Middle School: {len(middle_school_games)} games")
    print(f"Upper School: {len(upper_school_games)} games")

    # Generate date range string
    date_range = format_date_range(start_date, end_date)

    # Generate Middle School email
    if middle_school_games:
        ms_games_by_date = group_games_by_date(middle_school_games)
        ms_sports = set(game.sport for game in middle_school_games)
        ms_sports_list = ', '.join(sport.title() for sport in sorted(ms_sports))

        print(f"Generating Middle School email for {len(ms_games_by_date)} days with {len(ms_sports)} sports...")
        ms_html_content = generate_html_email(ms_games_by_date, date_range, ms_sports_list,
                                            start_date, end_date, "Middle School")

        with open(args.output_ms, 'w', encoding='utf-8') as f:
            f.write(ms_html_content)

        print(f"✅ Middle School email generated: {args.output_ms}")
    else:
        print("⚠️  No Middle School games found")

    # Generate Upper School email
    if upper_school_games:
        us_games_by_date = group_games_by_date(upper_school_games)
        us_sports = set(game.sport for game in upper_school_games)
        us_sports_list = ', '.join(sport.title() for sport in sorted(us_sports))

        print(f"Generating Upper School email for {len(us_games_by_date)} days with {len(us_sports)} sports...")
        us_html_content = generate_html_email(us_games_by_date, date_range, us_sports_list,
                                            start_date, end_date, "Upper School")

        with open(args.output_us, 'w', encoding='utf-8') as f:
            f.write(us_html_content)

        print(f"✅ Upper School email generated: {args.output_us}")
    else:
        print("⚠️  No Upper School games found")

def generate_html_email(games_by_date: Dict[str, List[Game]], date_range: str,
                       sports_list: str, start_date: str, end_date: str, school_level: str = "") -> str:
    """Generate the complete HTML email"""

    # HTML header and hero section
    title_suffix = f" — {school_level}" if school_level else ""
    html = f'''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en" style="margin:0;padding:0;">
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="x-apple-disable-message-reformatting" />
    <meta name="format-detection" content="telephone=no,address=no,email=no,date=no,url=no" />
    <title>Kent Denver — Games This Week ({date_range}){title_suffix}</title>
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

      /* Mobile Styles */
      @media only screen and (max-width: 600px) {{
        .stack {{ display: block !important; width: 100% !important; }}
        .pad {{ padding: 16px !important; }}
        .hero-title {{ font-size: 28px !important; line-height: 34px !important; }}
        .inner {{ width: 92% !important; }}
        .game-time {{ font-size: 12px !important; }}
        .mobile-center {{ text-align: center !important; }}
        .mobile-hide {{ display: none !important; }}
      }}

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
                        Games This Week{title_suffix}
                      </h1>
                      <table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:8px;">
                        <tr>
                          <td style="background:#ffffff;color:#041e42;border-radius:4px;padding:6px 10px;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-weight:700;font-size:13px;">
                            {date_range}
                          </td>
                        </tr>
                      </table>
                      <p style="margin:12px 0 0 0;color:#d7e3ff;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-size:16px;line-height:24px;">
                        Big week ahead for Sun Devil athletics! Check out all the games below and come support our teams across {len(set(game.sport for games in games_by_date.values() for game in games))} sports. Go Devils! 🔥😈
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
                        Mark your calendars and come cheer on our Sun Devils across all sports and grade levels.
                      </p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
'''

    # Generate content for each day
    sorted_dates = sorted(games_by_date.keys(), key=lambda x: datetime.strptime(x, '%b %d %Y'))

    for i, date_str in enumerate(sorted_dates):
        games_for_date = games_by_date[date_str]

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

        # Day header and games
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
                            <h3 style="margin:0;color:#041e42;font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;font-weight:800;font-size:22px;line-height:26px;">
                              {formatted_date}
                            </h3>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
'''

        # Generate game cards in rows of 2
        for j in range(0, len(games_for_date), 2):
            html += '                  <tr>\n'

            # First game in row
            html += generate_game_card_html(games_for_date[j])

            # Second game in row (or spacer if odd number)
            if j + 1 < len(games_for_date):
                html += generate_game_card_html(games_for_date[j + 1])
            else:
                html += '                    <td class="stack" width="50%" valign="top" style="padding:8px 10px;"></td>'

            html += '\n                  </tr>\n'

        html += '''                </table>
              </td>
            </tr>
          </table>
'''

    # Call to Action and Footer
    html += '''

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
                                  Support Our Teams
                                </td>
                              </tr>
                            </table>
                            <div style="margin-top:10px;color:#041e42;font-family:'Crimson Pro', Georgia, 'Times New Roman', serif;font-weight:800;font-size:24px;line-height:28px;">
                              Go Sun Devils! 🔥😈
                            </div>
                            <p style="margin:10px 0 0 0;color:#373737;font-family:'Red Hat Text', Arial, Helvetica, sans-serif;font-size:15px;line-height:24px;">
                              Come out and cheer on our teams across all sports and grade levels. Your support makes a difference!
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
