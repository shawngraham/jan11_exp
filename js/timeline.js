/**
 * DUAL TIMELINE VISUALIZATION
 * Shows London events vs Shawville publications
 */

class DualTimeline {
    constructor(containerId, data) {
        this.container = document.getElementById(containerId);
        this.data = data;
        this.tooltip = Utils.createTooltip('timeline-tooltip');

        // Dimensions
        this.margin = { top: 60, right: 40, bottom: 60, left: 120 };
        this.width = 1200 - this.margin.left - this.margin.right;
        this.height = 400 - this.margin.top - this.margin.bottom;

        this.init();
    }

    init() {
        if (!this.data || !this.data.london_events || !this.data.shawville_events) {
            console.error('Timeline data not available');
            this.container.innerHTML = '<p class="empty-state">Timeline data not available. Please run the data processing pipeline.</p>';
            return;
        }

        this.processData();
        this.createSVG();
        this.createScales();
        this.render();
    }

    processData() {
        // Parse dates
        this.londonEvents = this.data.london_events.map(d => ({
            ...d,
            date: Utils.parseDate(d.date)
        })).filter(d => d.date);

        this.shawvilleEvents = this.data.shawville_events.map(d => ({
            ...d,
            date: Utils.parseDate(d.date)
        })).filter(d => d.date);

        // Find date range
        const allDates = [...this.londonEvents, ...this.shawvilleEvents].map(d => d.date);
        this.dateExtent = d3.extent(allDates);
    }

    createSVG() {
        const svg = d3.select(this.container)
            .append('svg')
            .attr('class', 'timeline-svg')
            .attr('viewBox', `0 0 ${this.width + this.margin.left + this.margin.right} ${this.height + this.margin.top + this.margin.bottom}`)
            .attr('preserveAspectRatio', 'xMidYMid meet');

        this.svg = svg.append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);
    }

    createScales() {
        // X scale: time
        this.xScale = d3.scaleTime()
            .domain(this.dateExtent)
            .range([0, this.width]);

        // Y positions for tracks
        this.londonY = this.height * 0.3;
        this.shawvilleY = this.height * 0.7;
    }

    render() {
        this.renderTracks();
        this.renderAxis();
        this.renderEvents();
        this.renderConnections();
    }

    renderTracks() {
        // London track
        this.svg.append('line')
            .attr('class', 'timeline-track london')
            .attr('x1', 0)
            .attr('y1', this.londonY)
            .attr('x2', this.width)
            .attr('y2', this.londonY);

        this.svg.append('text')
            .attr('class', 'timeline-label track-label')
            .attr('x', -10)
            .attr('y', this.londonY)
            .attr('dy', '0.35em')
            .attr('text-anchor', 'end')
            .text('London');

        // Shawville track
        this.svg.append('line')
            .attr('class', 'timeline-track shawville')
            .attr('x1', 0)
            .attr('y1', this.shawvilleY)
            .attr('x2', this.width)
            .attr('y2', this.shawvilleY);

        this.svg.append('text')
            .attr('class', 'timeline-label track-label')
            .attr('x', -10)
            .attr('y', this.shawvilleY)
            .attr('dy', '0.35em')
            .attr('text-anchor', 'end')
            .text('Shawville');
    }

    renderAxis() {
        const xAxis = d3.axisBottom(this.xScale)
            .ticks(d3.timeMonth.every(2))
            .tickFormat(d3.timeFormat('%b %Y'));

        this.svg.append('g')
            .attr('class', 'timeline-axis')
            .attr('transform', `translate(0,${this.height})`)
            .call(xAxis)
            .selectAll('text')
            .style('text-anchor', 'end')
            .attr('dx', '-.8em')
            .attr('dy', '.15em')
            .attr('transform', 'rotate(-45)');
    }

    renderEvents() {
        const timeline = this;

        // London events
        const londonGroups = this.svg.selectAll('.london-event')
            .data(this.londonEvents)
            .join('g')
            .attr('class', d => `timeline-event london ${d.type}`)
            .attr('transform', d => `translate(${this.xScale(d.date)},${this.londonY})`)
            .on('mouseover', function(event, d) {
                timeline.showTooltip(event, d);
            })
            .on('mouseout', () => {
                timeline.tooltip.hide();
            });

        londonGroups.append('circle')
            .attr('r', d => d.type === 'murder' ? 8 : 6);

        // Shawville events
        const shawvilleGroups = this.svg.selectAll('.shawville-event')
            .data(this.shawvilleEvents)
            .join('g')
            .attr('class', 'timeline-event shawville')
            .attr('transform', d => `translate(${this.xScale(d.date)},${this.shawvilleY})`)
            .on('mouseover', function(event, d) {
                timeline.showTooltip(event, d);
            })
            .on('mouseout', () => {
                timeline.tooltip.hide();
            })
            .on('click', (event, d) => {
                if (d.article_id && Utils.DataCache.articles) {
                    const article = Utils.DataCache.articles.articles.find(
                        a => a.global_article_id === d.article_id
                    );
                    if (article) {
                        Utils.renderArticleModal(article);
                    }
                }
            });

        shawvilleGroups.append('circle')
            .attr('r', 6);
    }

    renderConnections() {
        // Draw lines connecting Shawville events to related London events
        const connections = this.shawvilleEvents
            .filter(d => d.related_london_event)
            .map(shawville => {
                const london = this.londonEvents.find(
                    l => l.id === shawville.related_london_event
                );
                return london ? { shawville, london } : null;
            })
            .filter(d => d);

        this.svg.selectAll('.timeline-connection')
            .data(connections)
            .join('path')
            .attr('class', 'timeline-connection')
            .attr('d', d => {
                const x1 = this.xScale(d.london.date);
                const y1 = this.londonY;
                const x2 = this.xScale(d.shawville.date);
                const y2 = this.shawvilleY;

                // Curved path
                const midY = (y1 + y2) / 2;
                return `M ${x1},${y1} Q ${x1},${midY} ${(x1 + x2) / 2},${midY} T ${x2},${y2}`;
            });
    }

    showTooltip(event, d) {
        const content = `
            <div class="timeline-tooltip-title">${d.title}</div>
            <div class="timeline-tooltip-date">${d.date_display || Utils.formatDate(d.date)}</div>
            <div class="timeline-tooltip-description">${d.description}</div>
            ${d.time_lag_days ?
                `<div class="timeline-tooltip-lag">Published ${d.time_lag_days} days after murder</div>` :
                ''
            }
        `;

        this.tooltip.show(content, event.pageX, event.pageY);
    }
}

// Initialize timeline when data is loaded
window.DualTimeline = DualTimeline;
