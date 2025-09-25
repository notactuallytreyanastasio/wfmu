# WFMU Blog Archive Tool

A comprehensive archiving solution for preserving the WFMU blog (blog.wfmu.org) before it shuts down. This tool scrapes the entire blog history, downloads media files, parses content, and creates a searchable archive.

## Features

- **Complete Blog Scraping**: Archives all posts, pages, and categories
- **Media Preservation**: Downloads all images, audio files, and other media
- **Content Extraction**: Converts HTML to clean text and Markdown formats
- **Full-Text Search**: Creates a searchable index using Whoosh
- **Database Storage**: SQLite database for easy portability
- **Integrity Verification**: Checks for missing posts and media files
- **Export Options**: JSON export for further processing

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd wfmu

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

To run the complete archiving process:

```bash
python archive_wfmu.py full-archive
```

This will:
1. Scrape all blog posts and pages
2. Download all media files
3. Parse content to extract clean text
4. Build a searchable index
5. Verify archive integrity

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
├── wfmu_archive.db       # SQLite database
├── media/                # Downloaded media files
│   ├── images/
│   ├── audio/
│   ├── video/
│   └── documents/
├── search_index/         # Whoosh search index
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

## Next Steps

Once archived, you can:
- Build a static site generator to recreate the blog
- Create an API server for the archive
- Import into other content management systems
- Analyze the blog's history and patterns

## License

This archiving tool is provided for preservation purposes. Please respect the original content creators and WFMU's copyright.