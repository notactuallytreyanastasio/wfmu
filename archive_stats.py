#!/usr/bin/env python3
"""
WFMU Archive Statistics and Analytics Page
Provides insights and visualizations of the archived blog data
"""

from flask import Flask, render_template_string, jsonify
import sqlite3
from collections import defaultdict, Counter
from datetime import datetime
import json

app = Flask(__name__)
DB_PATH = 'wfmu_archive_viewer.db'

STATS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>WFMU Archive Statistics</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: Georgia, serif;
            background: #f5f5f5;
            color: #333;
            padding: 20px;
        }

        header {
            background: #FF6600;
            color: white;
            padding: 20px;
            margin: -20px -20px 20px -20px;
            border-bottom: 3px solid #333;
        }

        h1 {
            font-size: 24px;
            margin-bottom: 5px;
        }

        .subtitle {
            font-size: 14px;
            opacity: 0.9;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .stat-card h2 {
            color: #FF6600;
            font-size: 16px;
            margin-bottom: 15px;
            border-bottom: 1px solid #f0f0f0;
            padding-bottom: 8px;
        }

        .big-number {
            font-size: 36px;
            font-weight: bold;
            color: #0066CC;
            margin-bottom: 5px;
        }

        .stat-label {
            color: #666;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .stat-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #f9f9f9;
        }

        .stat-row:last-child {
            border-bottom: none;
        }

        .stat-name {
            font-size: 13px;
            color: #333;
        }

        .stat-value {
            font-size: 13px;
            color: #0066CC;
            font-weight: bold;
        }

        .chart-container {
            background: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 20px;
            margin-bottom: 20px;
        }

        .chart-container h2 {
            color: #FF6600;
            font-size: 18px;
            margin-bottom: 15px;
        }

        .bar-chart {
            display: flex;
            align-items: flex-end;
            height: 200px;
            gap: 2px;
            margin-bottom: 10px;
            border-bottom: 1px solid #ddd;
        }

        .bar {
            flex: 1;
            background: #0066CC;
            min-height: 5px;
            position: relative;
            transition: background 0.2s;
        }

        .bar:hover {
            background: #FF6600;
        }

        .bar-label {
            position: absolute;
            bottom: -20px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 10px;
            white-space: nowrap;
        }

        .bar-value {
            position: absolute;
            top: -20px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 10px;
            font-weight: bold;
        }

        .top-list {
            list-style: none;
        }

        .top-list li {
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
            display: flex;
            justify-content: space-between;
            font-size: 13px;
        }

        .top-list .rank {
            color: #FF6600;
            font-weight: bold;
            margin-right: 10px;
        }

        .top-list .count {
            color: #999;
            font-size: 12px;
        }

        .timeline {
            background: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 20px;
            margin-bottom: 20px;
        }

        .timeline h2 {
            color: #FF6600;
            font-size: 18px;
            margin-bottom: 15px;
        }

        .year-bars {
            display: flex;
            gap: 5px;
            align-items: flex-end;
            height: 150px;
            margin-bottom: 10px;
        }

        .year-bar {
            flex: 1;
            background: linear-gradient(to top, #0066CC, #4d94ff);
            position: relative;
            min-height: 10px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .year-bar:hover {
            background: linear-gradient(to top, #FF6600, #ff8533);
            transform: scale(1.05);
        }

        .year-label {
            position: absolute;
            bottom: -25px;
            left: 50%;
            transform: translateX(-50%) rotate(-45deg);
            font-size: 11px;
            transform-origin: center;
        }

        .year-count {
            position: absolute;
            top: -20px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 10px;
            font-weight: bold;
            color: #666;
        }

        .insights {
            background: #fffbf0;
            border: 1px solid #FFCC00;
            border-radius: 5px;
            padding: 20px;
            margin-bottom: 20px;
        }

        .insights h2 {
            color: #FF6600;
            font-size: 18px;
            margin-bottom: 15px;
        }

        .insight {
            padding: 10px 0;
            border-bottom: 1px solid #ffe680;
            font-size: 14px;
        }

        .insight:last-child {
            border-bottom: none;
        }

        .insight strong {
            color: #FF6600;
        }

        .media-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }

        .media-type {
            background: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            text-align: center;
        }

        .media-type .icon {
            font-size: 24px;
            margin-bottom: 5px;
        }

        .media-type .count {
            font-size: 20px;
            font-weight: bold;
            color: #0066CC;
        }

        .media-type .label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }

        .nav-link {
            display: inline-block;
            margin-top: 20px;
            padding: 10px 20px;
            background: #0066CC;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: background 0.2s;
        }

        .nav-link:hover {
            background: #FF6600;
        }
    </style>
</head>
<body>
    <header>
        <h1>📊 WFMU Archive Statistics</h1>
        <div class="subtitle">Comprehensive analysis of {{ total_posts }} archived posts</div>
    </header>

    <div class="container">
        <!-- Overview Stats -->
        <div class="stats-grid">
            <div class="stat-card">
                <h2>📝 Posts</h2>
                <div class="big-number">{{ total_posts | format_number }}</div>
                <div class="stat-label">Total Articles Archived</div>
                <div style="margin-top: 15px;">
                    <div class="stat-row">
                        <span class="stat-name">Date Range</span>
                        <span class="stat-value">{{ date_range }}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-name">Years Covered</span>
                        <span class="stat-value">{{ years_count }}</span>
                    </div>
                </div>
            </div>

            <div class="stat-card">
                <h2>✍️ Authors</h2>
                <div class="big-number">{{ total_authors }}</div>
                <div class="stat-label">Contributing Writers</div>
                <div style="margin-top: 15px;">
                    <div class="stat-row">
                        <span class="stat-name">Most Prolific</span>
                        <span class="stat-value">{{ top_author.name }}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-name">Their Posts</span>
                        <span class="stat-value">{{ top_author.count }}</span>
                    </div>
                </div>
            </div>

            <div class="stat-card">
                <h2>💬 Comments</h2>
                <div class="big-number">{{ total_comments | format_number }}</div>
                <div class="stat-label">User Interactions</div>
                <div style="margin-top: 15px;">
                    <div class="stat-row">
                        <span class="stat-name">Avg per Post</span>
                        <span class="stat-value">{{ avg_comments }}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-name">Most Discussed</span>
                        <span class="stat-value">{{ most_commented_count }} comments</span>
                    </div>
                </div>
            </div>

            <div class="stat-card">
                <h2>📎 Media Files</h2>
                <div class="big-number">{{ total_media | format_number }}</div>
                <div class="stat-label">Images & Audio</div>
                <div class="media-stats">
                    <div class="media-type">
                        <div class="icon">🖼️</div>
                        <div class="count">{{ image_count | format_number }}</div>
                        <div class="label">Images</div>
                    </div>
                    <div class="media-type">
                        <div class="icon">🎵</div>
                        <div class="count">{{ audio_count | format_number }}</div>
                        <div class="label">Audio</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Timeline -->
        <div class="timeline">
            <h2>📅 Posts Over Time</h2>
            <div class="year-bars">
                {% for year_data in yearly_stats %}
                <div class="year-bar" style="height: {{ year_data.height }}%;" title="{{ year_data.year }}: {{ year_data.count }} posts">
                    <span class="year-count">{{ year_data.count }}</span>
                    <span class="year-label">{{ year_data.year }}</span>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- Top Authors -->
        <div class="stats-grid">
            <div class="stat-card">
                <h2>🏆 Top 10 Authors by Post Count</h2>
                <ul class="top-list">
                    {% for author in top_authors %}
                    <li>
                        <span>
                            <span class="rank">#{{ loop.index }}</span>
                            {{ author.name }}
                        </span>
                        <span class="count">{{ author.count }} posts</span>
                    </li>
                    {% endfor %}
                </ul>
            </div>

            <div class="stat-card">
                <h2>💭 Most Commented Posts</h2>
                <ul class="top-list">
                    {% for post in most_commented %}
                    <li>
                        <span title="{{ post.title }}">
                            {{ post.title[:50] }}{% if post.title|length > 50 %}...{% endif %}
                        </span>
                        <span class="count">{{ post.comments }} comments</span>
                    </li>
                    {% endfor %}
                </ul>
            </div>

            <div class="stat-card">
                <h2>🎯 Most Active Months</h2>
                <ul class="top-list">
                    {% for month in busiest_months %}
                    <li>
                        <span>{{ month.name }}</span>
                        <span class="count">{{ month.count }} posts</span>
                    </li>
                    {% endfor %}
                </ul>
            </div>
        </div>

        <!-- Insights -->
        <div class="insights">
            <h2>🔍 Key Insights</h2>
            <div class="insight">
                <strong>Peak Activity:</strong> The most active year was {{ peak_year }} with {{ peak_year_count }} posts
            </div>
            <div class="insight">
                <strong>Average Posts:</strong> {{ avg_posts_per_month }} posts per month across the entire archive
            </div>
            <div class="insight">
                <strong>Content Richness:</strong> {{ posts_with_media }}% of posts include media files
            </div>
            <div class="insight">
                <strong>Community Engagement:</strong> {{ posts_with_comments }}% of posts have comments
            </div>
            <div class="insight">
                <strong>Archive Span:</strong> {{ archive_days }} days of blog history preserved
            </div>
        </div>

        <a href="/" class="nav-link">← Back to Archive Browser</a>
    </div>

    <script>
        // Add interactivity to year bars
        document.querySelectorAll('.year-bar').forEach(bar => {
            bar.addEventListener('click', function() {
                const year = this.getAttribute('title').split(':')[0];
                window.location.href = '/?year=' + year;
            });
        });
    </script>
</body>
</html>
'''

def format_number(value):
    """Format number with commas"""
    return f"{value:,}"

# Register filter
app.jinja_env.filters['format_number'] = format_number

@app.route('/')
def stats():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Basic counts
    total_posts = cur.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    total_authors = cur.execute("SELECT COUNT(DISTINCT author) FROM posts WHERE author IS NOT NULL").fetchone()[0]
    total_comments = cur.execute("SELECT COUNT(*) FROM comments").fetchone()[0] if cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='comments'").fetchone() else 0
    total_media = cur.execute("SELECT COUNT(*) FROM media").fetchone()[0]

    # Media breakdown
    media_types = dict(cur.execute("SELECT media_type, COUNT(*) FROM media GROUP BY media_type").fetchall())
    image_count = media_types.get('image', 0)
    audio_count = media_types.get('audio', 0)

    # Date range
    date_range_data = cur.execute("""
        SELECT MIN(published_date), MAX(published_date)
        FROM posts
        WHERE published_date IS NOT NULL
    """).fetchone()

    if date_range_data[0] and date_range_data[1]:
        start_date = datetime.fromisoformat(date_range_data[0])
        end_date = datetime.fromisoformat(date_range_data[1])
        date_range = f"{start_date.strftime('%B %Y')} - {end_date.strftime('%B %Y')}"
        archive_days = (end_date - start_date).days
    else:
        date_range = "Unknown"
        archive_days = 0

    # Top authors
    top_authors = []
    for row in cur.execute("""
        SELECT author, COUNT(*) as count
        FROM posts
        WHERE author IS NOT NULL
        GROUP BY author
        ORDER BY count DESC
        LIMIT 10
    """).fetchall():
        top_authors.append({'name': row[0], 'count': row[1]})

    top_author = top_authors[0] if top_authors else {'name': 'Unknown', 'count': 0}

    # Yearly statistics
    yearly_data = cur.execute("""
        SELECT strftime('%Y', published_date) as year, COUNT(*) as count
        FROM posts
        WHERE published_date IS NOT NULL
        GROUP BY year
        ORDER BY year
    """).fetchall()

    yearly_stats = []
    max_year_count = max(y[1] for y in yearly_data) if yearly_data else 1

    for year, count in yearly_data:
        yearly_stats.append({
            'year': year,
            'count': count,
            'height': (count / max_year_count) * 100
        })

    years_count = len(yearly_stats)

    # Peak year
    if yearly_data:
        peak_data = max(yearly_data, key=lambda x: x[1])
        peak_year = peak_data[0]
        peak_year_count = peak_data[1]
    else:
        peak_year = "Unknown"
        peak_year_count = 0

    # Most commented posts
    most_commented = []
    if total_comments > 0:
        for row in cur.execute("""
            SELECT p.title, COUNT(c.comment_id) as comment_count
            FROM posts p
            LEFT JOIN comments c ON p.post_id = c.post_id
            GROUP BY p.post_id
            ORDER BY comment_count DESC
            LIMIT 10
        """).fetchall():
            if row[1] > 0:
                most_commented.append({'title': row[0] or 'Untitled', 'comments': row[1]})

    most_commented_count = most_commented[0]['comments'] if most_commented else 0

    # Busiest months
    busiest_months = []
    for row in cur.execute("""
        SELECT strftime('%Y-%m', published_date) as month, COUNT(*) as count
        FROM posts
        WHERE published_date IS NOT NULL
        GROUP BY month
        ORDER BY count DESC
        LIMIT 10
    """).fetchall():
        if row[0]:
            date_obj = datetime.strptime(row[0], '%Y-%m')
            busiest_months.append({
                'name': date_obj.strftime('%B %Y'),
                'count': row[1]
            })

    # Calculate averages and percentages
    avg_comments = round(total_comments / total_posts, 1) if total_posts > 0 else 0
    avg_posts_per_month = round(total_posts / max(len(busiest_months), 1), 1)

    posts_with_media_count = cur.execute("""
        SELECT COUNT(DISTINCT post_id) FROM media
    """).fetchone()[0]
    posts_with_media = round((posts_with_media_count / total_posts) * 100, 1) if total_posts > 0 else 0

    posts_with_comments_count = cur.execute("""
        SELECT COUNT(DISTINCT post_id) FROM comments
    """).fetchone()[0] if total_comments > 0 else 0
    posts_with_comments = round((posts_with_comments_count / total_posts) * 100, 1) if total_posts > 0 else 0

    conn.close()

    return render_template_string(
        STATS_TEMPLATE,
        total_posts=total_posts,
        total_authors=total_authors,
        total_comments=total_comments,
        total_media=total_media,
        image_count=image_count,
        audio_count=audio_count,
        date_range=date_range,
        archive_days=archive_days,
        years_count=years_count,
        top_author=top_author,
        top_authors=top_authors,
        yearly_stats=yearly_stats,
        peak_year=peak_year,
        peak_year_count=peak_year_count,
        most_commented=most_commented,
        most_commented_count=most_commented_count,
        busiest_months=busiest_months,
        avg_comments=avg_comments,
        avg_posts_per_month=avg_posts_per_month,
        posts_with_media=posts_with_media,
        posts_with_comments=posts_with_comments
    )

if __name__ == '__main__':
    print("\n" + "="*60)
    print("📊 WFMU ARCHIVE STATISTICS DASHBOARD")
    print("="*60)
    print("\nProvides comprehensive analytics of the archived blog")
    print("\nOpen: http://localhost:8085")
    print("="*60 + "\n")

    app.run(port=8085, debug=False)