/**
 * NEWSPAPER PAGE VIEWER
 * "Motes of Space-Time" visualization showing article layout
 * Focuses on pages containing Whitechapel/Ripper articles to show
 * how metropolitan horror "intruded" into rural Quebec news
 */

class NewspaperViewer {
    constructor(containerId, articles) {
        this.container = document.getElementById(containerId);
        this.articles = articles;

        // Group articles by source PDF - ONLY pages with Whitechapel content
        this.pageGroups = this.groupByPage();

        this.init();
    }

    init() {
        if (!this.articles || this.articles.length === 0) {
            this.container.innerHTML = '<p class="empty-state">No newspaper data available. Please run the data processing pipeline.</p>';
            return;
        }

        if (this.pageGroups.length === 0) {
            this.container.innerHTML = '<p class="empty-state">No pages with Whitechapel content found.</p>';
            return;
        }

        this.renderPages();
    }

    groupByPage() {
        const groups = {};

        // First pass: collect all articles by page
        this.articles.forEach(article => {
            const key = `${article.source_pdf}_page_${article.page_number}`;

            if (!groups[key]) {
                groups[key] = {
                    pdf: article.source_pdf,
                    pageNumber: article.page_number,
                    imagePath: article.image_path,
                    articles: [],
                    hasWhitechapel: false
                };
            }

            groups[key].articles.push(article);

            // Track if this page has Whitechapel content
            if (article.is_whitechapel || article.is_ripper_related) {
                groups[key].hasWhitechapel = true;
            }
        });

        // Second pass: filter to ONLY pages with Whitechapel content
        const whitechapelPages = Object.values(groups)
            .filter(page => page.hasWhitechapel)
            .sort((a, b) => {
                if (a.pdf !== b.pdf) {
                    return a.pdf.localeCompare(b.pdf);
                }
                return a.pageNumber - b.pageNumber;
            });

        return whitechapelPages;
    }

    renderPages() {
        this.container.innerHTML = '';

        this.pageGroups.forEach((group, index) => {
            const pageDiv = document.createElement('div');
            pageDiv.className = 'newspaper-page';
            pageDiv.id = `page-${index}`;

            // Count Whitechapel vs total articles
            const whitechapelCount = group.articles.filter(a => a.is_whitechapel || a.is_ripper_related).length;
            const totalCount = group.articles.length;

            // Parse date for display
            const dateMatch = group.pdf.match(/(\d{4}-\d{2}-\d{2})/);
            const displayDate = dateMatch ? Utils.formatDate(dateMatch[1]) : group.pdf;

            // Header with intrusion context
            const header = `
                <div class="newspaper-page-header">
                    <h3 class="newspaper-page-title">The Equity</h3>
                    <div class="newspaper-page-date">${displayDate}</div>
                    <div class="newspaper-page-stats">
                        <span class="whitechapel-count">${whitechapelCount} Whitechapel article${whitechapelCount !== 1 ? 's' : ''}</span>
                        among
                        <span class="total-count">${totalCount} total article${totalCount !== 1 ? 's' : ''}</span>
                        on this page
                    </div>
                </div>
            `;

            pageDiv.innerHTML = header;

            // Create content container
            const contentDiv = document.createElement('div');
            contentDiv.className = 'newspaper-page-content';
            pageDiv.appendChild(contentDiv);

            this.container.appendChild(pageDiv);

            // Render articles on this page
            this.renderArticleLayout(contentDiv, group.articles, group);
        });
    }

