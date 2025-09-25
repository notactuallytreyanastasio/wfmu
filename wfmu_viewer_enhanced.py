#!/usr/bin/env python3
"""
WFMU Archive Viewer - Enhanced with Sidebar Browsing
Features: Autocomplete search, year/month browsing, author selection
"""

from flask import Flask, render_template_string, request, jsonify
import sqlite3
import math
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
                <input type="hidden" name="author" value="{{ selected_author }}">
                <button type="submit">Search</button>
                {% if query or selected_year or selected_author %}
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

            <!-- Browse by Author -->
            <div class="sidebar-section">
                <h3>✍️ Browse by Author</h3>
                <div class="content author-list">
                    {% for author in authors %}
                    <a href="/?author={{ author.name | urlencode }}"
                       class="author-link {% if author.name == selected_author %}active{% endif %}">
                        {{ author.name }}
                        <span class="author-count">{{ author.count }}</span>
                    </a>
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
                {% if selected_author %} • <strong>Author: {{ selected_author }}</strong>{% endif %}
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
                {% if query or selected_year or selected_author %}
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

def get_authors_list(conn):
    """Get list of authors with post counts"""
    cur = conn.cursor()

    authors = cur.execute("""
        SELECT author, COUNT(*) as count
        FROM posts
        WHERE author IS NOT NULL AND author != ''
        GROUP BY author
        ORDER BY count DESC, author
    """).fetchall()

    return [{'name': author[0], 'count': author[1]} for author in authors]

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
    selected_author = request.args.get('author', '').strip()

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

    if selected_author:
        conditions.append("author = ?")
        params.append(selected_author)

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

    # Get archive structure and authors for sidebar
    archive_dates = get_archive_structure(conn)
    authors = get_authors_list(conn)

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
    if selected_author:
        filter_params.append(f"author={quote_plus(selected_author)}")

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
        selected_author=selected_author,
        page_range=page_range,
        archive_dates=archive_dates,
        authors=authors,
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
        'title': post_data['title'],
        'author': post_data['author'],
        'url': post_data['url'],
        'date': post_data['published_date'][:10] if post_data['published_date'] else None,
        'content': formatted_content
    }

    return render_template_string(POST_TEMPLATE, post=post)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎙️  WFMU BLOG ARCHIVE VIEWER - ENHANCED")
    print("="*60)
    print("\nFeatures:")
    print("  ✓ Live autocomplete search")
    print("  ✓ Browse by Year/Month")
    print("  ✓ Browse by Author")
    print("  ✓ Combined filtering")
    print("  ✓ Pagination (50 posts per page)")
    print("\nOpen: http://localhost:8080")
    print("\nUsing database: wfmu_archive_viewer.db")
    print("="*60 + "\n")

    app.run(port=8080, debug=False)
