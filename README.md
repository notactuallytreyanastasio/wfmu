# WFMU Blog Archive Tool

A comprehensive archiving solution for preserving the WFMU blog (blog.wfmu.org) before it shuts down. This tool scrapes the entire blog history, downloads media files, parses content, creates a searchable archive, and provides a modern web interface for viewing the preserved content.

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start archiving the blog
python scraper_paginated.py

# 3. View the archive
python wfmu_viewer_enhanced.py
# Open http://localhost:8080

# 4. View statistics
python archive_stats.py
# Open http://localhost:8085
```

## 📚 How It Works

### Architecture Overview

The WFMU Archive system consists of several components working together:

```
┌─────────────────────────────────────────────────┐
│                 WFMU Blog Website                │
│              (blog.wfmu.org - source)            │
└─────────────────┬───────────────────────────────┘
                  │ Scraping
                  ▼
┌─────────────────────────────────────────────────┐
│           scraper_paginated.py                   │
│   - Fetches posts via pagination                 │
│   - Extracts metadata & content                  │
│   - Identifies media files                       │
└─────────────────┬───────────────────────────────┘
                  │ Stores
                  ▼
┌─────────────────────────────────────────────────┐
│           SQLite Database                        │
│         (wfmu_archive.db)                        │
│                                                  │
│  Tables:                                         │
│  - posts: Blog posts with content               │
│  - media: Images, audio, video files            │
│  - categories: Blog categories                  │
│  - comments: User comments                      │
│  - scrape_progress: Tracking                    │
└──────┬──────────────────────┬───────────────────┘
       │                      │
       ▼                      ▼
┌──────────────┐      ┌──────────────────┐
│   Viewer     │      │ Media Downloader │
│   (port 8080)│      │ download_images.py│
└──────────────┘      └──────────────────┘
```

### Database Schema

The entire archive is stored in a SQLite database (`wfmu_archive.db`) with the following structure:

#### Posts Table
```sql
CREATE TABLE posts (
    post_id VARCHAR PRIMARY KEY,      -- MD5 hash of URL
    url VARCHAR UNIQUE NOT NULL,      -- Original blog URL
    title TEXT,                       -- Post title
    author VARCHAR,                   -- Author name
    published_date DATETIME,          -- Publication date
    raw_html TEXT,                    -- Original HTML
    content_text TEXT,                -- Extracted text
    content_markdown TEXT,            -- Markdown version
    categories TEXT,                  -- JSON array
    tags TEXT,                        -- JSON array
    scrape_date DATETIME              -- When scraped
)
```

#### Media Table
```sql
CREATE TABLE media (
    id INTEGER PRIMARY KEY,
    post_id VARCHAR,                  -- Links to posts.post_id
    media_type VARCHAR,               -- 'image', 'audio', 'video'
    original_url VARCHAR,             -- Source URL
    local_path VARCHAR,               -- Where file is saved
    filename VARCHAR,                 -- Local filename
    alt_text TEXT,                    -- Image alt text
    caption TEXT,                     -- Media caption
    downloaded BOOLEAN,               -- Download status
    download_error TEXT,              -- Error if failed
    FOREIGN KEY (post_id) REFERENCES posts(post_id)
)
```

## 🔧 Components

### 1. Scraper (`scraper_paginated.py`)

The main scraper that archives the blog:

```bash
python scraper_paginated.py
```

**Features:**
- Uses pagination strategy (/page/2/, /page/3/, etc.)
- Respects rate limits (1 second between requests)
- Extracts all post metadata and content
- Identifies all media files
- Resumes from interruptions
- Handles errors gracefully

**How it works:**
1. Starts from the homepage
2. Follows pagination links to get all posts
3. For each post:
   - Downloads HTML
   - Extracts metadata (title, author, date)
   - Parses content to text/markdown
   - Identifies media files
   - Stores in database

### 2. Media Downloader (`download_images.py`)

Downloads image files respectfully:

```bash
# Test with 10 images
echo "test" | python download_images.py

# Download all images (be respectful!)
echo "yes" | python download_images.py
```

**Features:**
- Rate limiting (0.1s between images)
- Batch processing (100 images per batch)
- 10-second pause between batches
- Resume capability
- Progress tracking

**Current Status:**
- 10,710 total images identified
- 2,263+ downloaded (ongoing)
- ~8,447 remaining

### 3. Audio Downloader (`download_audio.py`)

Downloads MP3/audio files very respectfully (for future use):

```bash
# Test with 5 audio files
echo "test" | python download_audio.py

# Resume downloading where left off
echo "resume" | python download_audio.py

