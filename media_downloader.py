import asyncio
import aiohttp
import aiofiles
import os
import logging
from pathlib import Path
from urllib.parse import urlparse, unquote
from database import init_database, Media
from tenacity import retry, stop_after_attempt, wait_exponential
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MediaDownloader:
    def __init__(self, media_dir='media', db_session=None):
        self.media_dir = Path(media_dir)
        self.media_dir.mkdir(exist_ok=True)
        self.session, _ = init_database() if not db_session else (db_session, None)
        self.semaphore = asyncio.Semaphore(3)

        for subdir in ['images', 'audio', 'video', 'documents']:
            (self.media_dir / subdir).mkdir(exist_ok=True)

    def get_file_extension(self, url, content_type=None):
        parsed = urlparse(url)
        path = unquote(parsed.path)
        ext = os.path.splitext(path)[1]

        if not ext and content_type:
            type_map = {
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'image/gif': '.gif',
                'audio/mpeg': '.mp3',
                'audio/wav': '.wav',
                'video/mp4': '.mp4',
                'application/pdf': '.pdf'
            }
            ext = type_map.get(content_type, '')

        return ext or '.unknown'

    def generate_filename(self, url, media_type):
        url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
        ext = self.get_file_extension(url)
        return f"{url_hash}{ext}"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def download_file(self, session, media_item):
        async with self.semaphore:
            try:
                async with session.get(media_item.original_url, timeout=60) as response:
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')

                        if media_item.media_type == 'image':
                            subdir = 'images'
                        elif media_item.media_type == 'audio':
                            subdir = 'audio'
                        elif media_item.media_type == 'video':
                            subdir = 'video'
                        else:
                            subdir = 'documents'

                        filename = self.generate_filename(media_item.original_url, media_item.media_type)
                        filepath = self.media_dir / subdir / filename

                        content = await response.read()
                        async with aiofiles.open(filepath, 'wb') as f:
                            await f.write(content)

                        media_item.local_path = str(filepath)
                        media_item.filename = filename
                        media_item.downloaded = True
                        self.session.commit()

                        logger.info(f"Downloaded: {media_item.original_url} -> {filepath}")
                        return True
                    else:
                        logger.warning(f"Status {response.status} for {media_item.original_url}")
                        media_item.download_error = f"HTTP {response.status}"
                        self.session.commit()
                        return False

            except asyncio.TimeoutError:
                logger.error(f"Timeout downloading {media_item.original_url}")
                media_item.download_error = "Timeout"
                self.session.commit()
                return False
            except Exception as e:
                logger.error(f"Error downloading {media_item.original_url}: {e}")
                media_item.download_error = str(e)
                self.session.commit()
                return False

    async def download_all_media(self):
        undownloaded = self.session.query(Media).filter_by(downloaded=False).all()
        logger.info(f"Found {len(undownloaded)} media items to download")

        async with aiohttp.ClientSession() as session:
            tasks = []
            for media_item in undownloaded:
                task = self.download_file(session, media_item)
                tasks.append(task)

                if len(tasks) >= 20:
                    await asyncio.gather(*tasks)
                    tasks = []
                    await asyncio.sleep(1)

            if tasks:
                await asyncio.gather(*tasks)

        downloaded = self.session.query(Media).filter_by(downloaded=True).count()
        failed = self.session.query(Media).filter(Media.download_error.isnot(None)).count()

        logger.info(f"Download complete: {downloaded} successful, {failed} failed")
        return downloaded, failed

    async def retry_failed_downloads(self):
        failed = self.session.query(Media).filter(
            Media.download_error.isnot(None),
            Media.downloaded == False
        ).all()

        logger.info(f"Retrying {len(failed)} failed downloads...")

        for media_item in failed:
            media_item.download_error = None
            self.session.commit()

        return await self.download_all_media()

def main():
    downloader = MediaDownloader()
    asyncio.run(downloader.download_all_media())

if __name__ == "__main__":
    main()