# WFMU Blog Archive Tool

A comprehensive archiving solution for preserving the WFMU blog (blog.wfmu.org) before it shuts down. This tool scrapes the entire blog history, downloads media files, parses content, creates a searchable archive, and provides a modern web interface for viewing the preserved content.

## Features

- **Complete Blog Scraping**: Archives all posts, pages, and categories
- **Media Preservation**: Downloads all images, audio files, and other media
- **Content Extraction**: Converts HTML to clean text and Markdown formats
- **Full-Text Search**: Creates a searchable index using Whoosh
- **Database Storage**: SQLite database for easy portability
- **Integrity Verification**: Checks for missing posts and media files
- **Export Options**: JSON export for further processing
- **Web Viewer Interface**: Modern, responsive web interface with:
  - Live search as you type
  - Multiple view modes (Card, List, Timeline)
  - Dual viewing: Modern redesign or original HTML preservation
  - Media playback for archived audio files

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd wfmu

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### Archive the Blog

To run the complete archiving process:

```bash
# Using the paginated scraper (recommended - faster)
python scraper_paginated.py

# Or use the all-in-one tool
python archive_wfmu.py full-archive
```

This will:
1. Scrape all blog posts and pages
2. Download all media files
3. Parse content to extract clean text
4. Build a searchable index
5. Verify archive integrity

### View the Archive

Once you have some posts archived, launch the web viewer:

```bash
python viewer.py
```

Then open your browser to: http://localhost:5000

The viewer provides:
- Browse all archived posts
- Live search functionality
- Toggle between modern and original HTML views
- View and play archived media files

## Usage

The tool provides several commands for different tasks:

### Scraping Posts

```bash
# Scrape all posts
python archive_wfmu.py scrape

# Resume from last position
python archive_wfmu.py scrape --resume

# Only scrape category pages
python archive_wfmu.py scrape --categories-only
```

### Downloading Media

```bash
# Download all media files
python archive_wfmu.py download-media

# Retry failed downloads
python archive_wfmu.py download-media --retry-failed
```

### Processing Content

```bash
# Parse HTML to extract clean text
python archive_wfmu.py parse-content

# Build search index
python archive_wfmu.py build-index
```

### Searching the Archive

```bash
# Search for posts
python archive_wfmu.py search "music"

# Limit results
python archive_wfmu.py search "radio show" --limit 20
```

### Verification and Statistics

```bash
# Show archive statistics
python archive_wfmu.py stats

# Verify archive integrity
python archive_wfmu.py verify

# Export posts to JSON
python archive_wfmu.py export-json
```

## Database Schema

The archive uses SQLite with the following main tables:

- **posts**: Raw HTML, parsed content, metadata
- **categories**: Blog categories and post counts
- **media**: Media files with download status
- **comments**: User comments on posts
- **scrape_progress**: Tracking scraping status

## File Structure

```
wfmu/
├── wfmu_archive.db       # SQLite database with all posts
├── media/                # Downloaded media files
│   ├── images/
│   ├── audio/
│   ├── video/
│   └── documents/
├── search_index/         # Whoosh search index
├── templates/            # HTML templates for viewer
│   ├── index.html       # Main browsing interface
│   └── post.html        # Individual post viewer
├── static/               # Static assets for viewer
│   ├── css/style.css    # Modern UI styles
│   └── js/app.js        # Interactive features
├── scraper_paginated.py # Fast pagination-based scraper
├── viewer.py            # Flask web application
└── archive_report.json   # Verification report
```

## Archive Statistics

The tool provides detailed statistics including:
- Total posts archived
- Media files downloaded
- Date range of posts
- Categories and authors
- Comments preserved

## Considerations

- **Respectful Scraping**: The tool includes delays between requests
- **Incremental Updates**: Can resume from interruptions
- **Error Handling**: Retries failed downloads
- **Storage**: Full archive may require several GB of space
- **Time**: Complete archiving may take several hours

## Output Formats

The archived data can be accessed in multiple ways:

1. **SQLite Database**: Direct SQL queries for analysis
2. **JSON Export**: Structured data for web applications
3. **Search Index**: Full-text search capabilities
4. **Raw HTML**: Original post content preserved
5. **Markdown**: Clean, portable text format

## Viewer Features

The web viewer (`viewer.py`) provides a modern interface to browse the archive:

### Search
- **Live Search**: Results appear instantly as you type
- **Full-Text Search**: Search post titles, content, and authors
- **Highlighted Matches**: Search terms are highlighted in results

### View Modes
- **Card View**: Visual grid layout with previews
- **List View**: Compact list for scanning many posts
- **Timeline View**: Posts grouped by month/year

### Post Viewing
- **Modern View**: Clean, readable redesign with:
  - Formatted text and markdown rendering
  - Embedded media players
  - Category tags and metadata
  - Comments section
- **Original View**: Preserved HTML exactly as it appeared on the blog
- **Seamless Switching**: Toggle between views with one click

### Media Support
- **Images**: Displayed inline, click to enlarge
- **Audio**: Built-in MP3 player for archived audio
- **Download Links**: Access original media files

## Current Status

The scraper runs continuously to archive the entire blog. You can monitor progress by checking the database:

```bash
python -c "from database import init_database, Post; s,_=init_database(); print(f'Posts archived: {s.query(Post).count()}')"
```

## Next Steps

Once archived, you can:
- Use the built-in viewer to browse and search
- Export to static HTML for permanent hosting
- Build custom applications using the SQLite database
- Create data visualizations of blog history
- Import into other content management systems

## License

This archiving tool is provided for preservation purposes. Please respect the original content creators and WFMU's copyright.