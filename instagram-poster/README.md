# Kent Denver Instagram Daily Carousel Generator

Generates a branded daily carousel for Instagram (`1080x1350`, 4:5), with one slide per day in the selected week/range.

## What this includes

- **Shared generator module** (`poster_generator.py`) for:
  - weekly/custom date range selection
  - fetching athletics + arts events from `sports-emails/generate_games.py`
  - merging custom events
  - building daily slide models (one poster per day)
  - rendering a complete carousel HTML document
- **CLI script** (`generate_instagram_poster.py`) for static carousel HTML generation
- **Local GUI** (`app.py`) to:
  - fetch source events
  - add/edit/remove custom events
  - preview daily slides with next/prev controls
  - download current slide PNG or all daily slide PNGs

## Install

From repository root:

```bash
pip3 install -r sports-emails/requirements.txt
pip3 install -r instagram-poster/requirements.txt
```

## Run the GUI

```bash
cd instagram-poster
python3 app.py
```

Open: [http://127.0.0.1:5050](http://127.0.0.1:5050)

### GUI flow

1. Choose week mode (`Next Week`, `This Week`, or `Custom Range`)
2. Click **Fetch Source Events**
3. Add any custom events (robotics, speech & debate, admissions, etc.)
4. Click **Refresh Carousel**
5. Use **Prev/Next** to review each day slide
6. Export with **Download All Slides**

## Run as script

Generate static carousel HTML with one day slide per day in range:

```bash
cd instagram-poster
python3 generate_instagram_poster.py --next-week
```

Optional flags:

```bash
python3 generate_instagram_poster.py \
  --start-date 2026-03-09 \
  --end-date 2026-03-15 \
  --custom-events custom-events.json \
  --heading "This Week at Kent Denver" \
  --output-html carousel.html
```

## Custom events JSON format

```json
[
  {
    "title": "Speech & Debate Tournament",
    "date": "2026-03-12",
    "time": "8:00 AM",
    "location": "Boulder Prep",
    "category": "Academics",
    "subtitle": "Regional Qualifier",
    "badge": "SPECIAL",
    "priority": 4,
    "accent": "#8C6A00"
  }
]
```

## Tests

```bash
python3 -m unittest discover -s instagram-poster/tests -p 'test_*.py'
```
