#!/usr/bin/env python3
"""
WFMU Blog Archive Viewer
A Flask web application to browse and search the archived blog
"""

from flask import Flask, render_template, jsonify, request, send_from_directory, Response
from flask_cors import CORS
from database import init_database, Post, Media, Category, Comment
from sqlalchemy import or_, func
from datetime import datetime
import os
from pathlib import Path
from urllib.parse import urlparse
import json

app = Flask(__name__)
CORS(app)
session, _ = init_database()

# Configuration
MEDIA_DIR = Path('media')
POSTS_PER_PAGE = 20

@app.route('/')
def index():
    """Main page with search and browse interface"""
    return render_template('index.html')

@app.route('/api/posts')
def get_posts():
    """Get paginated posts"""
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '')

    query = session.query(Post)

    if search_query:
        search_pattern = f'%{search_query}%'
        query = query.filter(
            or_(
                Post.title.ilike(search_pattern),
                Post.content_text.ilike(search_pattern),
                Post.author.ilike(search_pattern)
            )
        )

    # Order by date, most recent first
    query = query.order_by(Post.published_date.desc().nullslast(), Post.scraped_at.desc())

    # Paginate
    total = query.count()
    posts = query.offset((page - 1) * POSTS_PER_PAGE).limit(POSTS_PER_PAGE).all()

    return jsonify({
        'posts': [serialize_post(p) for p in posts],
        'total': total,
        'page': page,
        'pages': (total + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE
    })

@app.route('/api/search')
def search():
    """Live search endpoint"""
    query = request.args.get('q', '')
    limit = request.args.get('limit', 10, type=int)

    if not query or len(query) < 2:
        return jsonify({'results': []})

    search_pattern = f'%{query}%'

    posts = session.query(Post).filter(
        or_(
            Post.title.ilike(search_pattern),
            Post.content_text.ilike(search_pattern),
            Post.author.ilike(search_pattern)
        )
    ).limit(limit).all()

    results = []
    for post in posts:
        # Create snippet with highlighted match
        snippet = ''
        if post.content_text:
            # Find the match location
            text = post.content_text[:500]
            snippet = text

        results.append({
            'id': post.post_id,
            'title': post.title or 'Untitled',
            'author': post.author,
            'date': post.published_date.isoformat() if post.published_date else None,
            'snippet': snippet,
            'url': post.url
        })

    return jsonify({'results': results})

@app.route('/post/<post_id>')
def view_post(post_id):
    """View a single post"""
    post = session.query(Post).filter_by(post_id=post_id).first_or_404()
    return render_template('post.html', post=post)

@app.route('/post/<post_id>/original')
def view_original(post_id):
    """View the original HTML of a post"""
    post = session.query(Post).filter_by(post_id=post_id).first_or_404()
    if post.raw_html:
        # Inject a banner at the top
        banner = '''
        <div style="background: #333; color: white; padding: 10px; font-family: sans-serif; position: fixed; top: 0; left: 0; right: 0; z-index: 9999;">
            <a href="/post/{}" style="color: white; margin-right: 20px;">← Back to Archive View</a>
            <span>Original WFMU Blog Post (Archived)</span>
        </div>
        <div style="height: 40px;"></div>
        '''.format(post_id)

        # Inject the banner after the <body> tag
        html = post.raw_html
        if '<body' in html:
            parts = html.split('<body', 1)
            if len(parts) == 2:
                body_parts = parts[1].split('>', 1)
                if len(body_parts) == 2:
                    html = parts[0] + '<body' + body_parts[0] + '>' + banner + body_parts[1]

        return Response(html, mimetype='text/html')
    return "No original HTML available", 404

@app.route('/api/post/<post_id>')
def get_post(post_id):
    """Get post data as JSON"""
    post = session.query(Post).filter_by(post_id=post_id).first_or_404()
    return jsonify(serialize_post_full(post))

@app.route('/api/stats')
def get_stats():
    """Get archive statistics"""
    total_posts = session.query(Post).count()
    total_media = session.query(Media).count()
    total_authors = session.query(func.count(func.distinct(Post.author))).scalar()
    total_categories = session.query(Category).count()

    # Get date range
    earliest = session.query(func.min(Post.published_date)).scalar()
    latest = session.query(func.max(Post.published_date)).scalar()

    return jsonify({
        'total_posts': total_posts,
        'total_media': total_media,
        'total_authors': total_authors,
        'total_categories': total_categories,
        'date_range': {
            'start': earliest.isoformat() if earliest else None,
            'end': latest.isoformat() if latest else None
        }
    })

@app.route('/media/<path:filename>')
def serve_media(filename):
    """Serve archived media files"""
    return send_from_directory(MEDIA_DIR, filename)

def serialize_post(post):
    """Serialize a post for JSON response"""
    return {
        'id': post.post_id,
        'title': post.title or 'Untitled',
        'author': post.author,
        'url': post.url,
        'date': post.published_date.isoformat() if post.published_date else None,
        'excerpt': post.content_text[:200] if post.content_text else '',
        'media_count': len(post.media_items),
        'has_original': bool(post.raw_html)
    }

def serialize_post_full(post):
    """Serialize a full post with all details"""
    return {
        'id': post.post_id,
        'title': post.title or 'Untitled',
        'author': post.author,
        'url': post.url,
        'date': post.published_date.isoformat() if post.published_date else None,
        'content': post.content_text,
        'content_markdown': post.content_markdown,
        'categories': [cat.name for cat in post.categories],
        'media': [
            {
                'type': m.media_type,
                'url': m.original_url,
                'local': m.local_path,
                'downloaded': m.downloaded
            } for m in post.media_items
        ],
        'comments': [
            {
                'author': c.author,
                'date': c.date.isoformat() if c.date else None,
                'content': c.content
            } for c in post.comments
        ],
        'has_original': bool(post.raw_html)
    }

if __name__ == '__main__':
    app.run(debug=True, port=5000)