# Start full download (will take 3-4 days)
echo "yes" | python download_audio.py
```

**Features:**
- Very respectful rate limiting (2s between files)
- Batch processing (50 files per batch)
- 30-second pause between batches
- Full resume capability - won't re-download
- Progress tracking with size estimates
- File size display during download

**Current Status:**
- 10,666 total audio files identified
- 87 downloaded (637MB)
- 10,579 remaining
- Estimated ~77GB total storage needed
- Estimated 3-4 days continuous runtime

### 4. Web Viewer (`wfmu_viewer_enhanced.py`)

Modern web interface for browsing the archive:

```bash
python wfmu_viewer_enhanced.py
# Open http://localhost:8080
```

**Features:**
- **Live Search**: Instant results as you type
- **Browse by Date**: Year/month navigation
- **Browse by Author**: Filter by blog authors
- **Pagination**: 50 posts per page
- **Dual View**: Modern redesign or original HTML
- **Archive.org Links**: All external links use Wayback Machine

### 4. Statistics Dashboard (`archive_stats.py`)

Analytics and monitoring:

```bash
python archive_stats.py
# Open http://localhost:8085
```

**Shows:**
- Total posts archived
- Media file statistics
- Timeline visualization
- Author contributions
- Archive completeness

## 📊 Current Archive Status

As of the last run:
- **Posts**: 4,568 archived (2007-2015)
- **Images**: 8,147 identified, 58 downloaded
- **Audio**: 9,105 identified
- **Authors**: Various contributors
- **Date Range**: Missing 2003-2006 (pagination doesn't go that far back)

## 🏗️ Building the Archive

### Step 1: Initial Scraping

```bash
# Start the scraper
python scraper_paginated.py

# This will:
# 1. Create wfmu_archive.db if it doesn't exist
# 2. Begin scraping from page 1
# 3. Continue through all pages
# 4. Extract posts, metadata, and identify media
# 5. Can be interrupted and resumed
```

### Step 2: Download Media (Optional)

```bash
# Download images (respectfully)
python download_images.py

# Choose:
# - "test" for 10 images
# - "yes" for all images
# - "no" to cancel
```

### Step 3: View the Archive

```bash
# Start the viewer
python wfmu_viewer_enhanced.py

# Features available at http://localhost:8080:
# - Search posts
# - Browse by year/month
# - Browse by author
# - View individual posts
# - Access Archive.org versions
```

### Step 4: Monitor Progress

```bash
# View statistics
python archive_stats.py

# Available at http://localhost:8085
```

## 🗂️ File Structure

```
wfmu/
├── wfmu_archive.db           # Main SQLite database
├── wfmu_archive_viewer.db    # Copy for viewer (avoids locks)
├── media/                    # Downloaded media files
│   ├── images/
│   ├── audio/
│   └── video/
├── templates/                # HTML templates
│   ├── index.html           # Main viewer interface
│   └── post.html            # Individual post view
├── static/                   # Static assets
│   ├── css/style.css        # Styles
│   └── js/app.js            # JavaScript
├── scraper_paginated.py     # Main scraper
├── download_images.py       # Image downloader
├── wfmu_viewer_enhanced.py  # Web viewer
├── archive_stats.py         # Statistics dashboard
├── database.py              # Database models (SQLAlchemy)
└── requirements.txt         # Python dependencies
```

## 🔄 Database Operations

### Check Archive Status
```python
import sqlite3
conn = sqlite3.connect('wfmu_archive.db')
cur = conn.cursor()

# Total posts
total = cur.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
print(f"Total posts: {total}")

# Date range
dates = cur.execute("""
    SELECT MIN(published_date), MAX(published_date)
    FROM posts WHERE published_date IS NOT NULL
""").fetchone()
print(f"Date range: {dates[0]} to {dates[1]}")

# Media stats
media = cur.execute("""
    SELECT media_type, COUNT(*), SUM(downloaded)
    FROM media GROUP BY media_type
""").fetchall()
for m in media:
    print(f"{m[0]}: {m[1]} total, {m[2] or 0} downloaded")
```

### Export Data
```bash
# Export posts to JSON
python archive_wfmu.py export-json

# Creates archive_posts.json with all post data
```

### Backup Database
```bash
# Create backup
cp wfmu_archive.db wfmu_archive_backup_$(date +%Y%m%d).db
```

## ⚠️ Important Notes

1. **Be Respectful**: The scraper includes delays to avoid overwhelming WFMU's servers
2. **Storage Requirements**: Full archive with media may require several GB
3. **Time Requirements**: Complete archiving may take several hours
4. **Incremental Updates**: The scraper can resume from interruptions
5. **Database Locking**: The viewer uses a copy of the database to avoid conflicts

## 🚦 Troubleshooting

### Database Locked
```bash
# Create a copy for the viewer
cp wfmu_archive.db wfmu_archive_viewer.db
```

### Missing Posts
- The paginated scraper can only go back to around 2007
- Earlier posts (2003-2006) may require different approach

### Media Download Issues
- Check `download_error` field in media table
- Adjust rate limits if getting blocked
- Some media URLs may no longer be valid

### Viewer Not Showing Data
- Ensure database has data: `sqlite3 wfmu_archive.db "SELECT COUNT(*) FROM posts"`
- Check that `wfmu_archive_viewer.db` exists
- Restart the viewer after database updates

## 🎯 Next Steps

1. **Complete Image Downloads**: 8,000+ images remaining
2. **Audio Files**: Plan strategy for 9,000+ MP3 files
3. **Missing Years**: Investigate accessing 2003-2006 posts
4. **Export Options**: Static site generation for permanent hosting

## 📝 License

This archiving tool is provided for preservation purposes. Please respect the original content creators and WFMU's copyright. The archived content belongs to WFMU and its contributors.

## 🙏 Acknowledgments

Thanks to WFMU for decades of freeform radio and blog content. This archive ensures that the community's contributions are preserved for future generations.

---

**Remember**: Be a respectful archiver. Use appropriate delays and don't overwhelm the source servers.