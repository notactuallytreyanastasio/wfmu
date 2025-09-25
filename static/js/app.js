// WFMU Blog Archive Viewer - Main JavaScript

let currentPage = 1;
let currentView = 'cards';
let searchTimeout = null;
let isSearching = false;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadPosts(1);
    setupSearch();
    setupViewToggle();
    setupModal();
});

// Load archive statistics
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();

        const statsEl = document.getElementById('stats');
        if (stats.date_range.start && stats.date_range.end) {
            const startDate = new Date(stats.date_range.start).getFullYear();
            const endDate = new Date(stats.date_range.end).getFullYear();

            statsEl.innerHTML = `
                <span>📚 ${stats.total_posts} posts</span>
                <span>🎵 ${stats.total_media} media files</span>
                <span>✍️ ${stats.total_authors} authors</span>
                <span>📅 ${startDate}-${endDate}</span>
            `;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load posts with pagination
async function loadPosts(page, query = '') {
    currentPage = page;
    const container = document.getElementById('posts-container');
    container.innerHTML = '<div class="loading">Loading posts...</div>';

    try {
        const url = `/api/posts?page=${page}${query ? '&q=' + encodeURIComponent(query) : ''}`;
        const response = await fetch(url);
        const data = await response.json();

        renderPosts(data.posts);
        renderPagination(data.page, data.pages);
    } catch (error) {
        console.error('Error loading posts:', error);
        container.innerHTML = '<div class="error">Error loading posts. Please try again.</div>';
    }
}

// Render posts based on current view
function renderPosts(posts) {
    const container = document.getElementById('posts-container');

    if (posts.length === 0) {
        container.innerHTML = '<div class="no-results">No posts found.</div>';
        return;
    }

    container.className = `posts-${currentView}`;

    if (currentView === 'timeline') {
        renderTimelineView(posts);
    } else {
        container.innerHTML = posts.map(post => createPostCard(post)).join('');
    }

    // Add click handlers to post cards
    container.querySelectorAll('.post-card').forEach(card => {
        card.addEventListener('click', (e) => {
            if (!e.target.closest('a')) {
                window.location.href = `/post/${card.dataset.postId}`;
            }
        });
    });
}

// Create a post card HTML
function createPostCard(post) {
    const date = post.date ? new Date(post.date).toLocaleDateString() : 'Unknown date';
    const excerpt = post.excerpt || 'No preview available';

    return `
        <div class="post-card" data-post-id="${post.id}">
            <h3>${post.title}</h3>
            <div class="meta">
                ${post.author ? `<span>👤 ${post.author}</span>` : ''}
                <span>📅 ${date}</span>
                ${post.media_count > 0 ? `<span>📎 ${post.media_count} media</span>` : ''}
            </div>
            <div class="excerpt">${excerpt}...</div>
            <div class="actions">
                <a href="/post/${post.id}" class="action-btn">Read More</a>
                ${post.has_original ? `<a href="/post/${post.id}/original" class="action-btn">Original</a>` : ''}
            </div>
        </div>
    `;
}

// Render timeline view
function renderTimelineView(posts) {
    const container = document.getElementById('posts-container');
    const grouped = {};

    // Group posts by month/year
    posts.forEach(post => {
        const date = post.date ? new Date(post.date) : null;
        const key = date ? `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}` : 'Unknown';

        if (!grouped[key]) {
            grouped[key] = [];
        }
        grouped[key].push(post);
    });

    // Render grouped posts
    let html = '<div class="posts-timeline">';
    Object.keys(grouped).sort().reverse().forEach(key => {
        const [year, month] = key.split('-');
        const monthName = month ? new Date(year, month - 1).toLocaleDateString('en', { month: 'long', year: 'numeric' }) : key;

        html += `
            <div class="timeline-group">
                <div class="timeline-date">${monthName}</div>
                ${grouped[key].map(post => createPostCard(post)).join('')}
            </div>
        `;
    });
    html += '</div>';

    container.innerHTML = html;
}

// Render pagination controls
function renderPagination(current, total) {
    const pagination = document.getElementById('pagination');

    if (total <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = '';

    // Previous button
    if (current > 1) {
        html += `<button onclick="loadPosts(${current - 1})">← Previous</button>`;
    }

    // Page numbers (show max 5 pages)
    const startPage = Math.max(1, current - 2);
    const endPage = Math.min(total, startPage + 4);

    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="${i === current ? 'active' : ''}" onclick="loadPosts(${i})">${i}</button>`;
    }

    // Next button
    if (current < total) {
        html += `<button onclick="loadPosts(${current + 1})">Next →</button>`;
    }

    pagination.innerHTML = html;
}

// Setup live search functionality
function setupSearch() {
    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();

        // Clear timeout if user is still typing
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }

        if (query.length < 2) {
            searchResults.classList.remove('active');
            searchResults.innerHTML = '';
            if (!isSearching) {
                loadPosts(1); // Load default posts
            }
            isSearching = false;
            return;
        }

        // Debounce search
        searchTimeout = setTimeout(async () => {
            isSearching = true;
            await performSearch(query);
        }, 300);
    });

    // Handle Enter key
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const query = e.target.value.trim();
            if (query) {
                searchResults.classList.remove('active');
                loadPosts(1, query);
            }
        }
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-container')) {
            searchResults.classList.remove('active');
        }
    });
}

// Perform live search
async function performSearch(query) {
    const searchResults = document.getElementById('search-results');

    try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data.results.length === 0) {
            searchResults.innerHTML = '<div class="no-results">No results found</div>';
        } else {
            searchResults.innerHTML = data.results.map(result => `
                <div class="search-result" onclick="window.location.href='/post/${result.id}'">
                    <h4>${highlightMatch(result.title, query)}</h4>
                    <div class="meta">
                        ${result.author ? `By ${result.author} • ` : ''}
                        ${result.date ? new Date(result.date).toLocaleDateString() : ''}
                    </div>
                    <div class="snippet">${highlightMatch(result.snippet, query)}</div>
                </div>
            `).join('');
        }

        searchResults.classList.add('active');
    } catch (error) {
        console.error('Search error:', error);
    }
}

// Highlight search matches
function highlightMatch(text, query) {
    if (!text) return '';
    const regex = new RegExp(`(${query})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
}

// Setup view toggle buttons
function setupViewToggle() {
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            currentView = view;

            // Update active button
            document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Reload posts with new view
            loadPosts(currentPage);
        });
    });
}

