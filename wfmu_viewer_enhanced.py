#!/usr/bin/env python3
"""
WFMU Archive Viewer - Enhanced with Sidebar Browsing
Features: Autocomplete search, year/month browsing, author selection
"""

from flask import Flask, render_template_string, request, jsonify, send_from_directory
import sqlite3
import math
import os
from urllib.parse import quote_plus
from collections import defaultdict
from datetime import datetime

app = Flask(__name__)

POSTS_PER_PAGE = 50
DB_PATH = 'wfmu_archive_viewer.db'

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
            background: #f5f5f5;
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

        header a.gallery-link {
            color: white;
            text-decoration: none;
            margin-left: 20px;
            font-size: 14px;
            border: 1px solid white;
            padding: 3px 8px;
            border-radius: 3px;
        }

        header a.gallery-link:hover {
            background: rgba(255,255,255,0.2);
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
            max-width: 1400px;
            margin: 0 auto;
            position: relative;
        }

        .search-form {
            display: flex;
            gap: 5px;
        }

        input[type="search"] {
            padding: 4px 8px;
            font-size: 12px;
            border: 1px solid #FF6600;
            border-radius: 3px;
            width: 250px;
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

        .main-content {
            display: flex;
            max-width: 1400px;
            margin: 0 auto;
            gap: 20px;
            padding: 20px;
        }

        /* Sidebar Styles */
        .sidebar {
            width: 250px;
            flex-shrink: 0;
        }

        .sidebar-section {
            background: white;
            border: 1px solid #ddd;
            margin-bottom: 15px;
            border-radius: 3px;
        }

        .sidebar-section h3 {
            background: #f0f0f0;
            padding: 8px 10px;
            font-size: 13px;
            border-bottom: 1px solid #ddd;
            color: #FF6600;
        }

        .sidebar-section .content {
            padding: 10px;
        }

        /* Year/Month Browser */
        .year-browser {
            max-height: 400px;
            overflow-y: auto;
        }

        .year-item {
            margin-bottom: 5px;
        }

        .year-toggle {
            display: block;
            width: 100%;
            text-align: left;
            background: #f9f9f9;
            border: 1px solid #e0e0e0;
            padding: 5px 8px;
            font-size: 12px;
            color: #333;
            cursor: pointer;
            transition: all 0.2s;
        }

        .year-toggle:hover {
            background: #FFCC00;
        }

        .year-toggle.active {
            background: #FFCC00;
            color: #333;
            font-weight: bold;
        }

        .month-list {
            display: none;
            padding-left: 15px;
            margin-top: 5px;
        }

        .month-list.active {
            display: block;
        }

        .month-link {
            display: block;
            padding: 3px 8px;
            font-size: 11px;
            color: #0066CC;
            text-decoration: none;
            transition: all 0.2s;
        }

        .month-link:hover {
            background: #f0f0f0;
            padding-left: 12px;
        }

        .month-link.active {
            background: #FFCC00;
            font-weight: bold;
        }

        /* Author Browser */
        .author-list {
            max-height: 300px;
            overflow-y: auto;
        }

        .author-link {
            display: block;
            padding: 4px 8px;
            font-size: 11px;
            color: #0066CC;
            text-decoration: none;
            transition: all 0.2s;
            border-bottom: 1px solid #f0f0f0;
        }

        .author-link:hover {
            background: #f9f9f9;
            padding-left: 12px;
        }

        .author-link.active {
            background: #FFCC00;
            font-weight: bold;
        }

        .author-count {
            float: right;
            color: #999;
            font-size: 10px;
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
            max-width: 500px;
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

        .content-area {
            flex: 1;
            min-width: 0;
        }

        .filter-info {
            padding: 10px;
            background: #fffbf0;
            border: 1px solid #FFCC00;
            margin-bottom: 10px;
            font-size: 12px;
        }

        .posts {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
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
            background: white;
            border: 1px solid #ddd;
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
        <a href="/gallery" class="gallery-link">📸 Image Gallery</a>
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
                <input type="hidden" name="year" value="{{ selected_year }}">
                <input type="hidden" name="month" value="{{ selected_month }}">
                <button type="submit">Search</button>
                {% if query or selected_year %}
                <a href="/"><button type="button" class="clear-search">Clear All</button></a>
                {% endif %}
            </form>
            <div id="autocomplete-dropdown" class="autocomplete-dropdown"></div>
        </div>
    </div>

    <div class="main-content">
        <div class="sidebar">
            <!-- Browse by Date -->
            <div class="sidebar-section">
                <h3>📅 Browse by Date</h3>
                <div class="content year-browser">
                    {% for year, months in archive_dates %}
                    <div class="year-item">
                        <button class="year-toggle {% if year == selected_year %}active{% endif %}"
                                onclick="toggleYear('{{ year }}')">
                            {{ year }} ({{ months | sum(attribute='count') }} posts)
                        </button>
                        <div class="month-list {% if year == selected_year %}active{% endif %}" id="year-{{ year }}">
                            {% for month_data in months %}
                            <a href="/?year={{ year }}&month={{ month_data.month }}"
                               style="color:black"
                               class="month-link {% if year == selected_year and month_data.month == selected_month %}active{% endif %}">
                                {{ month_data.name }} ({{ month_data.count }})
                            </a>
                            {% endfor %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>

        </div>

        <div class="content-area">
            {% if query or selected_year or selected_author %}
            <div class="filter-info">
                Filtering by:
                {% if query %}<strong>Search: "{{ query }}"</strong> • {% endif %}
                {% if selected_year %}<strong>Year: {{ selected_year }}</strong>{% endif %}
                {% if selected_month %}<strong> / {{ selected_month_name }}</strong>{% endif %}
                - Found {{ total_results }} result{% if total_results != 1 %}s{% endif %}
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
                <a href="?page=1{{ filter_params }}">« First</a>
                <a href="?page={{ page - 1 }}{{ filter_params }}">‹ Previous</a>
                {% endif %}

                {% for p in page_range %}
                    {% if p == page %}
                    <span class="active">{{ p }}</span>
                    {% else %}
                    <a href="?page={{ p }}{{ filter_params }}">{{ p }}</a>
                    {% endif %}
                {% endfor %}

                {% if page < total_pages %}
                <a href="?page={{ page + 1 }}{{ filter_params }}">Next ›</a>
                <a href="?page={{ total_pages }}{{ filter_params }}">Last »</a>
                {% endif %}
            </div>
            {% else %}
            <div class="no-results">
                {% if query or selected_year %}
                No results found for your filters
                {% else %}
                No posts found
                {% endif %}
            </div>
            {% endif %}
        </div>
    </div>

    <script>
    let searchTimeout = null;
    const searchInput = document.getElementById('search-input');
    const searchDropdown = document.getElementById('autocomplete-dropdown');

    // Toggle year dropdown
    function toggleYear(year) {
        const yearList = document.getElementById('year-' + year);
        const toggle = yearList.previousElementSibling;

        yearList.classList.toggle('active');
        toggle.classList.toggle('active');
    }

    // Autocomplete search
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();

        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }

        if (query.length < 2) {
            searchDropdown.classList.remove('active');
            searchDropdown.innerHTML = '';
            return;
        }

        searchDropdown.innerHTML = '<div class="loading">Searching...</div>';
        searchDropdown.classList.add('active');

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
        }, 200);
    });

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
        .view-options {
            background: #f5f5f5;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            border: 1px solid #ddd;
        }
        .view-options h3 {
            margin-top: 0;
            font-size: 14px;
            color: #666;
        }
        .view-button {
            display: inline-block;
            padding: 8px 15px;
            margin-right: 10px;
            background: #FF6600;
            color: white;
            text-decoration: none;
            border-radius: 3px;
            font-size: 13px;
        }
        .view-button:hover {
            background: #e55500;
        }
        .view-button.secondary {
            background: #666;
        }
        .view-button.secondary:hover {
            background: #555;
        }
    </style>
