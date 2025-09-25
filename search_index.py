import os
import logging
from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID, DATETIME, KEYWORD
from whoosh.qparser import MultifieldParser, QueryParser
from whoosh.analysis import StemmingAnalyzer
from database import init_database, Post, Category
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchIndex:
    def __init__(self, index_dir='search_index', db_session=None):
        self.index_dir = index_dir
        self.session, _ = init_database() if not db_session else (db_session, None)

        self.schema = Schema(
            post_id=ID(stored=True, unique=True),
            url=ID(stored=True),
            title=TEXT(stored=True, analyzer=StemmingAnalyzer()),
            author=TEXT(stored=True),
            content=TEXT(analyzer=StemmingAnalyzer()),
            markdown=TEXT,
            categories=KEYWORD(stored=True, commas=True),
            published_date=DATETIME(stored=True),
            scraped_at=DATETIME(stored=True)
        )

        if not os.path.exists(index_dir):
            os.mkdir(index_dir)
            self.index = create_in(index_dir, self.schema)
        else:
            if exists_in(index_dir):
                self.index = open_dir(index_dir)
            else:
                self.index = create_in(index_dir, self.schema)

    def index_all_posts(self):
        posts = self.session.query(Post).all()
        logger.info(f"Indexing {len(posts)} posts...")

        writer = self.index.writer()
        indexed_count = 0

        for post in posts:
            try:
                categories = ','.join([cat.name for cat in post.categories])

                writer.add_document(
                    post_id=post.post_id,
                    url=post.url,
                    title=post.title or '',
                    author=post.author or '',
                    content=post.content_text or '',
                    markdown=post.content_markdown or '',
                    categories=categories,
                    published_date=post.published_date,
                    scraped_at=post.scraped_at
                )
                indexed_count += 1

                if indexed_count % 100 == 0:
                    logger.info(f"Indexed {indexed_count}/{len(posts)} posts")

            except Exception as e:
                logger.error(f"Error indexing post {post.post_id}: {e}")

        writer.commit()
        logger.info(f"Indexing complete: {indexed_count} posts indexed")

    def search(self, query_string, limit=20, fields=None):
        with self.index.searcher() as searcher:
            if fields:
                parser = MultifieldParser(fields, self.index.schema)
            else:
                parser = MultifieldParser(['title', 'content', 'author', 'categories'],
                                         self.index.schema)

            try:
                query = parser.parse(query_string)
                results = searcher.search(query, limit=limit)

                search_results = []
                for hit in results:
                    search_results.append({
                        'post_id': hit['post_id'],
                        'url': hit['url'],
                        'title': hit.get('title', 'Untitled'),
                        'author': hit.get('author', 'Unknown'),
                        'categories': hit.get('categories', '').split(',') if hit.get('categories') else [],
                        'score': hit.score,
                        'published_date': hit.get('published_date')
                    })

                return search_results

            except Exception as e:
                logger.error(f"Search error: {e}")
                return []

    def search_by_category(self, category_name):
        with self.index.searcher() as searcher:
            parser = QueryParser('categories', self.index.schema)
            query = parser.parse(category_name)
            results = searcher.search(query, limit=None)

            return [{
                'post_id': hit['post_id'],
                'url': hit['url'],
                'title': hit.get('title', 'Untitled'),
                'author': hit.get('author', 'Unknown')
            } for hit in results]

    def search_by_author(self, author_name):
        with self.index.searcher() as searcher:
            parser = QueryParser('author', self.index.schema)
            query = parser.parse(f'"{author_name}"')
            results = searcher.search(query, limit=None)

            return [{
                'post_id': hit['post_id'],
                'url': hit['url'],
                'title': hit.get('title', 'Untitled'),
                'published_date': hit.get('published_date')
            } for hit in results]

    def search_by_date_range(self, start_date, end_date):
        with self.index.searcher() as searcher:
            parser = QueryParser('published_date', self.index.schema)
            query_string = f"[{start_date.strftime('%Y%m%d')} TO {end_date.strftime('%Y%m%d')}]"
            query = parser.parse(query_string)
            results = searcher.search(query, limit=None)

            return [{
                'post_id': hit['post_id'],
                'url': hit['url'],
                'title': hit.get('title', 'Untitled'),
                'published_date': hit.get('published_date')
            } for hit in results]

    def update_post(self, post):
        writer = self.index.writer()

        categories = ','.join([cat.name for cat in post.categories])

        writer.update_document(
            post_id=post.post_id,
            url=post.url,
            title=post.title or '',
            author=post.author or '',
            content=post.content_text or '',
            markdown=post.content_markdown or '',
            categories=categories,
            published_date=post.published_date,
            scraped_at=post.scraped_at
        )

        writer.commit()

def main():
    search = SearchIndex()
    search.index_all_posts()

    test_searches = [
        "music",
        "radio",
        "WFMU",
        "podcast"
    ]

    for query in test_searches:
        results = search.search(query, limit=5)
        logger.info(f"Search for '{query}': {len(results)} results")
        for result in results[:3]:
            logger.info(f"  - {result['title']} (score: {result['score']:.2f})")

if __name__ == "__main__":
    main()