// Setup modal for about/info
function setupModal() {
    const modal = document.getElementById('post-modal');
    const closeBtn = modal.querySelector('.close');
    const aboutLink = document.getElementById('about-link');

    if (aboutLink) {
        aboutLink.addEventListener('click', (e) => {
            e.preventDefault();
            showAboutModal();
        });
    }

    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
}

// Show about modal
function showAboutModal() {
    const modal = document.getElementById('post-modal');
    const modalBody = document.getElementById('modal-body');

    modalBody.innerHTML = `
        <h2>About the WFMU Blog Archive</h2>
        <p>This archive preserves the complete history of WFMU's Beware of the Blog,
        which was active from 2003 to 2015. The blog was a pioneering music blog that
        featured rare recordings, obscure music, and fascinating commentary from the
        freeform radio station's DJs and contributors.</p>

        <h3>Features</h3>
        <ul>
            <li><strong>Complete Archive:</strong> All posts, comments, and media preserved</li>
            <li><strong>Dual View:</strong> See posts in modern format or original HTML</li>
            <li><strong>Live Search:</strong> Find posts instantly as you type</li>
            <li><strong>Media Preservation:</strong> Images and MP3s archived locally</li>
        </ul>

        <h3>Navigation Tips</h3>
        <ul>
            <li>Use the search bar to find specific content</li>
            <li>Switch between Card, List, and Timeline views</li>
            <li>Click "Original" to see the post as it appeared on the blog</li>
            <li>Media files are preserved and playable directly</li>
        </ul>

        <p><em>Archived with love for the WFMU community ❤️</em></p>
    `;

    modal.style.display = 'block';
}