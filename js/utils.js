/**
 * UTILITY FUNCTIONS
 * Data loading and helper functions
 */

// Data cache
const DataCache = {
    articles: null,
    timeline: null,
    textAnalysis: null
};

/**
 * Load JSON data file
 */
async function loadJSON(path) {
    try {
        const response = await fetch(path);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Error loading ${path}:`, error);
        return null;
    }
}

/**
 * Load all data files
 */
async function loadAllData() {
    const [articles, timeline, textAnalysis] = await Promise.all([
        loadJSON('data/processed/tagged_articles.json'),
        loadJSON('data/processed/timeline.json'),
        loadJSON('data/processed/text_analysis.json')
    ]);

    DataCache.articles = articles;
    DataCache.timeline = timeline;
    DataCache.textAnalysis = textAnalysis;

    return {
        articles,
        timeline,
        textAnalysis
    };
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    if (!dateString) return 'Date unknown';

    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    } catch {
        return dateString;
    }
}

/**
 * Parse date from string
 */
function parseDate(dateString) {
    if (!dateString) return null;
    try {
        return new Date(dateString);
    } catch {
        return null;
    }
}

/**
 * Truncate text to specified length
 */
function truncate(text, maxLength = 150) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength).trim() + '...';
}

/**
 * Debounce function for performance
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Show modal with content
 */
function showModal(content) {
    const modal = document.getElementById('article-modal');
    const modalBody = document.getElementById('modal-body');

    modalBody.innerHTML = content;
    modal.classList.add('active');

    // Close on click outside
    modal.onclick = (e) => {
        if (e.target === modal) {
            closeModal();
        }
    };

    // Close button
    const closeBtn = modal.querySelector('.modal-close');
    if (closeBtn) {
        closeBtn.onclick = closeModal;
    }

    // Close on escape key
    document.addEventListener('keydown', handleEscapeKey);
}

/**
 * Close modal
 */
function closeModal() {
    const modal = document.getElementById('article-modal');
    modal.classList.remove('active');
    document.removeEventListener('keydown', handleEscapeKey);
}

/**
 * Handle escape key to close modal
 */
function handleEscapeKey(e) {
    if (e.key === 'Escape') {
        closeModal();
    }
}

/**
 * Render article in modal
 */
function renderArticleModal(article) {
    const tags = article.tags.map(t =>
        `<span class="tag ${t.tag}">${t.tag.replace(/_/g, ' ')}</span>`
    ).join('');

    const content = `
        <div class="article-full">
            <h2 class="article-headline">
                ${article.headline || 'Article from The Equity'}
            </h2>
            <div class="article-meta">
                <strong>Source:</strong> ${article.source_pdf || 'Unknown'} |
                <strong>Page:</strong> ${article.page_number || 'Unknown'} |
                <strong>Date:</strong> ${article.extracted_date || 'Unknown'}
            </div>
            <div class="article-text">
                ${article.full_text}
            </div>
            <div class="article-tags">
                <strong>Tags:</strong> ${tags}
            </div>
        </div>
    `;

    showModal(content);
}

/**
 * Get color for tag type
 */
function getTagColor(tag) {
    const colors = {
        'whitechapel_ripper': '#8b0000',
        'crime_general': '#8b4513',
        'british_empire': '#191970',
        'local_shawville': '#228b22',
        'canadian': '#dc143c',
        'international': '#4b0082',
        'advertisement': '#808080',
        'social_cultural': '#2f4f4f'
    };
    return colors[tag] || '#6b6b6b';
}

/**
 * Check if element is in viewport
 */
function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

/**
 * Animate number counting
 */
function animateNumber(element, start, end, duration = 1000) {
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;

    const timer = setInterval(() => {
        current += increment;
        if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
            current = end;
            clearInterval(timer);
        }
        element.textContent = Math.round(current);
    }, 16);
}

/**
 * Create tooltip element
 */
function createTooltip(className = 'chart-tooltip') {
    let tooltip = document.querySelector(`.${className}`);

    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.className = className;
        document.body.appendChild(tooltip);
    }

    return {
        show: (content, x, y) => {
            tooltip.innerHTML = content;
            tooltip.classList.add('visible');
            tooltip.style.left = `${x + 10}px`;
            tooltip.style.top = `${y - 10}px`;
        },
        hide: () => {
            tooltip.classList.remove('visible');
        }
    };
}

// Export for use in other files
window.Utils = {
    loadJSON,
    loadAllData,
    formatDate,
    parseDate,
    truncate,
    debounce,
    showModal,
    closeModal,
    renderArticleModal,
    getTagColor,
    isInViewport,
    animateNumber,
    createTooltip,
    DataCache
};
