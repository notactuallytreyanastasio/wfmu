#!/usr/bin/env python3
"""
WFMU Archive Viewer with Live Autocomplete Search
Uses a copy of the database to avoid concurrency issues
"""

from flask import Flask, render_template_string, request, jsonify
import sqlite3
import math
from urllib.parse import quote_plus

app = Flask(__name__)

POSTS_PER_PAGE = 50
DB_PATH = 'wfmu_archive_viewer.db'  # Uses the copy

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>WFMU Blog Archive</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: Georgia, serif;
            font-size: 13px;
            background: #fff;
            color: #333;
        }

        header {
            background: #FF6600;
            border-bottom: 3px solid #333;
            padding: 10px 20px;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        header h1 {
            font-size: 20px;
            color: white;
            display: inline;
        }

        .stats {
            display: inline;
            margin-left: 20px;
            color: #fff;
            font-size: 12px;
            opacity: 0.9;
        }

        .search-bar {
            background: #f9f9f9;
            border-bottom: 1px solid #FFCC00;
            padding: 8px 20px;
            position: sticky;
            top: 48px;
            z-index: 99;
        }

        .search-container {
            max-width: 1200px;
            margin: 0 auto;
            position: relative;
        }

        input[type="search"] {
            padding: 4px 8px;
            font-size: 12px;
            border: 1px solid #FF6600;
            border-radius: 3px;
            width: 250px;
        }

        input[type="search"]:focus {
            outline: none;
            border-color: #0066CC;
            box-shadow: 0 0 0 2px rgba(255, 102, 0, 0.2);
        }

        button {
            padding: 4px 12px;
            background: #0066CC;
            color: white;
            border: none;
            border-radius: 3px;
            font-size: 12px;
            cursor: pointer;
        }

        button:hover {
            background: #0055aa;
        }

        .clear-search {
            margin-left: 5px;
            background: #666;
        }

        /* Autocomplete dropdown */
        .autocomplete-dropdown {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #FF6600;
            border-top: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            max-height: 300px;
            overflow-y: auto;
            display: none;
            z-index: 101;
        }

        .autocomplete-dropdown.active {
            display: block;
        }

        .autocomplete-item {
            padding: 6px 10px;
            border-bottom: 1px solid #f0f0f0;
            cursor: pointer;
            transition: background 0.2s;
        }

        .autocomplete-item:hover {
            background: #fffbf0;
        }

        .autocomplete-item .title {
            color: #0066CC;
            font-size: 12px;
            margin-bottom: 2px;
            font-weight: bold;
        }

        .autocomplete-item .meta {
            font-size: 10px;
            color: #666;
            margin-bottom: 2px;
        }

        .autocomplete-item .snippet {
            font-size: 11px;
            color: #555;
            display: -webkit-box;
            -webkit-line-clamp: 1;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        .autocomplete-item mark {
            background: #FFFF00;
            font-weight: bold;
        }

        .container {
            max-width: 1200px;
            margin: 10px auto;
            padding: 0 20px;
        }

        .search-info {
            padding: 10px;
            background: #fffbf0;
            border: 1px solid #FFCC00;
            margin-bottom: 10px;
            font-size: 12px;
        }

        .posts {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 10px;
        }

        .post {
            border: 1px solid #e0e0e0;
            padding: 8px;
            transition: all 0.2s;
            background: white;
        }

        .post:hover {
            border-color: #FF6600;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .post h3 {
            font-size: 13px;
            margin-bottom: 4px;
            line-height: 1.3;
        }

        .post h3 a {
            color: #0066CC;
            text-decoration: none;
        }

        .post h3 a:hover {
            color: #FF6600;
            text-decoration: underline;
        }

        .post .meta {
            font-size: 11px;
            color: #666;
            margin-bottom: 4px;
        }

        .post .excerpt {
            font-size: 11px;
            color: #333;
            line-height: 1.4;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        .highlight {
            background: #FFFF00;
            font-weight: bold;
        }

        .pagination {
            margin: 20px 0;
            text-align: center;
        }

        .pagination a, .pagination span {
            display: inline-block;
            padding: 4px 8px;
            margin: 0 2px;
            background: #f0f0f0;
            border: 1px solid #ccc;
            text-decoration: none;
            color: #333;
            font-size: 12px;
        }

        .pagination a:hover {
            background: #FFCC00;
        }

        .pagination .active {
            background: #FF6600;
            color: white;
            border-color: #FF6600;
        }

        .no-results {
            padding: 40px;
            text-align: center;
            color: #666;
        }

        .loading {
            font-size: 11px;
            color: #666;
            padding: 4px 10px;
            font-style: italic;
        }
    </style>
</head>
<body>
    <header>
        <h1>📻 WFMU Blog Archive</h1>
        <span class="stats">{{ total_posts }} posts archived</span>
    </header>

    <div class="search-bar">
        <div class="search-container">
            <form method="get" action="/" style="display: inline;">
                <input type="search"
                       id="search-input"
                       name="q"
                       value="{{ query }}"
                       placeholder="Search posts, titles, authors..."
                       autocomplete="off"
                       autofocus>
                <button type="submit">Search</button>
                {% if query %}
                <a href="/"><button type="button" class="clear-search">Clear</button></a>
                {% endif %}
            </form>
            <div id="autocomplete-dropdown" class="autocomplete-dropdown"></div>
        </div>
    </div>

    <div class="container">
        {% if query %}
        <div class="search-info">
            Searching for: "<strong>{{ query }}</strong>" -
            Found {{ total_results }} result{% if total_results != 1 %}s{% endif %}
        </div>
        {% endif %}

        {% if posts %}
        <div class="posts">
            {% for post in posts %}
            <div class="post">
                <h3><a href="/post/{{ post.id }}" target="_blank">{{ post.title | safe }}</a></h3>
                <div class="meta">
                    {% if post.author %}{{ post.author }} • {% endif %}
                    {% if post.date %}{{ post.date }}{% endif %}
                    {% if post.media_count > 0 %} • 📎 {{ post.media_count }} media{% endif %}
                </div>
                <div class="excerpt">{{ post.excerpt | safe }}...</div>
            </div>
            {% endfor %}
        </div>

        <div class="pagination">
            {% if page > 1 %}
            <a href="?page=1{% if query %}&q={{ query | urlencode }}{% endif %}">« First</a>
            <a href="?page={{ page - 1 }}{% if query %}&q={{ query | urlencode }}{% endif %}">‹ Previous</a>
            {% endif %}

            {% for p in page_range %}
                {% if p == page %}
                <span class="active">{{ p }}</span>
                {% else %}
                <a href="?page={{ p }}{% if query %}&q={{ query | urlencode }}{% endif %}">{{ p }}</a>
                {% endif %}
            {% endfor %}

            {% if page < total_pages %}
            <a href="?page={{ page + 1 }}{% if query %}&q={{ query | urlencode }}{% endif %}">Next ›</a>
            <a href="?page={{ total_pages }}{% if query %}&q={{ query | urlencode }}{% endif %}">Last »</a>
            {% endif %}
        </div>
        {% else %}
        <div class="no-results">
            {% if query %}
            No results found for "{{ query }}"
            {% else %}
            No posts found
            {% endif %}
        </div>
        {% endif %}
    </div>

    <script>
    let searchTimeout = null;
    const searchInput = document.getElementById('search-input');
    const searchDropdown = document.getElementById('autocomplete-dropdown');

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();

        // Clear timeout if user is still typing
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }

        if (query.length < 2) {
            searchDropdown.classList.remove('active');
            searchDropdown.innerHTML = '';
            return;
        }

        // Show loading
        searchDropdown.innerHTML = '<div class="loading">Searching...</div>';
        searchDropdown.classList.add('active');

        // Debounce search
        searchTimeout = setTimeout(async () => {
            try {
                const response = await fetch('/api/search?q=' + encodeURIComponent(query));
                const data = await response.json();

                if (data.results.length === 0) {
                    searchDropdown.innerHTML = '<div class="loading">No results found</div>';
                } else {
                    searchDropdown.innerHTML = data.results.map(result => `
                        <div class="autocomplete-item" onclick="window.location.href='/post/${result.id}'">
                            <div class="title">${highlightMatch(result.title, query)}</div>
                            <div class="meta">
                                ${result.author ? result.author + ' • ' : ''}
                                ${result.date || ''}
                            </div>
                            <div class="snippet">${highlightMatch(result.snippet, query)}</div>
                        </div>
                    `).join('');
                }
            } catch (error) {
                console.error('Search error:', error);
                searchDropdown.innerHTML = '<div class="loading">Error searching</div>';
            }
        }, 300);
    });

    // Highlight search matches
    function highlightMatch(text, query) {
        if (!text) return '';
        const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }

    function escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
    }

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-container')) {
            searchDropdown.classList.remove('active');
        }
    });

    // Handle Enter key
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchDropdown.classList.remove('active');
        }
    });
    </script>