</head>
<body>
    <div class="back"><a href="/">← Back to Archive</a></div>
    <h1>{{ post.title or 'Untitled' }}</h1>
    <div class="meta">
        {% if post.author %}By {{ post.author }} • {% endif %}
        {% if post.date %}{{ post.date }}{% endif %}
    </div>

    <div class="view-options">
        <h3>View Options:</h3>
        <a href="/post/{{ post.id }}/original" class="view-button">
            🖼️ View Original Layout (as it appeared on WFMU)
        </a>
        {% if post.url %}
        <a href="https://web.archive.org/web/2015/{{ post.url }}" class="view-button secondary" target="_blank">
            🌐 View on Archive.org
        </a>
        {% endif %}
    </div>

    <div class="content">
        {% if post.content %}
        {{ post.content | safe }}
        {% else %}
        <p>No content available</p>
        {% endif %}
    </div>
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

def get_archive_structure(conn):
    """Get year/month structure for sidebar"""
    cur = conn.cursor()

    # Get all posts with dates
    posts_by_date = cur.execute("""
        SELECT strftime('%Y', published_date) as year,
               strftime('%m', published_date) as month,
               COUNT(*) as count
        FROM posts
        WHERE published_date IS NOT NULL
        GROUP BY year, month
        ORDER BY year DESC, month DESC
    """).fetchall()

    # Structure the data
    archive = defaultdict(list)
    month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']

    for row in posts_by_date:
        if row[0]:  # If year exists
            month_num = int(row[1]) if row[1] else 1
            archive[row[0]].append({
                'month': row[1],
                'name': month_names[month_num],
                'count': row[2]
            })

    # Convert to sorted list
    archive_list = []
    for year in sorted(archive.keys(), reverse=True):
        archive_list.append((year, archive[year]))

    return archive_list


