#!/usr/bin/env python3
"""
WFMU Image Downloader
Downloads images from the WFMU blog archive respectfully
"""
import sqlite3
import requests
import hashlib
import time
import os
from pathlib import Path
from urllib.parse import urlparse
import sys

# Configuration
DB_PATH = 'wfmu_archive.db'
MEDIA_DIR = Path('media/images')
BATCH_SIZE = 100  # Images per batch
DELAY_BETWEEN_IMAGES = 0.1  # Seconds between each image
DELAY_BETWEEN_BATCHES = 10  # Seconds between batches
MAX_RETRIES = 3
TIMEOUT = 30  # Seconds
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Archive Bot'

def init_database():
    """Initialize database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_pending_images(conn, limit=None):
    """Get images that haven't been downloaded"""
    cur = conn.cursor()
    query = """
        SELECT id, original_url, filename
        FROM media
        WHERE media_type = 'image'
        AND downloaded = 0
        AND download_error IS NULL
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
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg']:
            return ext

    # Try from content type
    if content_type:
        type_map = {
            'image/jpeg': 'jpg',
            'image/jpg': 'jpg',
            'image/png': 'png',
            'image/gif': 'gif',
            'image/webp': 'webp',
            'image/svg+xml': 'svg',
            'image/bmp': 'bmp'
        }
        for mime, ext in type_map.items():
            if mime in content_type.lower():
                return ext

    return 'jpg'  # Default

def download_image(url, filename):
    """Download a single image"""
    headers = {
        'User-Agent': USER_AGENT,
        'Referer': 'https://blog.wfmu.org/'
    }

    try:
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
                if '.' in filename and filename.split('.')[-1] == 'unknown':
                    filename = filename.replace('.unknown', f'.{ext}')
                else:
                    filename = f"{filename}.{ext}"

            # Save file
            filepath = MEDIA_DIR / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

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
        """, (f'media/images/{filename}', filename, media_id))
    else:
        cur.execute("""
            UPDATE media
            SET download_error = ?
            WHERE id = ?
        """, (error, media_id))
    conn.commit()

def main():
    """Main download process"""
    conn = init_database()
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    # Get statistics
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM media WHERE media_type = 'image'").fetchone()[0]
    downloaded = cur.execute("SELECT COUNT(*) FROM media WHERE media_type = 'image' AND downloaded = 1").fetchone()[0]
    remaining = total - downloaded

    print("=" * 60)
    print("WFMU Image Downloader")
    print("=" * 60)
    print(f"Total images: {total:,}")
    print(f"Already downloaded: {downloaded:,}")
    print(f"Remaining: {remaining:,}")
    print(f"\nSettings:")
    print(f"  Batch size: {BATCH_SIZE} images")
    print(f"  Delay between images: {DELAY_BETWEEN_IMAGES}s")
    print(f"  Delay between batches: {DELAY_BETWEEN_BATCHES}s")
    print(f"  Estimated time: {(remaining * DELAY_BETWEEN_IMAGES / 3600):.1f} hours")
    print("=" * 60)

    response = input("\nProceed with download? (yes/no/test): ").strip().lower()

    if response == 'test':
        limit = 10
        print(f"\nTest mode: Downloading {limit} images only...")
    elif response == 'yes':
        limit = None
        print("\nStarting full download...")
    else:
        print("Cancelled.")
        return

    # Get pending images
    images = get_pending_images(conn, limit)
    if not images:
        print("No images to download!")
        return

    print(f"\nProcessing {len(images)} images...")

    success_count = 0
    error_count = 0
    batch_count = 0

    for i, row in enumerate(images, 1):
        # Check for batch pause
        if i > 1 and (i - 1) % BATCH_SIZE == 0:
            batch_count += 1
            print(f"\n[Batch {batch_count} complete] Pausing {DELAY_BETWEEN_BATCHES}s...")
            print(f"Progress: {success_count}/{i-1} successful")
            time.sleep(DELAY_BETWEEN_BATCHES)

        # Download image
        print(f"\r[{i}/{len(images)}] {row['original_url'][:80]}...", end='', flush=True)

        success, filename, error = download_image(row['original_url'], row['filename'])

        if success:
            update_media_record(conn, row['id'], True, filename)
            success_count += 1
        else:
            update_media_record(conn, row['id'], False, error=error)
            error_count += 1
            print(f"\n  ✗ Error: {error}")

        # Rate limiting
        time.sleep(DELAY_BETWEEN_IMAGES)

        # Allow interruption
        if i % 10 == 0:
            try:
                # Check for Ctrl+C
                pass
            except KeyboardInterrupt:
                print(f"\n\nInterrupted! Downloaded {success_count} images.")
                break

    # Final stats
    print("\n" + "=" * 60)
    print("Download Complete!")
    print(f"Successfully downloaded: {success_count}")
    print(f"Errors: {error_count}")
    print("=" * 60)

    conn.close()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
        sys.exit(0)