/**
 * TEXT ANALYSIS VISUALIZATIONS
 * Word clouds, frequency charts, etc.
 */

class TextVisualizations {
    constructor(textAnalysis, articles) {
        this.data = textAnalysis;
        this.articles = articles;
    }

    init() {
        if (!this.data) {
            console.error('Text analysis data not available');
            return;
        }

        this.renderWordCloud();
        this.renderSensationalWords();
        this.renderFrequencyChart();
        this.renderArticleBreakdown();
    }

    renderWordCloud() {
        const container = document.getElementById('word-cloud');
        if (!container || !this.data.word_cloud_data) return;

        const width = container.clientWidth || 600;
        const height = container.clientHeight || 500;

        // Use D3 for simple word cloud visualization
        const svg = d3.select(container)
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        const words = this.data.word_cloud_data.slice(0, 50);

        // Simple word cloud layout (without complex library)
        const maxSize = d3.max(words, d => d.size);
        const minSize = d3.min(words, d => d.size);

        const fontSize = d3.scaleLinear()
            .domain([minSize, maxSize])
            .range([12, 48]);

        const g = svg.append('g')
            .attr('transform', `translate(${width / 2},${height / 2})`);

        // Spiral placement (simple algorithm)
        words.forEach((word, i) => {
            const angle = i * 0.5;
            const radius = i * 3;
            const x = radius * Math.cos(angle);
            const y = radius * Math.sin(angle);

            g.append('text')
                .attr('x', x)
                .attr('y', y)
                .attr('text-anchor', 'middle')
                .attr('font-family', 'var(--font-display)')
                .attr('font-size', `${fontSize(word.size)}px`)
                .attr('fill', Utils.getTagColor('whitechapel_ripper'))
                .attr('opacity', 0)
                .text(word.text)
                .transition()
                .duration(1000)
                .delay(i * 20)
                .attr('opacity', d3.scaleLinear()
                    .domain([minSize, maxSize])
                    .range([0.4, 1])(word.size)
                );
        });
    }

    renderSensationalWords() {
        const container = document.getElementById('sensational-list');
        if (!container || !this.data.sensational_language) return;

        const sensational = Object.entries(this.data.sensational_language)
            .sort((a, b) => b[1].total_uses - a[1].total_uses)
            .slice(0, 15);

        const html = sensational.map(([word, stats]) => `
            <div class="sensational-item">
                <span class="sensational-word">${word}</span>
                <span class="sensational-count">${stats.total_uses} uses</span>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    renderFrequencyChart() {
        const container = document.getElementById('frequency-chart');
        if (!container) return;

        const width = container.clientWidth || 400;
        const height = 350;
        const margin = { top: 20, right: 20, bottom: 60, left: 50 };

        const svg = d3.select(container)
            .append('svg')
            .attr('class', 'chart-svg')
            .attr('viewBox', `0 0 ${width} ${height}`)
            .attr('preserveAspectRatio', 'xMidYMid meet');

        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        const chartWidth = width - margin.left - margin.right;
        const chartHeight = height - margin.top - margin.bottom;

        // Group articles by date (year)
        const whitechapelArticles = this.articles.filter(a => a.is_whitechapel);

        const byYear = d3.rollup(
            whitechapelArticles,
            v => v.length,
            d => {
                const year = d.extracted_date ? d.extracted_date.split(',')[1]?.trim() : 'Unknown';
                return year || 'Unknown';
            }
        );

        const data = Array.from(byYear, ([year, count]) => ({ year, count }))
            .sort((a, b) => a.year.localeCompare(b.year));

        if (data.length === 0) {
            g.append('text')
                .attr('x', chartWidth / 2)
                .attr('y', chartHeight / 2)
                .attr('text-anchor', 'middle')
                .text('No data available');
            return;
        }

        const x = d3.scaleBand()
            .domain(data.map(d => d.year))
            .range([0, chartWidth])
            .padding(0.2);

        const y = d3.scaleLinear()
            .domain([0, d3.max(data, d => d.count)])
            .range([chartHeight, 0]);

        // Bars
        g.selectAll('.bar')
            .data(data)
            .join('rect')
            .attr('class', 'bar whitechapel')
            .attr('x', d => x(d.year))
            .attr('y', chartHeight)
            .attr('width', x.bandwidth())
            .attr('height', 0)
            .transition()
            .duration(1000)
            .attr('y', d => y(d.count))
            .attr('height', d => chartHeight - y(d.count));

        // Axes
        g.append('g')
            .attr('class', 'axis')
            .attr('transform', `translate(0,${chartHeight})`)
            .call(d3.axisBottom(x));

        g.append('g')
            .attr('class', 'axis')
            .call(d3.axisLeft(y));

        // Labels
        g.append('text')
            .attr('class', 'axis-label')
            .attr('x', chartWidth / 2)
            .attr('y', chartHeight + 45)
            .attr('text-anchor', 'middle')
            .text('Year');

        g.append('text')
            .attr('class', 'axis-label')
            .attr('transform', 'rotate(-90)')
            .attr('x', -chartHeight / 2)
            .attr('y', -35)
            .attr('text-anchor', 'middle')
            .text('Articles');
    }

    renderArticleBreakdown() {
        const container = document.getElementById('article-breakdown');
        if (!container) return;

        const width = container.clientWidth || 400;
        const height = 350;
        const radius = Math.min(width, height) / 2 - 40;

        const svg = d3.select(container)
            .append('svg')
            .attr('class', 'chart-svg')
            .attr('viewBox', `0 0 ${width} ${height}`)
            .attr('preserveAspectRatio', 'xMidYMid meet');

        const g = svg.append('g')
            .attr('transform', `translate(${width / 2},${height / 2})`);

        // Count articles by primary tag
        const tagCounts = d3.rollup(
            this.articles,
            v => v.length,
            d => d.primary_tag
        );

        const data = Array.from(tagCounts, ([tag, count]) => ({ tag, count }))
            .sort((a, b) => b.count - a.count);

        const pie = d3.pie()
            .value(d => d.count)
            .sort(null);

        const arc = d3.arc()
            .innerRadius(radius * 0.5)
            .outerRadius(radius);

        const arcs = g.selectAll('.arc')
            .data(pie(data))
            .join('g')
            .attr('class', 'arc');

        arcs.append('path')
            .attr('fill', d => Utils.getTagColor(d.data.tag))
            .attr('d', arc)
            .transition()
            .duration(1000)
            .attrTween('d', function(d) {
                const interpolate = d3.interpolate({ startAngle: 0, endAngle: 0 }, d);
                return function(t) {
                    return arc(interpolate(t));
                };
            });

        // Labels
        arcs.append('text')
            .attr('transform', d => `translate(${arc.centroid(d)})`)
            .attr('text-anchor', 'middle')
            .attr('font-size', '10px')
            .text(d => d.data.count > 2 ? d.data.tag.replace(/_/g, ' ') : '');
    }
}

window.TextVisualizations = TextVisualizations;
