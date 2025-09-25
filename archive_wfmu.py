#!/usr/bin/env python3
import asyncio
import aiohttp
import click
import logging
from pathlib import Path
from database import init_database
from scraper import WFMUBlogScraper
from media_downloader import MediaDownloader
from content_parser import ContentParser
from search_index import SearchIndex
from verify import ArchiveVerifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@click.group()
def cli():
    """WFMU Blog Archive Tool - Preserve the WFMU blog for posterity"""
    pass

@cli.command()
@click.option('--resume', is_flag=True, help='Resume from last scraping position')
@click.option('--categories-only', is_flag=True, help='Only scrape category pages')
async def scrape(resume, categories_only):
    """Scrape the WFMU blog posts and save to database"""
    logger.info("Starting WFMU blog scraping...")
    scraper = WFMUBlogScraper()

    if categories_only:
        async with aiohttp.ClientSession() as session:
            await scraper.scrape_categories(session)
    else:
        await scraper.run_full_scrape()

    logger.info("Scraping complete!")

@cli.command()
@click.option('--retry-failed', is_flag=True, help='Retry failed downloads')
async def download_media(retry_failed):
    """Download all media files from scraped posts"""
    logger.info("Starting media download...")
    downloader = MediaDownloader()

    if retry_failed:
        downloaded, failed = await downloader.retry_failed_downloads()
    else:
        downloaded, failed = await downloader.download_all_media()

    logger.info(f"Downloaded {downloaded} files, {failed} failures")

@cli.command()
def parse_content():
    """Parse HTML content to extract clean text and markdown"""
    logger.info("Starting content parsing...")
    parser = ContentParser()
    parser.process_all_posts()
    parser.update_missing_metadata()
    logger.info("Content parsing complete!")

@cli.command()
def build_index():
    """Build search index from parsed content"""
    logger.info("Building search index...")
    search = SearchIndex()
    search.index_all_posts()
    logger.info("Search index built!")

@cli.command()
@click.argument('query')
@click.option('--limit', default=10, help='Number of results to show')
def search(query, limit):
    """Search the archived blog posts"""
    search_index = SearchIndex()
    results = search_index.search(query, limit=limit)

    if not results:
        click.echo("No results found")
        return

    click.echo(f"\nFound {len(results)} results for '{query}':\n")

    for i, result in enumerate(results, 1):
        click.echo(f"{i}. {result['title']}")
        click.echo(f"   Author: {result['author']}")
        click.echo(f"   URL: {result['url']}")
        click.echo(f"   Score: {result['score']:.2f}")
        click.echo()

@cli.command()
def verify():
    """Verify archive integrity and generate report"""
    logger.info("Verifying archive...")
    verifier = ArchiveVerifier()
    verifier.print_summary()
    report = verifier.generate_report()
    logger.info("Verification complete! Report saved to archive_report.json")

@cli.command()
@click.pass_context
def full_archive(ctx):
    """Run the complete archiving process"""
    logger.info("Starting full archive process...")

    async def run_async_tasks():
        logger.info("Step 1: Scraping blog...")
        scraper = WFMUBlogScraper()
        await scraper.run_full_scrape()

        logger.info("Step 2: Downloading media...")
        downloader = MediaDownloader()
        await downloader.download_all_media()

    asyncio.run(run_async_tasks())

    logger.info("Step 3: Parsing content...")
    parser = ContentParser()
    parser.process_all_posts()
    parser.update_missing_metadata()

    logger.info("Step 4: Building search index...")
    search_index = SearchIndex()
    search_index.index_all_posts()

    logger.info("Step 5: Verifying archive...")
    verifier = ArchiveVerifier()
    verifier.print_summary()
    verifier.generate_report()

    logger.info("✅ Full archive process complete!")

@cli.command()
def stats():
    """Show archive statistics"""
    verifier = ArchiveVerifier()
    verifier.print_summary()

@cli.command()
def export_json():
    """Export all posts to JSON format"""
    from database import init_database, Post
    import json

    session, _ = init_database()
    posts = session.query(Post).all()

    export_data = []
    for post in posts:
        export_data.append({
            'post_id': post.post_id,
            'url': post.url,
            'title': post.title,
            'author': post.author,
            'published_date': post.published_date.isoformat() if post.published_date else None,
            'content_text': post.content_text,
            'categories': [cat.name for cat in post.categories],
            'media_count': len(post.media_items),
            'comment_count': len(post.comments)
        })

    output_file = 'wfmu_posts_export.json'
    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2)

    logger.info(f"Exported {len(export_data)} posts to {output_file}")

if __name__ == '__main__':
    cli()