@app.route('/api/search')
def search():
    """API endpoint for autocomplete search"""
    query = request.args.get('q', '').strip()

    if len(query) < 2:
        return jsonify({'results': []})

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    search_pattern = f'%{query}%'

    # Get top 10 matching posts
    sql = """
        SELECT p.post_id, p.title, p.author, p.published_date,
               SUBSTR(p.content_text, 1, 150) as snippet
        FROM posts p
        WHERE p.title LIKE ? OR p.content_text LIKE ? OR p.author LIKE ?
        ORDER BY
            CASE
                WHEN p.title LIKE ? THEN 1
                WHEN p.author LIKE ? THEN 2
                ELSE 3
            END,
            p.published_date DESC
        LIMIT 10
    """

    results = cur.execute(sql,
                          (search_pattern, search_pattern, search_pattern,
                           search_pattern, search_pattern)).fetchall()

    conn.close()

    search_results = []
    for row in results:
        snippet = row['snippet'] or ''
        if query.lower() in snippet.lower():
            # Center snippet around search term
            pos = snippet.lower().find(query.lower())
            start = max(0, pos - 30)
            end = min(len(snippet), pos + len(query) + 50)
            snippet = ('...' if start > 0 else '') + snippet[start:end] + ('...' if end < len(snippet) else '')

        search_results.append({
            'id': row['post_id'],
            'title': row['title'] or 'Untitled',
            'author': row['author'],
            'date': row['published_date'][:10] if row['published_date'] else None,
            'snippet': snippet
        })

    return jsonify({'results': search_results})

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    query = request.args.get('q', '').strip()
    selected_year = request.args.get('year', '').strip()
    selected_month = request.args.get('month', '').strip()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Build filter conditions
    conditions = []
    params = []

    if query:
        conditions.append("(title LIKE ? OR content_text LIKE ? OR author LIKE ?)")
        search_pattern = f'%{query}%'
        params.extend([search_pattern, search_pattern, search_pattern])

    if selected_year:
        if selected_month:
            conditions.append("strftime('%Y-%m', published_date) = ?")
            params.append(f"{selected_year}-{selected_month}")
        else:
            conditions.append("strftime('%Y', published_date) = ?")
            params.append(selected_year)


    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Get total count
    count_sql = f"SELECT COUNT(*) FROM posts WHERE {where_clause}"
    total_results = cur.execute(count_sql, params).fetchone()[0]

    # Get posts
    posts_sql = f"""
        SELECT p.post_id, p.title, p.author, p.url, p.published_date,
               SUBSTR(p.content_text, 1, 200) as excerpt,
               (SELECT COUNT(*) FROM media WHERE post_id = p.post_id) as media_count
        FROM posts p
        WHERE {where_clause}
        ORDER BY p.published_date DESC
        LIMIT ? OFFSET ?
    """
    params.extend([POSTS_PER_PAGE, (page - 1) * POSTS_PER_PAGE])
    posts_data = cur.execute(posts_sql, params).fetchall()

    # Get archive structure for sidebar
    archive_dates = get_archive_structure(conn)

    # Get total posts count
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

    # Build filter params for pagination links
    filter_params = []
    if query:
        filter_params.append(f"q={quote_plus(query)}")
    if selected_year:
        filter_params.append(f"year={selected_year}")
    if selected_month:
        filter_params.append(f"month={selected_month}")

    filter_params_str = "&" + "&".join(filter_params) if filter_params else ""

    # Get month name if selected
    month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    selected_month_name = month_names[int(selected_month)] if selected_month else ''

    return render_template_string(
        HTML_TEMPLATE,
        posts=posts,
        page=page,
        total_pages=total_pages,
        total_posts=total_posts,
        total_results=total_results,
        query=query,
        selected_year=selected_year,
        selected_month=selected_month,
        selected_month_name=selected_month_name,
        page_range=page_range,
        archive_dates=archive_dates,
        filter_params=filter_params_str,
        urlencode=quote_plus
    )

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
        paragraphs = content.split('\n\n')
        formatted_content = ''.join(f'<p>{p.replace(chr(10), "<br>")}</p>' for p in paragraphs if p.strip())
    else:
        formatted_content = None

    post = {
        'id': post_data['post_id'],
        'title': post_data['title'],
        'author': post_data['author'],
        'url': post_data['url'],
        'date': post_data['published_date'][:10] if post_data['published_date'] else None,
        'content': formatted_content
    }

    return render_template_string(POST_TEMPLATE, post=post)

