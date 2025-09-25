#!/usr/bin/env python3
"""
WFMU Blog Complete Archive Scraper

This scraper will systematically go through all monthly archives from 2003-2015
to capture the complete WFMU blog archive.
"""

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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WFMUCompleteArchiver:
    def __init__(self, base_url='https://blog.wfmu.org/', db_session=None):
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
                    elif response.status == 404:
                        logger.debug(f"404 for {url}")
                        return None
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
            return False

        self.visited_urls.add(url)

        # Check if already scraped
        post_id = self.generate_post_id(url)
        existing_post = self.session.query(Post).filter_by(post_id=post_id).first()
        if existing_post:
            logger.debug(f"Post already exists: {url}")
            return False

        logger.info(f"Scraping post {self.post_count + 1}: {url}")

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

        # Extract title - try multiple selectors
        title_elem = (
            soup.find('h3', class_='entry-header') or
            soup.find('h3', class_='title') or
            soup.find('h2', class_='entry-title')
        )
        if title_elem:
            post.title = title_elem.get_text(strip=True)

        # Extract author
        author_elem = soup.find('span', class_='vcard')
        if author_elem:
            author_link = author_elem.find('a')
            if author_link:
                post.author = author_link.get_text(strip=True)
        else:
            # Try alternative author locations
            byline = soup.find('span', class_='byline')
            if byline:
                author_link = byline.find('a')
                if author_link:
                    post.author = author_link.get_text(strip=True)

        # Extract date
        date_elem = soup.find('h2', class_='date-header')
        if date_elem:
            post.published_date = self.parse_post_date(date_elem.get_text(strip=True))
        else:
            # Try alternative date locations
            date_span = soup.find('span', class_='post-date')
            if date_span:
                post.published_date = self.parse_post_date(date_span.get_text(strip=True))

        # Extract content
        content_div = (
            soup.find('div', class_='entry-body') or
            soup.find('div', class_='blogbody') or
            soup.find('div', class_='entry-content')
        )
        if content_div:
            post.content_text = content_div.get_text(separator='\n', strip=True)

            # Extract media
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

            # Extract audio/MP3 links
            audio_links = content_div.find_all('a', href=lambda x: x and '.mp3' in x.lower())
            for audio in audio_links:
                media = Media(
                    post_id=post_id,
                    media_type='audio',
                    original_url=urljoin(url, audio.get('href')),
                )
                self.session.add(media)

        # Extract categories/tags
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
            self.post_count += 1
            logger.info(f"Saved post #{self.post_count}: {post.title if post.title else 'Untitled'}")
            return True
        except IntegrityError:
            self.session.rollback()
            logger.debug(f"Post already exists: {url}")
            return False
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error saving post: {e}")
            return False

    async def scrape_monthly_archive(self, session, year, month):
        """Scrape all posts from a specific month's archive"""
        archive_url = f"{self.base_url}freeform/{year}/{month:02d}/"
        logger.info(f"Scraping archive: {year}-{month:02d}")

        html = await self.fetch_page(session, archive_url)
        if not html:
            logger.debug(f"No archive found for {year}-{month:02d}")
            return []

        soup = BeautifulSoup(html, 'lxml')
        post_urls = set()

        # Find all post links
        # Try multiple patterns
        patterns = [
            ('h3', 'entry-header'),
            ('h3', 'title'),
            ('h2', 'entry-title'),
        ]

        for tag, class_name in patterns:
            headers = soup.find_all(tag, class_=class_name)
            for header in headers:
                link = header.find('a')
                if link and link.get('href'):
                    post_url = urljoin(archive_url, link.get('href'))
                    post_urls.add(post_url)

        # Also look for direct links to posts in this month
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href')
            if f'/{year}/{month:02d}/' in href and '.html' in href:
                post_url = urljoin(archive_url, href)
                post_urls.add(post_url)

        logger.info(f"Found {len(post_urls)} posts in {year}-{month:02d}")
        return list(post_urls)

    async def scrape_year(self, session, year):
        """Scrape all posts from a specific year"""
        logger.info(f"Starting year {year}")
        year_posts = []

        for month in range(1, 13):
            month_posts = await self.scrape_monthly_archive(session, year, month)
            year_posts.extend(month_posts)

            # Scrape each post
            for post_url in month_posts:
                await self.scrape_post(session, post_url)
                await asyncio.sleep(0.3)  # Be polite

            # Take a break between months
            if month_posts:
                logger.info(f"Completed {year}-{month:02d}, taking a break...")
                await asyncio.sleep(2)

        logger.info(f"Completed year {year}: {len(year_posts)} posts found")
        return year_posts

    async def run_complete_archive(self, start_year=2003, end_year=2015):
        """Archive the complete blog from start_year to end_year"""
        logger.info(f"Starting complete archive from {start_year} to {end_year}")

        async with aiohttp.ClientSession() as session:
            all_posts = []

            for year in range(start_year, end_year + 1):
                year_posts = await self.scrape_year(session, year)
                all_posts.extend(year_posts)

                # Take a longer break between years
                logger.info(f"Completed year {year}, total posts so far: {self.post_count}")
                await asyncio.sleep(5)

            logger.info(f"Archive complete! Total posts scraped: {self.post_count}")
            return self.post_count

    def get_progress(self):
        """Get current scraping progress"""
        total_posts = self.session.query(Post).count()
        total_media = self.session.query(Media).count()

        # Get date range
        dates = self.session.query(Post.published_date).filter(
            Post.published_date.isnot(None)
        ).all()

        if dates:
            dates = [d[0] for d in dates if d[0]]
            if dates:
                earliest = min(dates)
                latest = max(dates)
                return {
                    'total_posts': total_posts,
                    'total_media': total_media,
                    'date_range': f"{earliest.strftime('%Y-%m-%d')} to {latest.strftime('%Y-%m-%d')}"
                }

        return {
            'total_posts': total_posts,
            'total_media': total_media,
            'date_range': 'Unknown'
        }

async def main():
    archiver = WFMUCompleteArchiver()

    # Start from 2015 and work backwards (most recent first)
    # This way we get the final posts first
    await archiver.run_complete_archive(start_year=2014, end_year=2015)

    # Show progress
    progress = archiver.get_progress()
    print(f"\nArchive Progress:")
    print(f"  Posts: {progress['total_posts']}")
    print(f"  Media: {progress['total_media']}")
    print(f"  Date Range: {progress['date_range']}")

if __name__ == "__main__":
    asyncio.run(main())