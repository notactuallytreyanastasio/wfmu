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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WFMUBlogScraper:
    def __init__(self, base_url='https://blog.wfmu.org/', db_session=None):
        self.base_url = base_url
        self.session, self.engine = init_database() if not db_session else (db_session, None)
        self.visited_urls = set()
        self.semaphore = asyncio.Semaphore(5)

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

        title_elem = soup.find('h3', class_='title')
        if title_elem:
            post.title = title_elem.get_text(strip=True)

        byline = soup.find('span', class_='byline')
        if byline:
            author_elem = byline.find('a')
            if author_elem:
                post.author = author_elem.get_text(strip=True)
            date_elem = byline.find('span', class_='date')
            if date_elem:
                post.published_date = self.parse_post_date(date_elem.get_text(strip=True))

        content_div = soup.find('div', class_='blogbody')
        if content_div:
            post.content_text = content_div.get_text(separator='\n', strip=True)

        categories_div = soup.find('p', class_='postmetadata')
        if categories_div:
            category_links = categories_div.find_all('a', rel='category tag')
            for cat_link in category_links:
                cat_name = cat_link.get_text(strip=True)
                category = self.session.query(Category).filter_by(name=cat_name).first()
                if not category:
                    category = Category(name=cat_name, url=urljoin(url, cat_link.get('href')))
                    self.session.add(category)
                post.categories.append(category)

        if content_div:
            images = content_div.find_all('img')
            for img in images:
                media = Media(
                    post_id=post_id,
                    media_type='image',
                    original_url=urljoin(url, img.get('src', '')),
                    alt_text=img.get('alt', ''),
                )
                self.session.add(media)

            audio_links = content_div.find_all('a', href=lambda x: x and x.endswith('.mp3'))
            for audio in audio_links:
                media = Media(
                    post_id=post_id,
                    media_type='audio',
                    original_url=urljoin(url, audio.get('href')),
                )
                self.session.add(media)

        comments_div = soup.find('ol', class_='commentlist')
        if comments_div:
            comments = comments_div.find_all('li')
            for comment_elem in comments:
                comment = Comment(post_id=post_id)

                cite = comment_elem.find('cite')
                if cite:
                    comment.author = cite.get_text(strip=True)

                date_elem = comment_elem.find('small')
                if date_elem:
                    comment.date = self.parse_post_date(date_elem.get_text(strip=True))

                content = comment_elem.find('p')
                if content:
                    comment.content = content.get_text(strip=True)

                self.session.add(comment)

        try:
            self.session.add(post)
            self.session.commit()
            logger.info(f"Saved post: {post.title}")
        except IntegrityError:
            self.session.rollback()
            logger.warning(f"Post already exists: {url}")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error saving post: {e}")

    async def scrape_archive_page(self, session, url):
        logger.info(f"Scraping archive page: {url}")
        html = await self.fetch_page(session, url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'lxml')
        post_urls = []

        post_titles = soup.find_all('h3', class_='title')
        for title in post_titles:
            link = title.find('a')
            if link and link.get('href'):
                post_url = urljoin(url, link.get('href'))
                post_urls.append(post_url)

        next_page = soup.find('a', string='Older Posts')
        if next_page and next_page.get('href'):
            next_url = urljoin(url, next_page.get('href'))
            post_urls.append(('NEXT', next_url))

        return post_urls

    async def scrape_categories(self, session):
        logger.info("Scraping categories...")
        html = await self.fetch_page(session, self.base_url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'lxml')
        categories = []

        cat_list = soup.find('ul', id='categories')
        if cat_list:
            links = cat_list.find_all('a')
            for link in links:
                cat_name = link.get_text(strip=True)
                if '(' in cat_name:
                    name = cat_name[:cat_name.rfind('(')].strip()
                    count_str = cat_name[cat_name.rfind('(')+1:cat_name.rfind(')')].strip()
                    try:
                        count = int(count_str)
                    except:
                        count = 0
                else:
                    name = cat_name
                    count = 0

                cat_url = urljoin(self.base_url, link.get('href', ''))

                category = self.session.query(Category).filter_by(name=name).first()
                if not category:
                    category = Category(name=name, url=cat_url, post_count=count)
                    self.session.add(category)
                    self.session.commit()

                categories.append(cat_url)

        return categories

    async def run_full_scrape(self):
        async with aiohttp.ClientSession() as session:
            category_urls = await self.scrape_categories(session)
            logger.info(f"Found {len(category_urls)} categories")

            archive_urls = [self.base_url] + category_urls

            for archive_url in archive_urls:
                current_url = archive_url
                page_count = 0

                while current_url:
                    page_count += 1
                    logger.info(f"Processing page {page_count} of {archive_url}")

                    post_urls = await self.scrape_archive_page(session, current_url)
                    next_url = None

                    for item in post_urls:
                        if isinstance(item, tuple) and item[0] == 'NEXT':
                            next_url = item[1]
                        else:
                            await self.scrape_post(session, item)
                            await asyncio.sleep(0.5)

                    current_url = next_url

                    if page_count % 10 == 0:
                        logger.info(f"Processed {page_count} pages, taking a break...")
                        await asyncio.sleep(5)

def main():
    scraper = WFMUBlogScraper()
    asyncio.run(scraper.run_full_scrape())

if __name__ == "__main__":
    main()