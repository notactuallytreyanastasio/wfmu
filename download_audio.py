#!/usr/bin/env python3
"""
WFMU Audio Downloader
Downloads MP3 files from the WFMU blog archive very respectfully
Tracks all downloads to prevent duplicates
"""
import sqlite3
import requests
import hashlib
import time
import os
from pathlib import Path
from urllib.parse import urlparse
import sys
from datetime import datetime

# Configuration - VERY respectful for large files
DB_PATH = 'wfmu_archive.db'
MEDIA_DIR = Path('media/audio')
BATCH_SIZE = 50  # Fewer files per batch for audio
DELAY_BETWEEN_FILES = 2  # Longer delay for larger files
DELAY_BETWEEN_BATCHES = 30  # Longer pause between batches
MAX_RETRIES = 2
TIMEOUT = 120  # Longer timeout for audio files
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) WFMU Archive Bot - Respectful MP3 Archiver'

def init_database():
    """Initialize database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_pending_audio(conn, limit=None):
    """Get audio files that haven't been downloaded"""
    cur = conn.cursor()
    query = """
        SELECT id, original_url, filename
        FROM media
        WHERE media_type = 'audio'
        AND downloaded = 0
        AND (download_error IS NULL OR download_error = '')
        ORDER BY id
    """
    if limit:
        query += f" LIMIT {limit}"

    return cur.execute(query).fetchall()

def get_file_extension(url, content_type=None):
    """Determine file extension from URL or content type"""
    # Try from URL first
    path = urlparse(url).path
    if '.' in path:
        ext = path.split('.')[-1].lower()
        if ext in ['mp3', 'm4a', 'wav', 'ogg', 'flac', 'aac']:
            return ext

    # Try from content type
    if content_type:
        type_map = {
            'audio/mpeg': 'mp3',
            'audio/mp3': 'mp3',
            'audio/x-mp3': 'mp3',
            'audio/mp4': 'm4a',
            'audio/x-m4a': 'm4a',
            'audio/wav': 'wav',
            'audio/ogg': 'ogg',
            'audio/flac': 'flac',
            'audio/aac': 'aac'
        }
        for mime, ext in type_map.items():
            if mime in content_type.lower():
                return ext

    return 'mp3'  # Default for audio

def format_size(bytes):
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"

def download_audio(url, filename):
    """Download a single audio file"""
    headers = {
        'User-Agent': USER_AGENT,
        'Referer': 'https://blog.wfmu.org/',
        'Accept': 'audio/*,*/*'
    }

    try:
        # First check file size with HEAD request
        head_response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        content_length = head_response.headers.get('Content-Length')
        if content_length:
            file_size = int(content_length)
            print(f"\n  → File size: {format_size(file_size)}", end='', flush=True)

        # Download the file
        response = requests.get(url, headers=headers, timeout=TIMEOUT, stream=True)

        if response.status_code == 200:
            # Generate filename if None
            if not filename:
                # Generate filename from URL hash
                url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
                filename = url_hash

            # Determine extension
            content_type = response.headers.get('Content-Type', '')
            ext = get_file_extension(url, content_type)

            # Update filename with extension if needed
            if not filename.endswith(f'.{ext}'):
                # Remove any existing extension
                if '.' in filename:
                    base = filename.rsplit('.', 1)[0]
                    filename = f"{base}.{ext}"
                else:
                    filename = f"{filename}.{ext}"

            # Save file
            filepath = MEDIA_DIR / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Download with progress tracking
            downloaded_bytes = 0
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded_bytes += len(chunk)
                    if content_length and downloaded_bytes % (1024 * 512) == 0:  # Update every 512KB
                        progress = (downloaded_bytes / int(content_length)) * 100
                        print(f"\r  → File size: {format_size(int(content_length))} [{progress:.1f}%]", end='', flush=True)

            # Get final file size
            actual_size = os.path.getsize(filepath)
            print(f"\r  ✓ Downloaded: {format_size(actual_size)}", end='', flush=True)

            return True, filename, None
        else:
            return False, None, f"HTTP {response.status_code}"

    except requests.RequestException as e:
        return False, None, str(e)
    except Exception as e:
        return False, None, f"Error: {str(e)}"

def update_media_record(conn, media_id, success, filename=None, error=None):
    """Update media record in database"""
    cur = conn.cursor()
    if success:
        cur.execute("""
            UPDATE media
            SET downloaded = 1,
                local_path = ?,
                filename = ?
            WHERE id = ?
        """, (f'media/audio/{filename}', filename, media_id))
    else:
        cur.execute("""
            UPDATE media
            SET download_error = ?
            WHERE id = ?
        """, (error, media_id))
    conn.commit()

