#!/usr/bin/env python3
"""
WFMU Blog Paginated Scraper
Uses the /page/N/ pagination to scrape all posts
"""

import asyncio
import aiohttp
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential
import hashlib
from database import init_database, Post, Category, Media
from sqlalchemy.exc import IntegrityError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WFMUPaginatedScraper:
    def __init__(self, base_url='https://blog.wfmu.org/freeform/', db_session=None):
        self.base_url = base_url
        self.session, self.engine = init_database() if not db_session else (db_session, None)
        self.visited_urls = set()
        self.semaphore = asyncio.Semaphore(3)
        self.post_count = 0

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch_page(self, session, url):
        async with self.semaphore:
            try:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        return await response.text()
                    return None
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                raise

    def generate_post_id(self, url):
        return hashlib.md5(url.encode()).hexdigest()

    def parse_post_date(self, date_str):
        try:
            from dateutil import parser
            return parser.parse(date_str)
        except:
            return None

    async def scrape_post(self, session, url):
        if url in self.visited_urls:
            return False

        self.visited_urls.add(url)

        post_id = self.generate_post_id(url)
        existing = self.session.query(Post).filter_by(post_id=post_id).first()
        if existing:
            return False

        html = await self.fetch_page(session, url)
        if not html:
            return False

        soup = BeautifulSoup(html, 'lxml')

        post = Post(
            post_id=post_id,
            url=url,
            raw_html=html,
            scraped_at=datetime.utcnow()
        )

        # Title
        title_elem = soup.find('h3', class_='entry-header')
        if title_elem:
            post.title = title_elem.get_text(strip=True)

        # Author
        author_elem = soup.find('span', class_='vcard')
        if author_elem:
            link = author_elem.find('a')
            if link:
                post.author = link.get_text(strip=True)

        # Date
        date_elem = soup.find('h2', class_='date-header')
        if date_elem:
            post.published_date = self.parse_post_date(date_elem.get_text(strip=True))

        # Content
        content_div = soup.find('div', class_='entry-body')
        if content_div:
            post.content_text = content_div.get_text(separator='\n', strip=True)

            # Media
            for img in content_div.find_all('img'):
                src = img.get('src', '')
                if src:
                    media = Media(
                        post_id=post_id,
                        media_type='image',
                        original_url=urljoin(url, src),
                        alt_text=img.get('alt', ''),
                    )
                    self.session.add(media)

            for audio in content_div.find_all('a', href=lambda x: x and '.mp3' in x.lower()):
                media = Media(
                    post_id=post_id,
                    media_type='audio',
                    original_url=urljoin(url, audio.get('href')),
                )
                self.session.add(media)

        try:
            self.session.add(post)
            self.session.commit()
            self.post_count += 1
            logger.info(f"[{self.post_count}] Saved: {post.title if post.title else url}")
            return True
        except IntegrityError:
            self.session.rollback()
            return False
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error saving: {e}")
            return False

    async def scrape_page_of_posts(self, session, page_num):
        """Scrape all posts from a single page"""
        if page_num == 1:
            page_url = self.base_url
        else:
            page_url = f"{self.base_url}page/{page_num}/"

        logger.info(f"Fetching page {page_num}: {page_url}")
        html = await self.fetch_page(session, page_url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'lxml')
        post_urls = []

        # Find all post headers
        headers = soup.find_all('h3', class_='entry-header')
        for header in headers:
            link = header.find('a')
            if link and link.get('href'):
                post_url = urljoin(page_url, link.get('href'))
                post_urls.append(post_url)

        return post_urls

    async def run(self, max_pages=None):
        """Run the complete scraping process"""
        logger.info("Starting WFMU blog scraping...")

        async with aiohttp.ClientSession() as session:
            page_num = 1
            consecutive_empty = 0

            while True:
                if max_pages and page_num > max_pages:
                    break

                # Get posts from this page
                post_urls = await self.scrape_page_of_posts(session, page_num)

                if not post_urls:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        logger.info("No more pages found")
                        break
                else:
                    consecutive_empty = 0
                    logger.info(f"Page {page_num}: Found {len(post_urls)} posts")

                    # Scrape each post
                    for url in post_urls:
                        await self.scrape_post(session, url)
                        await asyncio.sleep(0.2)  # Rate limiting

                page_num += 1

                # Take a break between pages
                if page_num % 10 == 0:
                    logger.info(f"Processed {page_num} pages, taking a break...")
                    await asyncio.sleep(3)

        logger.info(f"Scraping complete! Total posts: {self.post_count}")
        return self.post_count

async def main():
    scraper = WFMUPaginatedScraper()
    await scraper.run()

if __name__ == "__main__":
    asyncio.run(main())