GALLERY_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Image Gallery - WFMU Archive</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: Georgia, serif;
            background: #1a1a1a;
            color: #fff;
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
            margin-right: 20px;
        }

        .nav {
            display: inline;
        }

        .nav a {
            color: white;
            text-decoration: none;
            margin-right: 15px;
            font-size: 14px;
        }

        .nav a:hover {
            text-decoration: underline;
        }

        .filters {
            background: #2a2a2a;
            padding: 15px 20px;
            border-bottom: 1px solid #444;
        }

        .filters select {
            margin-right: 10px;
            padding: 5px 10px;
            background: #333;
            color: white;
            border: 1px solid #555;
            border-radius: 3px;
        }

        .stats {
            color: #ccc;
            font-size: 13px;
            margin-left: 20px;
            display: inline;
        }

        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 20px;
            padding: 20px;
            max-width: 1600px;
            margin: 0 auto;
        }

        .image-item {
            position: relative;
            background: #2a2a2a;
            border-radius: 8px;
            overflow: hidden;
            transition: transform 0.2s;
            cursor: pointer;
        }

        .image-item:hover {
            transform: scale(1.02);
            box-shadow: 0 4px 12px rgba(255, 102, 0, 0.3);
        }

        .image-item img {
            width: 100%;
            height: 200px;
            object-fit: cover;
            display: block;
        }

        .image-info {
            padding: 10px;
            background: rgba(0,0,0,0.7);
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            transform: translateY(100%);
            transition: transform 0.2s;
        }

        .image-item:hover .image-info {
            transform: translateY(0);
        }

        .image-info .post-title {
            font-size: 12px;
            color: #FF6600;
            margin-bottom: 3px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .image-info .post-date {
            font-size: 11px;
            color: #999;
        }

        .pagination {
            text-align: center;
            padding: 30px 20px;
            background: #2a2a2a;
            border-top: 1px solid #444;
        }

        .pagination a, .pagination span {
            display: inline-block;
            padding: 8px 12px;
            margin: 0 3px;
            background: #333;
            color: #fff;
            text-decoration: none;
            border-radius: 3px;
        }

        .pagination .current {
            background: #FF6600;
        }

        .pagination a:hover {
            background: #FF6600;
        }

        .no-images {
            text-align: center;
            padding: 100px 20px;
            color: #666;
        }

        .loading {
            display: none;
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #FF6600;
            font-size: 18px;
        }
    </style>
</head>
<body>
    <header>
        <h1>🎙️ WFMU Image Gallery</h1>
        <div class="nav">
            <a href="/">← Back to Archive</a>
        </div>
        <div class="stats">
            {{ total_images }} images {% if year_filter %}from {{ year_filter }}{% endif %}
        </div>
    </header>

    <div class="filters">
        <select id="yearFilter" onchange="filterImages()">
            <option value="">All Years</option>
            {% for year in years %}
            <option value="{{ year[0] }}" {% if year[0] == year_filter %}selected{% endif %}>
                {{ year[0] }} ({{ year[1] }} images)
            </option>
            {% endfor %}
        </select>

        <select id="monthFilter" onchange="filterImages()">
            <option value="">All Months</option>
            {% if year_filter %}
                {% for month in months %}
                <option value="{{ month[0] }}" {% if month[0] == month_filter %}selected{% endif %}>
                    {{ month[1] }} ({{ month[2] }} images)
                </option>
                {% endfor %}
            {% endif %}
        </select>
    </div>

    <div class="loading" id="loading">Loading images...</div>

    {% if images %}
    <div class="gallery">
        {% for image in images %}
        <div class="image-item" onclick="window.location.href='/post/{{ image.post_id }}'">
            <img src="/{{ image.local_path }}" alt="{{ image.alt_text or 'Image' }}"
                 onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\"http://www.w3.org/2000/svg\" width=\"200\" height=\"200\" viewBox=\"0 0 200 200\"%3E%3Crect fill=\"%23333\" width=\"200\" height=\"200\"/%3E%3Ctext fill=\"%23999\" font-size=\"14\" x=\"50%25\" y=\"50%25\" text-anchor=\"middle\" dy=\".3em\"%3EImage not found%3C/text%3E%3C/svg%3E'">
            <div class="image-info">
                <div class="post-title">{{ image.post_title or 'Untitled Post' }}</div>
                <div class="post-date">{{ image.post_date }}</div>
            </div>
        </div>
        {% endfor %}
    </div>

    {% if total_pages > 1 %}
    <div class="pagination">
        {% if page > 1 %}
        <a href="?page=1{{ filter_params }}">« First</a>
        <a href="?page={{ page - 1 }}{{ filter_params }}">‹ Previous</a>
        {% endif %}

        {% for p in page_range %}
            {% if p == page %}
            <span class="current">{{ p }}</span>
            {% else %}
            <a href="?page={{ p }}{{ filter_params }}">{{ p }}</a>
            {% endif %}
        {% endfor %}

        {% if page < total_pages %}
        <a href="?page={{ page + 1 }}{{ filter_params }}">Next ›</a>
        <a href="?page={{ total_pages }}{{ filter_params }}">Last »</a>
        {% endif %}
    </div>
    {% endif %}

    {% else %}
    <div class="no-images">
        <h2>No images found</h2>
        <p>{% if year_filter %}No images for this time period{% else %}No downloaded images in the archive{% endif %}</p>
    </div>
    {% endif %}

    <script>
        function filterImages() {
            const year = document.getElementById('yearFilter').value;
            const month = document.getElementById('monthFilter').value;

            let url = '/gallery?';
            if (year) url += 'year=' + year;
            if (month) url += '&month=' + month;

            document.getElementById('loading').style.display = 'block';
            window.location.href = url;
        }
    </script>
</body>
</html>
'''

@app.route('/media/images/<path:filename>')
def serve_image(filename):
    """Serve images from the media directory"""
    return send_from_directory('media/images', filename)

@app.route('/gallery')
def gallery():
    """Image gallery view"""
    page = request.args.get('page', 1, type=int)
    year_filter = request.args.get('year', '')
    month_filter = request.args.get('month', '')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Build query conditions
    conditions = ["m.downloaded = 1", "m.media_type = 'image'"]
    params = []

    if year_filter:
        if month_filter:
            conditions.append("strftime('%Y-%m', p.published_date) = ?")
            params.append(f"{year_filter}-{int(month_filter):02d}")
        else:
            conditions.append("strftime('%Y', p.published_date) = ?")
            params.append(year_filter)

    where_clause = " AND ".join(conditions)

    # Get total count
    count_sql = f"""
        SELECT COUNT(*)
        FROM media m
        JOIN posts p ON m.post_id = p.post_id
        WHERE {where_clause}
    """
    total_images = cur.execute(count_sql, params).fetchone()[0]

    # Get images with pagination
    images_per_page = 48
    images_sql = f"""
        SELECT m.id, m.post_id, m.local_path, m.alt_text, m.caption,
               p.title as post_title, p.published_date,
               strftime('%Y-%m-%d', p.published_date) as post_date
        FROM media m
        JOIN posts p ON m.post_id = p.post_id
        WHERE {where_clause}
        ORDER BY p.published_date DESC, m.id DESC
        LIMIT ? OFFSET ?
    """
    params.extend([images_per_page, (page - 1) * images_per_page])

    images = []
    for row in cur.execute(images_sql, params):
        images.append({
            'id': row['id'],
            'post_id': row['post_id'],
            'local_path': row['local_path'],
            'alt_text': row['alt_text'],
            'caption': row['caption'],
            'post_title': row['post_title'],
            'post_date': row['post_date']
        })

    # Get available years for filter
    years = cur.execute("""
        SELECT strftime('%Y', p.published_date) as year, COUNT(*) as count
        FROM media m
        JOIN posts p ON m.post_id = p.post_id
        WHERE m.downloaded = 1 AND m.media_type = 'image'
            AND p.published_date IS NOT NULL
        GROUP BY year
        ORDER BY year DESC
    """).fetchall()

    # Get months for selected year
    months = []
    if year_filter:
        month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        months_data = cur.execute("""
            SELECT strftime('%m', p.published_date) as month, COUNT(*) as count
            FROM media m
            JOIN posts p ON m.post_id = p.post_id
            WHERE m.downloaded = 1 AND m.media_type = 'image'
                AND strftime('%Y', p.published_date) = ?
            GROUP BY month
            ORDER BY month DESC
        """, (year_filter,)).fetchall()

        months = [(int(m[0]), month_names[int(m[0])], m[1]) for m in months_data]

    conn.close()

    # Pagination
    total_pages = math.ceil(total_images / images_per_page)
    page_range = get_page_range(page, total_pages)

    # Build filter params for pagination
    filter_params = []
    if year_filter:
        filter_params.append(f"&year={year_filter}")
    if month_filter:
        filter_params.append(f"&month={month_filter}")
    filter_params_str = "".join(filter_params)

    return render_template_string(
        GALLERY_TEMPLATE,
        images=images,
        page=page,
        total_pages=total_pages,
        total_images=total_images,
        page_range=page_range,
        years=years,
        months=months,
        year_filter=year_filter,
        month_filter=month_filter,
        filter_params=filter_params_str
    )

@app.route('/post/<post_id>/original')
def view_post_original(post_id):
    """Serve the original HTML exactly as it was on the blog"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get the raw HTML from the database
    post_data = cur.execute("""
        SELECT raw_html, title, url
        FROM posts
        WHERE post_id = ?
    """, (post_id,)).fetchone()

    conn.close()

    if not post_data:
        return "Post not found", 404

    raw_html = post_data['raw_html']

    # Create a full HTML page that preserves the original styling
    # We'll inject the WFMU blog's original CSS and wrap the content
    original_html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{post_data['title'] or 'WFMU Blog Post'} - Original View</title>
    <base href="https://blog.wfmu.org/">

    <!-- Original WFMU Blog Styles -->
    <link rel="stylesheet" type="text/css" href="https://web.archive.org/web/20150101/http://blog.wfmu.org/styles-site.css">

    <style>
        /* Additional wrapper to ensure proper display */
        body {{
            margin: 0;
            padding: 20px;
            background: #fff;
            font-family: Georgia, serif;
        }}

        /* Override any problematic styles */
        .original-content {{
            max-width: 800px;
            margin: 0 auto;
        }}

        /* Navigation bar */
        .archive-nav {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: #FF6600;
            color: white;
            padding: 10px 20px;
            z-index: 10000;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            font-family: Arial, sans-serif;
        }}

        .archive-nav a {{
            color: white;
            text-decoration: none;
            margin-right: 20px;
        }}

        .archive-nav a:hover {{
            text-decoration: underline;
        }}

        /* Push content down to account for fixed nav */
        body {{
            padding-top: 60px;
        }}

        /* Fix any broken image links to use Archive.org */
        img {{
            max-width: 100%;
            height: auto;
        }}
    </style>

    <script>
        // Redirect broken images to Archive.org
        document.addEventListener('DOMContentLoaded', function() {{
            var images = document.getElementsByTagName('img');
            for (var i = 0; i < images.length; i++) {{
                images[i].onerror = function() {{
                    // Try Archive.org version
                    if (!this.src.includes('web.archive.org')) {{
                        var archiveUrl = 'https://web.archive.org/web/2015/' + this.src.replace(/^https?:\\/\\//, '');
                        this.src = archiveUrl;
                    }}
                }};
            }}

            // Fix links to point to Archive.org
            var links = document.getElementsByTagName('a');
            for (var i = 0; i < links.length; i++) {{
                var href = links[i].href;
                if (href && href.includes('blog.wfmu.org') && !href.includes('web.archive.org')) {{
                    links[i].href = 'https://web.archive.org/web/2015/' + href.replace(/^https?:\\/\\//, '');
                    links[i].target = '_blank';
                }}
            }}
        }});
    </script>
</head>
<body>
    <div class="archive-nav">
        <a href="/post/{post_id}">← Back to Archive View</a>
        <a href="/">Browse Archive</a>
        <span style="float: right; font-size: 12px;">
            Original from: <a href="https://web.archive.org/web/{post_data['url']}" target="_blank" style="text-decoration: underline;">
                {post_data['url'].replace('https://blog.wfmu.org/', '')}
            </a>
        </span>
    </div>

    <div class="original-content">
        {raw_html}
    </div>
</body>
</html>'''

    return original_html

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎙️  WFMU BLOG ARCHIVE VIEWER - ENHANCED")
    print("="*60)
    print("\nFeatures:")
    print("  ✓ Live autocomplete search")
    print("  ✓ Browse by Year/Month")
    print("  ✓ Combined filtering")
    print("  ✓ Pagination (50 posts per page)")
    print("  ✓ Image gallery at /gallery")
    print("\nURLs:")
    print("  Archive: http://localhost:8080")
    print("  Gallery: http://localhost:8080/gallery")
    print("\nUsing database: wfmu_archive_viewer.db")
    print("="*60 + "\n")

    app.run(port=8080, debug=False)
