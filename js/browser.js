/**
 * ARTICLE BROWSER
 * Search and filter functionality for the archive
 */

class ArticleBrowser {
    constructor(articles) {
        this.allArticles = articles || [];
        this.filteredArticles = [...this.allArticles];
        this.activeFilters = new Set();

        this.searchInput = document.getElementById('search-input');
        this.filterTags = document.getElementById('filter-tags');
        this.articleGrid = document.getElementById('article-grid');

        this.init();
    }

    init() {
        if (this.allArticles.length === 0) {
            this.articleGrid.innerHTML = '<p class="empty-state">No articles available. Please run the data processing pipeline.</p>';
            return;
        }

        this.setupFilters();
        this.setupSearch();
        this.render();
    }

    setupFilters() {
        // Get unique tags
        const allTags = new Set();
        this.allArticles.forEach(article => {
            article.tags.forEach(tagObj => {
                allTags.add(tagObj.tag);
            });
        });

        const tags = Array.from(allTags).sort();

        // Create filter buttons
        this.filterTags.innerHTML = tags.map(tag => `
            <button class="filter-tag" data-tag="${tag}">
                ${tag.replace(/_/g, ' ')}
            </button>
        `).join('');

        // Add click handlers
        this.filterTags.querySelectorAll('.filter-tag').forEach(btn => {
            btn.addEventListener('click', () => {
                const tag = btn.dataset.tag;

                if (this.activeFilters.has(tag)) {
                    this.activeFilters.delete(tag);
                    btn.classList.remove('active');
                } else {
                    this.activeFilters.add(tag);
                    btn.classList.add('active');
                }

                this.filter();
            });
        });
    }

    setupSearch() {
        if (!this.searchInput) return;

        const debouncedSearch = Utils.debounce(() => {
            this.filter();
        }, 300);

        this.searchInput.addEventListener('input', debouncedSearch);
    }

    filter() {
        const searchTerm = this.searchInput?.value.toLowerCase() || '';

        this.filteredArticles = this.allArticles.filter(article => {
            // Filter by tags
            if (this.activeFilters.size > 0) {
                const articleTags = article.tags.map(t => t.tag);
                const hasActiveTag = articleTags.some(tag => this.activeFilters.has(tag));
                if (!hasActiveTag) return false;
            }

            // Filter by search term
            if (searchTerm) {
                const searchableText = `
                    ${article.headline || ''}
                    ${article.full_text || ''}
                    ${article.source_pdf || ''}
                `.toLowerCase();

                if (!searchableText.includes(searchTerm)) {
                    return false;
                }
            }

            return true;
        });

        this.render();
    }

    render() {
        if (this.filteredArticles.length === 0) {
            this.articleGrid.innerHTML = '<p class="empty-state">No articles match your filters.</p>';
            return;
        }

        // Render article cards
        this.articleGrid.innerHTML = this.filteredArticles.map(article =>
            this.renderArticleCard(article)
        ).join('');

        // Add click handlers
        this.articleGrid.querySelectorAll('.article-card').forEach(card => {
            card.addEventListener('click', () => {
                const articleId = card.dataset.articleId;
                const article = this.allArticles.find(a => a.global_article_id === articleId);
                if (article) {
                    Utils.renderArticleModal(article);
                }
            });
        });
    }

    renderArticleCard(article) {
        const whitechapelClass = article.is_whitechapel ? 'whitechapel' : '';
        const excerpt = Utils.truncate(article.full_text, 150);
        const tags = article.tags.slice(0, 3).map(t =>
            `<span class="article-card-tag">${t.tag.replace(/_/g, ' ')}</span>`
        ).join('');

        return `
            <div class="article-card ${whitechapelClass}" data-article-id="${article.global_article_id}">
                <h3 class="article-card-headline">
                    ${article.headline || 'Untitled Article'}
                </h3>
                <div class="article-card-meta">
                    ${article.source_pdf || 'Unknown source'} |
                    Page ${article.page_number || '?'} |
                    ${article.extracted_date || 'Date unknown'}
                </div>
                <p class="article-card-excerpt">${excerpt}</p>
                <div class="article-card-tags">${tags}</div>
            </div>
        `;
    }
}

window.ArticleBrowser = ArticleBrowser;
