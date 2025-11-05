# Kent Denver Digital Signage

Automated daily display of Kent Denver games and performances for digital signage around the school.

## Overview

This system automatically generates a daily HTML page (optimized for 2500x1650px displays) showing today's sports games and arts events. The page updates every day at midnight Denver time via GitHub Actions.

## Features

- **Daily Updates**: Automatically fetches and displays today's events
- **Card-Based Design**: Similar styling to the email system with featured and regular events
- **Automatic Deployment**: GitHub Actions updates the page daily
- **Cloudflare Pages Integration**: Serves the HTML via Cloudflare Pages

## Display Specifications

- **Size**: 2500 x 1650 pixels
- **Aspect Ratio**: ~3:2 (optimized for digital signage displays)
- **Format**: Static HTML with embedded CSS

## How It Works

1. **Daily Schedule**: GitHub Actions runs at midnight Denver time (6 AM UTC)
2. **Fetch Events**: Script fetches today's games from athletics website and arts events from iCal feed
3. **Generate HTML**: Creates `index.html` with today's events in card format
4. **Commit Changes**: Automatically commits the updated HTML to the repository
5. **Deploy**: Cloudflare Pages detects the commit and redeploys automatically

## Setup

### Prerequisites

- Python 3.11+
- Dependencies from `sports-emails/requirements.txt`

### Local Testing

Run the generator locally:

```bash
cd digital-signage
python generate_signage.py
```

This will create `index.html` in the `digital-signage` directory.

### Cloudflare Pages Setup

1. Connect your GitHub repository to Cloudflare Pages
2. Set the **Build output directory** to: `digital-signage`
3. Leave build command empty (static HTML)
4. Deploy!

The page will automatically redeploy whenever the GitHub Action commits a new `index.html`.

## Manual Trigger

You can manually trigger the signage update from GitHub:

1. Go to **Actions** tab in your repository
2. Select **Update Digital Signage** workflow
3. Click **Run workflow**

## File Structure

```
digital-signage/
├── generate_signage.py    # Main generator script
├── index.html             # Generated daily (auto-updated)
└── README.md              # This file
```

## Customization

### Display Size

To change the display size, edit the `body` dimensions in `generate_signage.py`:

```python
body {
    width: 2500px;
    height: 1650px;
    ...
}
```

### Update Schedule

To change when the signage updates, edit `.github/workflows/update-signage.yml`:

```yaml
schedule:
  - cron: '0 6 * * *'  # Change this cron expression
```

## Troubleshooting

### No events showing

- Check that events are published on the Kent Denver athletics website
- Verify the iCal feed is accessible
- Check GitHub Actions logs for errors

### Signage not updating

- Verify GitHub Actions is enabled for your repository
- Check the Actions tab for failed workflow runs
- Ensure the workflow has permission to commit to the repository

## Author

Jacob Barkin (jbarkin28@kentdenver.org)