    renderArticleLayout(container, articles, pageInfo) {
        const width = 900;
        const height = 700;

        const svg = d3.select(container)
            .append('svg')
            .attr('class', 'newspaper-svg')
            .attr('viewBox', `0 0 ${width} ${height}`)
            .attr('preserveAspectRatio', 'xMidYMid meet');

        // Optional: Add background page image if available
        if (pageInfo.imagePath) {
            svg.append('image')
                .attr('href', pageInfo.imagePath)
                .attr('width', width)
                .attr('height', height)
                .attr('opacity', 0.1)
                .attr('preserveAspectRatio', 'xMidYMid slice');
        }

        const viewer = this;

        // Sort articles: Whitechapel first for layering
        const sortedArticles = [...articles].sort((a, b) => {
            const aIsWhitechapel = a.is_whitechapel || a.is_ripper_related;
            const bIsWhitechapel = b.is_whitechapel || b.is_ripper_related;
            return aIsWhitechapel === bIsWhitechapel ? 0 : (aIsWhitechapel ? 1 : -1);
        });

        // Render each article
        sortedArticles.forEach(article => {
            const isWhitechapel = article.is_whitechapel || article.is_ripper_related;

            const group = svg.append('g')
                .attr('class', `article-block ${isWhitechapel ? 'whitechapel' : ''} ${article.primary_tag || 'general'}`)
                .style('cursor', 'pointer')
                .on('click', () => {
                    Utils.renderArticleModal(article);
                })
                .on('mouseenter', function() {
                    d3.select(this).raise(); // Bring to front on hover
                });

            // Scale bbox to fit SVG
            let bbox = { ...article.bbox } || { x: 0, y: 0, width: 100, height: 50 };

            // Simple layout: stack articles if no position data
            if (!bbox.x || !bbox.y) {
                // Fallback layout
                const index = articles.indexOf(article);
                const cols = 3;
                const col = index % cols;
                const row = Math.floor(index / cols);

                bbox.x = (col * width / cols) + 10;
                bbox.y = (row * 100) + 10;
                bbox.width = (width / cols) - 20;
                bbox.height = 80;
            } else {
                // Scale down to fit SVG (assuming original is ~6000px wide for typical newspaper scan)
                const scale = width / 6000;
                bbox.x *= scale;
                bbox.y *= scale;
                bbox.width *= scale;
                bbox.height *= scale;
            }

            // Draw rectangle with stronger emphasis for Whitechapel
            group.append('rect')
                .attr('x', bbox.x)
                .attr('y', bbox.y)
                .attr('width', bbox.width)
                .attr('height', bbox.height)
                .attr('rx', 2)
                .attr('stroke-width', isWhitechapel ? 2 : 1);

            // Add subtle glow effect for Whitechapel articles
            if (isWhitechapel) {
                group.insert('rect', ':first-child')
                    .attr('x', bbox.x - 2)
                    .attr('y', bbox.y - 2)
                    .attr('width', bbox.width + 4)
                    .attr('height', bbox.height + 4)
                    .attr('rx', 3)
                    .attr('class', 'whitechapel-glow')
                    .attr('fill', 'none')
                    .attr('stroke', 'var(--color-ripper, #8b0000)')
                    .attr('stroke-width', 3)
                    .attr('opacity', 0.3);
            }

            // Add text label (headline or truncated text)
            const label = article.headline ||
                          Utils.truncate(article.full_text, 50);

            // Calculate font size based on box size
            const fontSize = Math.min(Math.max(bbox.height / 5, 6), 12);

            if (fontSize > 4 && bbox.width > 20) {
                group.append('text')
                    .attr('x', bbox.x + bbox.width / 2)
                    .attr('y', bbox.y + bbox.height / 2)
                    .attr('text-anchor', 'middle')
                    .attr('dominant-baseline', 'middle')
                    .attr('font-size', `${fontSize}px`)
                    .attr('class', isWhitechapel ? 'whitechapel-text' : '')
                    .text(this.truncateLabel(label, bbox.width, fontSize));
            }
        });
    }

    truncateLabel(text, maxWidth, fontSize) {
        // Approximate character width
        const charWidth = fontSize * 0.6;
        const maxChars = Math.floor(maxWidth / charWidth);

        if (text.length <= maxChars) {
            return text;
        }

        return text.substring(0, maxChars - 3) + '...';
    }
}

// Initialize newspaper viewer
window.NewspaperViewer = NewspaperViewer;
