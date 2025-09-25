import logging
from database import init_database, Post, Media, Comment, Category
from pathlib import Path
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArchiveVerifier:
    def __init__(self, db_session=None, media_dir='media'):
        self.session, _ = init_database() if not db_session else (db_session, None)
        self.media_dir = Path(media_dir)

    def get_statistics(self):
        stats = {}

        stats['total_posts'] = self.session.query(Post).count()
        stats['posts_with_content'] = self.session.query(Post).filter(
            Post.content_text.isnot(None)
        ).count()
        stats['posts_with_markdown'] = self.session.query(Post).filter(
            Post.content_markdown.isnot(None)
        ).count()

        stats['total_media'] = self.session.query(Media).count()
        stats['downloaded_media'] = self.session.query(Media).filter_by(downloaded=True).count()
        stats['failed_media'] = self.session.query(Media).filter(
            Media.download_error.isnot(None)
        ).count()

        stats['total_comments'] = self.session.query(Comment).count()
        stats['total_categories'] = self.session.query(Category).count()

        stats['unique_authors'] = self.session.query(Post.author).distinct().count()

        date_range = self.session.query(
            Post.published_date
        ).filter(Post.published_date.isnot(None)).all()

        if date_range:
            dates = [d[0] for d in date_range if d[0]]
            if dates:
                stats['earliest_post'] = min(dates).strftime('%Y-%m-%d')
                stats['latest_post'] = max(dates).strftime('%Y-%m-%d')

        media_by_type = {}
        for media_type in ['image', 'audio', 'video']:
            count = self.session.query(Media).filter_by(media_type=media_type).count()
            media_by_type[media_type] = count
        stats['media_by_type'] = media_by_type

        return stats

    def verify_media_files(self):
        issues = []

        media_items = self.session.query(Media).filter_by(downloaded=True).all()

        for media in media_items:
            if media.local_path:
                path = Path(media.local_path)
                if not path.exists():
                    issues.append({
                        'type': 'missing_file',
                        'media_id': media.id,
                        'expected_path': media.local_path,
                        'url': media.original_url
                    })
                elif path.stat().st_size == 0:
                    issues.append({
                        'type': 'empty_file',
                        'media_id': media.id,
                        'path': media.local_path,
                        'url': media.original_url
                    })

        return issues

    def verify_database_integrity(self):
        issues = []

        posts_without_content = self.session.query(Post).filter(
            Post.raw_html.isnot(None),
            Post.content_text.is_(None)
        ).count()

        if posts_without_content > 0:
            issues.append({
                'type': 'posts_without_extracted_content',
                'count': posts_without_content
            })

        posts_without_title = self.session.query(Post).filter(
            Post.title.is_(None)
        ).count()

        if posts_without_title > 0:
            issues.append({
                'type': 'posts_without_title',
                'count': posts_without_title
            })

        orphaned_media = self.session.query(Media).filter(
            ~Media.post_id.in_(
                self.session.query(Post.post_id)
            )
        ).count()

        if orphaned_media > 0:
            issues.append({
                'type': 'orphaned_media',
                'count': orphaned_media
            })

        return issues

    def check_missing_posts(self):
        categories = self.session.query(Category).all()
        discrepancies = []

        for category in categories:
            if category.post_count:
                actual_count = len(category.posts)
                if actual_count < category.post_count:
                    discrepancies.append({
                        'category': category.name,
                        'expected': category.post_count,
                        'actual': actual_count,
                        'missing': category.post_count - actual_count
                    })

        return discrepancies

    def generate_report(self, output_file='archive_report.json'):
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'statistics': self.get_statistics(),
            'media_file_issues': self.verify_media_files(),
            'database_issues': self.verify_database_integrity(),
            'missing_posts': self.check_missing_posts()
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Report saved to {output_file}")
        return report

    def print_summary(self):
        stats = self.get_statistics()
        media_issues = self.verify_media_files()
        db_issues = self.verify_database_integrity()
        missing = self.check_missing_posts()

        print("\n=== WFMU Blog Archive Summary ===\n")

        print("📊 Statistics:")
        print(f"  Total Posts: {stats['total_posts']}")
        print(f"  Posts with Content: {stats['posts_with_content']}")
        print(f"  Total Comments: {stats['total_comments']}")
        print(f"  Total Categories: {stats['total_categories']}")
        print(f"  Unique Authors: {stats['unique_authors']}")

        if 'earliest_post' in stats:
            print(f"  Date Range: {stats['earliest_post']} to {stats['latest_post']}")

        print(f"\n📁 Media Files:")
        print(f"  Total Media: {stats['total_media']}")
        print(f"  Downloaded: {stats['downloaded_media']}")
        print(f"  Failed: {stats['failed_media']}")

        if stats.get('media_by_type'):
            print("  By Type:")
            for media_type, count in stats['media_by_type'].items():
                print(f"    {media_type}: {count}")

        if media_issues:
            print(f"\n⚠️  Media File Issues: {len(media_issues)}")
            for issue in media_issues[:5]:
                print(f"    - {issue['type']}: {issue.get('path', issue.get('expected_path'))}")

        if db_issues:
            print(f"\n⚠️  Database Issues:")
            for issue in db_issues:
                print(f"    - {issue['type']}: {issue['count']}")

        if missing:
            total_missing = sum(d['missing'] for d in missing)
            print(f"\n⚠️  Potentially Missing Posts: {total_missing}")
            for disc in missing[:5]:
                print(f"    - {disc['category']}: {disc['missing']} posts missing")

        print("\n" + "="*35)

def main():
    verifier = ArchiveVerifier()
    verifier.print_summary()
    verifier.generate_report()

if __name__ == "__main__":
    main()