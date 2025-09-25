import logging
from bs4 import BeautifulSoup
import html2text
from database import init_database, Post
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentParser:
    def __init__(self, db_session=None):
        self.session, _ = init_database() if not db_session else (db_session, None)
        self.html2text = html2text.HTML2Text()
        self.html2text.ignore_links = False
        self.html2text.ignore_images = False
        self.html2text.body_width = 0
        self.html2text.protect_links = True

    def clean_text(self, text):
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def extract_clean_content(self, raw_html):
        soup = BeautifulSoup(raw_html, 'lxml')

        content_div = soup.find('div', class_='blogbody')
        if not content_div:
            content_div = soup.find('article') or soup.find('main')

        if not content_div:
            return None, None

        for script in content_div(['script', 'style']):
            script.decompose()

        text_content = content_div.get_text(separator='\n', strip=True)
        text_content = self.clean_text(text_content)

        try:
            markdown_content = self.html2text.handle(str(content_div))
            markdown_content = self.clean_text(markdown_content)
        except Exception as e:
            logger.error(f"Error converting to markdown: {e}")
            markdown_content = text_content

        return text_content, markdown_content

    def process_all_posts(self):
        posts = self.session.query(Post).filter(
            Post.content_text.is_(None) | (Post.content_markdown.is_(None))
        ).all()

        logger.info(f"Processing {len(posts)} posts...")

        for i, post in enumerate(posts, 1):
            if post.raw_html:
                text_content, markdown_content = self.extract_clean_content(post.raw_html)

                if text_content and not post.content_text:
                    post.content_text = text_content

                if markdown_content and not post.content_markdown:
                    post.content_markdown = markdown_content

                self.session.commit()

                if i % 100 == 0:
                    logger.info(f"Processed {i}/{len(posts)} posts")

        logger.info("Content parsing complete")

    def extract_metadata(self, raw_html):
        soup = BeautifulSoup(raw_html, 'lxml')
        metadata = {}

        title = soup.find('h3', class_='title')
        if title:
            metadata['title'] = title.get_text(strip=True)

        byline = soup.find('span', class_='byline')
        if byline:
            author = byline.find('a')
            if author:
                metadata['author'] = author.get_text(strip=True)

            date = byline.find('span', class_='date')
            if date:
                metadata['date'] = date.get_text(strip=True)

        categories = []
        cat_div = soup.find('p', class_='postmetadata')
        if cat_div:
            cat_links = cat_div.find_all('a', rel='category tag')
            categories = [link.get_text(strip=True) for link in cat_links]
        metadata['categories'] = categories

        return metadata

    def update_missing_metadata(self):
        posts = self.session.query(Post).filter(
            (Post.title.is_(None)) | (Post.author.is_(None))
        ).all()

        logger.info(f"Updating metadata for {len(posts)} posts...")

        for post in posts:
            if post.raw_html:
                metadata = self.extract_metadata(post.raw_html)

                if not post.title and metadata.get('title'):
                    post.title = metadata['title']

                if not post.author and metadata.get('author'):
                    post.author = metadata['author']

                self.session.commit()

        logger.info("Metadata update complete")

def main():
    parser = ContentParser()
    parser.process_all_posts()
    parser.update_missing_metadata()

if __name__ == "__main__":
    main()