</body>
</html>
'''

POST_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>{{ post.title or 'Post' }} - WFMU Archive</title>
    <style>
        body {
            font-family: Georgia, serif;
            max-width: 800px;
            margin: 20px auto;
            padding: 0 20px;
            line-height: 1.6;
        }
        h1 { color: #FF6600; font-size: 24px; }
        .meta { color: #666; margin-bottom: 20px; }
        .content { font-size: 14px; }
        .content p { margin-bottom: 1em; }
        a { color: #0066CC; }
        .back { margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="back"><a href="/">← Back to Archive</a></div>
    <h1>{{ post.title or 'Untitled' }}</h1>
    <div class="meta">
        {% if post.author %}By {{ post.author }} • {% endif %}
        {% if post.date %}{{ post.date }}{% endif %}
    </div>
    <div class="content">
        {% if post.content %}
        {{ post.content | safe }}
        {% else %}
        <p>No content available</p>
        {% endif %}
    </div>
    {% if post.url %}
    <p><a href="{{ post.url }}" target="_blank">View original post →</a></p>
    {% endif %}
</body>
</html>
'''

def highlight_text(text, query):
    """Highlight search terms in text"""
    if not query or not text:
        return text

    import re
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(f'<span class="highlight">{query}</span>', text)

def get_page_range(current_page, total_pages):
    """Generate page numbers to display"""
    if total_pages <= 10:
        return range(1, total_pages + 1)

    start = max(1, current_page - 3)
    end = min(total_pages, current_page + 3)

    if end - start < 7:
        if start == 1:
            end = min(total_pages, start + 6)
        else:
            start = max(1, end - 6)

    return range(start, end + 1)

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    query = request.args.get('q', '').strip()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Build SQL query
    if query:
        count_sql = """
            SELECT COUNT(*) FROM posts
            WHERE title LIKE ? OR content_text LIKE ? OR author LIKE ?
        """
        search_pattern = f'%{query}%'
        total_results = cur.execute(count_sql, (search_pattern, search_pattern, search_pattern)).fetchone()[0]

        posts_sql = """
            SELECT p.post_id, p.title, p.author, p.url, p.published_date,
                   SUBSTR(p.content_text, 1, 200) as excerpt,
                   (SELECT COUNT(*) FROM media WHERE post_id = p.post_id) as media_count
            FROM posts p
            WHERE p.title LIKE ? OR p.content_text LIKE ? OR p.author LIKE ?
            ORDER BY p.published_date DESC
            LIMIT ? OFFSET ?
        """
        posts_data = cur.execute(posts_sql,
                                 (search_pattern, search_pattern, search_pattern,
                                  POSTS_PER_PAGE, (page - 1) * POSTS_PER_PAGE)).fetchall()
    else:
        total_results = cur.execute("SELECT COUNT(*) FROM posts").fetchone()[0]

        posts_sql = """
            SELECT p.post_id, p.title, p.author, p.url, p.published_date,
                   SUBSTR(p.content_text, 1, 200) as excerpt,
                   (SELECT COUNT(*) FROM media WHERE post_id = p.post_id) as media_count
            FROM posts p
            ORDER BY p.published_date DESC
            LIMIT ? OFFSET ?
        """
        posts_data = cur.execute(posts_sql, (POSTS_PER_PAGE, (page - 1) * POSTS_PER_PAGE)).fetchall()

    # Get total posts count for header
    total_posts = cur.execute("SELECT COUNT(*) FROM posts").fetchone()[0]

    posts = []
    for row in posts_data:
        title = row['title'] or 'Untitled'
        excerpt = row['excerpt'] or ''

        if query:
            title = highlight_text(title, query)
            excerpt = highlight_text(excerpt, query)

        posts.append({
            'id': row['post_id'],
            'title': title,
            'author': row['author'],
            'url': row['url'],
            'date': row['published_date'][:10] if row['published_date'] else None,
            'excerpt': excerpt,
            'media_count': row['media_count']
        })

    conn.close()

    total_pages = math.ceil(total_results / POSTS_PER_PAGE)
    page_range = get_page_range(page, total_pages)

    return render_template_string(
        HTML_TEMPLATE,
        posts=posts,
        page=page,
        total_pages=total_pages,
        total_posts=total_posts,
        total_results=total_results,
        query=query,
        page_range=page_range,
        urlencode=quote_plus
    )

