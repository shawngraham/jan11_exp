/**
 * NEWSPAPER PAGE VIEWER
 * "Motes of Space-Time" visualization showing article layout
 */

class NewspaperViewer {
    constructor(containerId, articles) {
        this.container = document.getElementById(containerId);
        this.articles = articles;

        // Group articles by source PDF
        this.pageGroups = this.groupByPage();

        this.init();
    }

    init() {
        if (!this.articles || this.articles.length === 0) {
            this.container.innerHTML = '<p class="empty-state">No newspaper data available. Please run the data processing pipeline.</p>';
            return;
        }

        this.renderPages();
    }

    groupByPage() {
        const groups = {};

        this.articles.forEach(article => {
            const key = `${article.source_pdf}_page_${article.page_number}`;

            if (!groups[key]) {
                groups[key] = {
                    pdf: article.source_pdf,
                    pageNumber: article.page_number,
                    imagePath: article.image_path,
                    articles: []
                };
            }

            groups[key].articles.push(article);
        });

        return Object.values(groups).sort((a, b) => {
            if (a.pdf !== b.pdf) {
                return a.pdf.localeCompare(b.pdf);
            }
            return a.pageNumber - b.pageNumber;
        });
    }

    renderPages() {
        this.container.innerHTML = '';

        this.pageGroups.forEach((group, index) => {
            const pageDiv = document.createElement('div');
            pageDiv.className = 'newspaper-page';
            pageDiv.id = `page-${index}`;

            // Header
            const header = `
                <div class="newspaper-page-header">
                    <h3 class="newspaper-page-title">The Equity</h3>
                    <div class="newspaper-page-date">${group.pdf} - Page ${group.pageNumber}</div>
                </div>
            `;

            pageDiv.innerHTML = header;

            // Create content container
            const contentDiv = document.createElement('div');
            contentDiv.className = 'newspaper-page-content';
            pageDiv.appendChild(contentDiv);

            this.container.appendChild(pageDiv);

            // Render articles on this page
            this.renderArticleLayout(contentDiv, group.articles);
        });
    }

    renderArticleLayout(container, articles) {
        const width = 900;
        const height = 700;

        const svg = d3.select(container)
            .append('svg')
            .attr('class', 'newspaper-svg')
            .attr('viewBox', `0 0 ${width} ${height}`)
            .attr('preserveAspectRatio', 'xMidYMid meet');

        const viewer = this;

        // Render each article
        articles.forEach(article => {
            const group = svg.append('g')
                .attr('class', `article-block ${article.is_whitechapel ? 'whitechapel' : ''} ${article.primary_tag}`)
                .style('cursor', 'pointer')
                .on('click', () => {
                    Utils.renderArticleModal(article);
                });

            // Scale bbox to fit SVG
            const bbox = article.bbox || { x: 0, y: 0, width: 100, height: 50 };

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
                // Scale down to fit SVG (assuming original is ~2000px wide)
                const scale = width / 2000;
                bbox.x *= scale;
                bbox.y *= scale;
                bbox.width *= scale;
                bbox.height *= scale;
            }

            // Draw rectangle
            group.append('rect')
                .attr('x', bbox.x)
                .attr('y', bbox.y)
                .attr('width', bbox.width)
                .attr('height', bbox.height)
                .attr('rx', 2);

            // Add text label (headline or truncated text)
            const label = article.headline ||
                          Utils.truncate(article.full_text, 50);

            // Calculate font size based on box size
            const fontSize = Math.min(bbox.height / 5, 12);

            group.append('text')
                .attr('x', bbox.x + bbox.width / 2)
                .attr('y', bbox.y + bbox.height / 2)
                .attr('text-anchor', 'middle')
                .attr('dominant-baseline', 'middle')
                .attr('font-size', `${fontSize}px`)
                .text(this.truncateLabel(label, bbox.width, fontSize));
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