def get_statistics(conn):
    """Get download statistics"""
    cur = conn.cursor()

    # Total counts
    total = cur.execute("SELECT COUNT(*) FROM media WHERE media_type = 'audio'").fetchone()[0]
    downloaded = cur.execute("SELECT COUNT(*) FROM media WHERE media_type = 'audio' AND downloaded = 1").fetchone()[0]
    errors = cur.execute("SELECT COUNT(*) FROM media WHERE media_type = 'audio' AND download_error IS NOT NULL AND download_error != ''").fetchone()[0]
    remaining = total - downloaded - errors

    # Calculate size of downloaded files
    downloaded_size = 0
    if downloaded > 0:
        audio_dir = Path('media/audio')
        if audio_dir.exists():
            for file in audio_dir.glob('*'):
                if file.is_file():
                    downloaded_size += file.stat().st_size

    return {
        'total': total,
        'downloaded': downloaded,
        'errors': errors,
        'remaining': remaining,
        'downloaded_size': downloaded_size
    }

def main():
    """Main download process"""
    conn = init_database()
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    # Get statistics
    stats = get_statistics(conn)

    print("=" * 60)
    print("WFMU Audio Downloader (Respectful MP3 Archiver)")
    print("=" * 60)
    print(f"Total audio files: {stats['total']:,}")
    print(f"Already downloaded: {stats['downloaded']:,} ({format_size(stats['downloaded_size'])})")
    print(f"Failed downloads: {stats['errors']:,}")
    print(f"Remaining: {stats['remaining']:,}")
    print(f"\nSettings (RESPECTFUL MODE):")
    print(f"  Batch size: {BATCH_SIZE} files")
    print(f"  Delay between files: {DELAY_BETWEEN_FILES}s")
    print(f"  Delay between batches: {DELAY_BETWEEN_BATCHES}s")

    # Estimate time and size
    avg_size_mb = 7.4  # Based on your 82 files = 606MB
    estimated_size = stats['remaining'] * avg_size_mb * 1024 * 1024
    estimated_time_hours = (stats['remaining'] * DELAY_BETWEEN_FILES) / 3600
    estimated_time_days = estimated_time_hours / 24

    print(f"\nEstimates:")
    print(f"  Storage needed: ~{format_size(estimated_size)}")
    print(f"  Time needed: ~{estimated_time_hours:.1f} hours ({estimated_time_days:.1f} days)")
    print(f"  Note: This will run slowly and respectfully")
    print("=" * 60)

    response = input("\nProceed with download? (yes/no/test/resume): ").strip().lower()

    if response == 'test':
        limit = 5
        print(f"\nTest mode: Downloading {limit} files only...")
    elif response in ['yes', 'resume']:
        limit = None
        if response == 'resume':
            print("\nResuming download (skipping already downloaded files)...")
        else:
            print("\nStarting full download (this will take days)...")
        print("You can safely interrupt with Ctrl+C and resume later.")
    else:
        print("Cancelled.")
        return

    # Get pending audio files
    audio_files = get_pending_audio(conn, limit)
    if not audio_files:
        print("No audio files to download!")
        return

    print(f"\nProcessing {len(audio_files)} audio files...")
    print("=" * 60)

    success_count = 0
    error_count = 0
    batch_count = 0
    session_start = time.time()

    for i, row in enumerate(audio_files, 1):
        # Check for batch pause
        if i > 1 and (i - 1) % BATCH_SIZE == 0:
            batch_count += 1
            elapsed = time.time() - session_start
            rate = success_count / (elapsed / 3600) if elapsed > 0 else 0
            print(f"\n[Batch {batch_count} complete] Pausing {DELAY_BETWEEN_BATCHES}s...")
            print(f"Progress: {success_count}/{i-1} successful, {error_count} errors")
            print(f"Rate: {rate:.1f} files/hour")
            time.sleep(DELAY_BETWEEN_BATCHES)

        # Show current file
        url_display = row['original_url']
        if len(url_display) > 80:
            url_display = '...' + url_display[-77:]
        print(f"\n[{i}/{len(audio_files)}] {url_display}")

        # Download audio file
        success, filename, error = download_audio(row['original_url'], row['filename'])

        if success:
            update_media_record(conn, row['id'], True, filename)
            success_count += 1
            print(f"  → Saved as: {filename}")
        else:
            update_media_record(conn, row['id'], False, error=error)
            error_count += 1
            print(f"  ✗ Error: {error}")

        # Rate limiting
        time.sleep(DELAY_BETWEEN_FILES)

        # Allow clean interruption every 10 files
        if i % 10 == 0:
            try:
                # This allows checking for Ctrl+C
                pass
            except KeyboardInterrupt:
                print(f"\n\nInterrupted! Downloaded {success_count} files.")
                print("You can resume later by running the script again and selecting 'resume'.")
                break

    # Final statistics
    elapsed_total = time.time() - session_start
    print("\n" + "=" * 60)
    print("Download Session Complete!")
    print(f"Successfully downloaded: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Time elapsed: {elapsed_total/3600:.1f} hours")

    # Show updated totals
    final_stats = get_statistics(conn)
    print(f"\nTotal progress:")
    print(f"  Downloaded so far: {final_stats['downloaded']:,}/{final_stats['total']:,}")
    print(f"  Total size: {format_size(final_stats['downloaded_size'])}")
    print(f"  Still remaining: {final_stats['remaining']:,}")
    print("=" * 60)

    conn.close()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopped by user. You can resume anytime.")
        sys.exit(0)