@app.route('/api/search')
def search():
    """API endpoint for live search"""
    query = request.args.get('q', '').strip()

    if not query or len(query) < 2:
        return jsonify({'results': []})

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    search_pattern = f'%{query}%'

    posts_sql = """
        SELECT p.post_id, p.title, p.author, p.published_date,
               SUBSTR(p.content_text, 1, 150) as snippet
        FROM posts p
        WHERE p.title LIKE ? OR p.content_text LIKE ? OR p.author LIKE ?
        ORDER BY p.published_date DESC
        LIMIT 10
    """

    posts_data = cur.execute(posts_sql, (search_pattern, search_pattern, search_pattern)).fetchall()

    results = []
    for row in posts_data:
        results.append({
            'id': row['post_id'],
            'title': row['title'] or 'Untitled',
            'author': row['author'],
            'date': row['published_date'][:10] if row['published_date'] else None,
            'snippet': row['snippet'] or ''
        })

    conn.close()

    return jsonify({'results': results})

@app.route('/post/<post_id>')
def view_post(post_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    post_data = cur.execute("""
        SELECT post_id, title, author, url, published_date, content_text
        FROM posts
        WHERE post_id = ?
    """, (post_id,)).fetchone()

    conn.close()

    if not post_data:
        return "Post not found", 404

    # Format content with paragraphs
    content = post_data['content_text'] or ''
    if content:
        # Convert line breaks to paragraphs
        paragraphs = content.split('\n\n')
        formatted_content = ''.join(f'<p>{p.replace(chr(10), "<br>")}</p>' for p in paragraphs if p.strip())
    else:
        formatted_content = None

    post = {
        'title': post_data['title'],
        'author': post_data['author'],
        'url': post_data['url'],
        'date': post_data['published_date'][:10] if post_data['published_date'] else None,
        'content': formatted_content
    }

    return render_template_string(POST_TEMPLATE, post=post)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎙️  WFMU BLOG ARCHIVE VIEWER - WITH AUTOCOMPLETE")
    print("="*60)
    print("\nFeatures:")
    print("  ✓ Live autocomplete search as you type")
    print("  ✓ Full-text search")
    print("  ✓ Pagination (50 posts per page)")
    print("  ✓ Compact grid layout")
    print("  ✓ Post viewer with formatted content")
    print("\nOpen: http://localhost:8083")
    print("\nUsing database copy: wfmu_archive_viewer.db")
    print("="*60 + "\n")

    app.run(port=8083, debug=False)