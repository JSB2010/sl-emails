# "Load More" Button Implementation

## Overview
The scraping system now uses a **two-stage approach** to handle the "Load More" button on the Kent Denver athletics schedule page, ensuring all future events are captured even when they're not initially visible.

## How It Works

### Stage 1: Quick Fetch (BeautifulSoup)
- **Fast**: Uses simple HTTP request
- **Best for**: Near-term events (next 1-2 weeks)
- **Process**:
  1. Fetches the initial page HTML
  2. Parses visible events
  3. Checks if events cover the requested date range
  4. If successful → Done! ✅
  5. If not → Proceeds to Stage 2

### Stage 2: Deep Fetch (Selenium)
- **Thorough**: Uses browser automation
- **Best for**: Far-future events (months ahead)
- **Process**:
  1. Opens page in headless Chrome browser
  2. Clicks "Load More" button repeatedly
  3. Continues until:
     - Events cover the requested date range, OR
     - "Load More" button disappears (all events loaded)
  4. Parses all loaded events
  5. Returns complete results

## When Stage 2 Activates

Stage 2 is triggered when:
- ❌ No events found in the requested date range
- ❌ Latest event date is before the requested end date

## GitHub Actions Compatibility

✅ **Fully compatible** with GitHub Actions workflows!

Both workflows now include:
```yaml
- name: Install Chrome dependencies
  run: |
    sudo apt-get update
    sudo apt-get install -y chromium-browser chromium-chromedriver
```

This ensures Chrome is available for Selenium when needed.

## Performance

| Scenario | Method Used | Speed |
|----------|-------------|-------|
| Next week's events | Stage 1 only | ⚡ Fast (~2 seconds) |
| Events 1 month out | Stage 2 | 🔄 Moderate (~10-15 seconds) |
| Events 3+ months out | Stage 2 | 🔄 Moderate (~15-30 seconds) |

## Benefits

1. ✅ **Efficient**: Uses fast method when possible
2. ✅ **Reliable**: Falls back to thorough method when needed
3. ✅ **Future-proof**: Can fetch events months in advance
4. ✅ **GitHub Actions ready**: Works in automated workflows
5. ✅ **Smart**: Only uses Selenium when necessary

## Technical Details

### New Dependencies
- `selenium>=4.0.0` - Browser automation
- `webdriver-manager>=4.0.0` - Automatic ChromeDriver management

### New Functions
- `parse_games_from_soup()` - Shared parsing logic
- `scrape_athletics_schedule_with_selenium()` - Stage 2 implementation
- `scrape_athletics_schedule()` - Two-stage coordinator (updated)

### Safety Features
- Maximum 50 "Load More" clicks (prevents infinite loops)
- Proper error handling and fallbacks
- Headless mode for server environments
- Automatic driver cleanup

## Usage

No changes needed! The function signature remains the same:

```python
games = scrape_athletics_schedule(start_date='2025-11-10', end_date='2025-11-16')
```

The system automatically chooses the best approach based on what's needed.

## Console Output Examples

### Stage 1 Success:
```
📥 Stage 1: Quick fetch with BeautifulSoup...
✅ Stage 1 successful! Found 12 games covering the date range
```

### Stage 2 Activation:
```
📥 Stage 1: Quick fetch with BeautifulSoup...
⚠️  Stage 1: Latest event is 2025-11-30, but need events until 2026-02-15
🔄 Moving to Stage 2: Selenium with 'Load More' clicking...
🔄 Using Selenium to load more events...
   Clicked 'Load More' (1 times)...
   Clicked 'Load More' (2 times)...
   Clicked 'Load More' (3 times)...
✅ Found events up to 2026-02-20, which covers requested range
```

## Testing

To test the implementation locally:

```bash
# Install dependencies
cd sports-emails
pip install -r requirements.txt

# Test with near-term dates (should use Stage 1)
python generate_games.py --start-date 2025-11-10 --end-date 2025-11-16

# Test with far-future dates (should use Stage 2)
python generate_games.py --start-date 2026-02-01 --end-date 2026-02-28
```

## Troubleshooting

If Selenium fails:
1. Check Chrome/Chromium is installed
2. Verify ChromeDriver is compatible with Chrome version
3. Check console output for specific error messages
4. System will fall back gracefully (returns empty list with error message)

