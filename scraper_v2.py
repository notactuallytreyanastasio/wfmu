import asyncio
import aiohttp
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential
import hashlib
from database import init_database, Post, Category, Media, Comment, ScrapeProgress
from sqlalchemy.exc import IntegrityError
import time
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WFMUBlogScraperV2:
    def __init__(self, base_url='https://blog.wfmu.org/', db_session=None):
        self.base_url = base_url
        self.session, self.engine = init_database() if not db_session else (db_session, None)
        self.visited_urls = set()
        self.semaphore = asyncio.Semaphore(3)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch_page(self, session, url):
        async with self.semaphore:
            try:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.warning(f"Status {response.status} for {url}")
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
            return

        self.visited_urls.add(url)
        logger.info(f"Scraping post: {url}")

        html = await self.fetch_page(session, url)
        if not html:
            return

        soup = BeautifulSoup(html, 'lxml')
        post_id = self.generate_post_id(url)

        existing_post = self.session.query(Post).filter_by(post_id=post_id).first()
        if existing_post:
            logger.info(f"Post already exists: {url}")
            return

        post = Post(
            post_id=post_id,
            url=url,
            raw_html=html,
            scraped_at=datetime.utcnow()
        )

        # Try both class formats
        title_elem = soup.find('h3', class_='entry-header') or soup.find('h3', class_='title')
        if title_elem:
            post.title = title_elem.get_text(strip=True)

        # Look for author in various places
        author_elem = soup.find('span', class_='vcard')
        if author_elem:
            author_link = author_elem.find('a')
            if author_link:
                post.author = author_link.get_text(strip=True)

        # Look for date
        date_elem = soup.find('h2', class_='date-header')
        if date_elem:
            post.published_date = self.parse_post_date(date_elem.get_text(strip=True))

        # Get content - try multiple class names
        content_div = soup.find('div', class_='entry-body') or soup.find('div', class_='blogbody')
        if content_div:
            post.content_text = content_div.get_text(separator='\n', strip=True)

            # Extract images
            images = content_div.find_all('img')
            for img in images:
                src = img.get('src', '')
                if src:
                    media = Media(
                        post_id=post_id,
                        media_type='image',
                        original_url=urljoin(url, src),
                        alt_text=img.get('alt', ''),
                    )
                    self.session.add(media)

            # Extract audio links (MP3s)
            audio_links = content_div.find_all('a', href=lambda x: x and '.mp3' in x.lower())
            for audio in audio_links:
                media = Media(
                    post_id=post_id,
                    media_type='audio',
                    original_url=urljoin(url, audio.get('href')),
                )
                self.session.add(media)

        # Look for categories/tags
        footer = soup.find('p', class_='entry-footer')
        if footer:
            category_links = footer.find_all('a', rel=lambda x: x and 'tag' in x)
            for cat_link in category_links:
                cat_name = cat_link.get_text(strip=True)
                category = self.session.query(Category).filter_by(name=cat_name).first()
                if not category:
                    category = Category(name=cat_name, url=urljoin(url, cat_link.get('href')))
                    self.session.add(category)
                post.categories.append(category)

        try:
            self.session.add(post)
            self.session.commit()
            logger.info(f"Saved post: {post.title if post.title else 'Untitled'}")
        except IntegrityError:
            self.session.rollback()
            logger.warning(f"Post already exists: {url}")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error saving post: {e}")

    async def scrape_archives_page(self, session):
        """Scrape the archives.html page to get all post URLs"""
        archives_url = urljoin(self.base_url, 'freeform/archives.html')
        logger.info(f"Scraping archives page: {archives_url}")

        html = await self.fetch_page(session, archives_url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'lxml')
        post_urls = []

        # Find all links that look like blog posts
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href')
            # Match typical WFMU blog post URL pattern
            if '/freeform/20' in href and '.html' in href:
                post_url = urljoin(archives_url, href)
                if post_url not in post_urls:
                    post_urls.append(post_url)

        logger.info(f"Found {len(post_urls)} post URLs in archives")
        return post_urls

    async def scrape_year_month_archives(self, session):
        """Try to find monthly archive pages"""
        post_urls = []

        # Try years from 2003 to 2015 (when blog ended)
        for year in range(2003, 2016):
            for month in range(1, 13):
                # Try common archive URL patterns
                patterns = [
                    f'{self.base_url}freeform/{year}/{month:02d}/',
                    f'{self.base_url}freeform/{year}_{month:02d}.html',
                    f'{self.base_url}freeform/{year}/{month:02d}/index.html'
                ]

                for pattern_url in patterns:
                    logger.info(f"Trying archive pattern: {pattern_url}")
                    html = await self.fetch_page(session, pattern_url)
                    if html:
                        soup = BeautifulSoup(html, 'lxml')
                        # Look for post links
                        links = soup.find_all('h3', class_='entry-header')
                        for link_elem in links:
                            link = link_elem.find('a')
                            if link and link.get('href'):
                                post_url = urljoin(pattern_url, link.get('href'))
                                if post_url not in post_urls:
                                    post_urls.append(post_url)

                        if links:
                            logger.info(f"Found {len(links)} posts in {pattern_url}")
                            break  # Found valid pattern, skip other patterns for this month

                await asyncio.sleep(0.5)  # Be polite

        return post_urls

    async def run_full_scrape(self):
        async with aiohttp.ClientSession() as session:
            # First, scrape the archives page
            archive_posts = await self.scrape_archives_page(session)

            # If no posts found in archives.html, try monthly patterns
            if not archive_posts:
                logger.info("No posts found in archives.html, trying monthly patterns...")
                archive_posts = await self.scrape_year_month_archives(session)

            # Scrape each post
            total_posts = len(archive_posts)
            logger.info(f"Starting to scrape {total_posts} posts...")

            for i, post_url in enumerate(archive_posts, 1):
                logger.info(f"Processing post {i}/{total_posts}")
                await self.scrape_post(session, post_url)

                # Be polite - small delay between requests
                await asyncio.sleep(0.5)

                # Longer break every 50 posts
                if i % 50 == 0:
                    logger.info(f"Processed {i} posts, taking a longer break...")
                    await asyncio.sleep(5)

            logger.info(f"Scraping complete! Processed {total_posts} posts")

def main():
    scraper = WFMUBlogScraperV2()
    asyncio.run(scraper.run_full_scrape())

if __name__ == "__main__":
    main()