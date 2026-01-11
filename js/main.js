/**
 * MAIN APPLICATION
 * Orchestrates all components and scroll animations
 */

(async function() {
    'use strict';

    console.log('Whitechapel in Shawville - Initializing...');

    // Load all data
    const data = await Utils.loadAllData();

    if (!data.articles || !data.timeline || !data.textAnalysis) {
        console.error('Failed to load data. Please run the data processing pipeline.');
        showDataWarning();
        return;
    }

    console.log('Data loaded successfully:', {
        articles: data.articles?.total_articles || 0,
        timeline: data.timeline?.statistics || {},
        textAnalysis: data.textAnalysis?.whitechapel_articles_analyzed || 0
    });

    // Initialize components
    initializeComponents(data);

    // Setup scroll animations
    setupScrollAnimations();

    // Setup GSAP animations
    setupGSAPAnimations();

    console.log('Initialization complete!');
})();

function initializeComponents(data) {
    const articles = data.articles?.articles || [];
    const timeline = data.timeline;
    const textAnalysis = data.textAnalysis;

    // Initialize Timeline
    if (timeline && document.getElementById('dual-timeline')) {
        new DualTimeline('dual-timeline', timeline);
    }

    // Initialize Newspaper Viewer
    if (articles.length > 0 && document.getElementById('newspaper-viewer')) {
        new NewspaperViewer('newspaper-viewer', articles);
    }

    // Initialize Text Visualizations
    if (textAnalysis && articles.length > 0) {
        const textViz = new TextVisualizations(textAnalysis, articles);
        textViz.init();
    }

    // Initialize Article Browser
    if (articles.length > 0) {
        new ArticleBrowser(articles);
    }

    // Initialize Empire visualization (placeholder for now)
    initializeEmpireViz(articles);
}

function initializeEmpireViz(articles) {
    const container = document.getElementById('empire-viz');
    if (!container) return;

    // Simple visualization showing British Empire articles alongside Whitechapel
    const britishArticles = articles.filter(a =>
        a.tags.some(t => t.tag === 'british_empire')
    );

    const whitechapelArticles = articles.filter(a => a.is_whitechapel);

    const stats = `
        <div style="text-align: center; padding: 2rem;">
            <h3 style="margin-bottom: 1rem;">The British Empire in The Equity</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 2rem; max-width: 800px; margin: 0 auto;">
                <div>
                    <div style="font-size: 3rem; font-weight: bold; color: var(--color-ripper);">
                        ${whitechapelArticles.length}
                    </div>
                    <div style="color: var(--color-ink-faded);">Whitechapel Articles</div>
                </div>
                <div>
                    <div style="font-size: 3rem; font-weight: bold; color: #191970;">
                        ${britishArticles.length}
                    </div>
                    <div style="color: var(--color-ink-faded);">British Empire Articles</div>
                </div>
                <div>
                    <div style="font-size: 3rem; font-weight: bold; color: var(--color-shawville);">
                        ${articles.length}
                    </div>
                    <div style="color: var(--color-ink-faded);">Total Articles</div>
                </div>
            </div>
            <p style="margin-top: 2rem; font-style: italic; color: var(--color-ink-faded);">
                Whitechapel coverage represented ${((whitechapelArticles.length / articles.length) * 100).toFixed(1)}%
                of all articles extracted
            </p>
        </div>
    `;

    container.innerHTML = stats;
}

function setupScrollAnimations() {
    // Initialize Scrollama
    const scroller = scrollama();

    scroller
        .setup({
            step: '.section',
            offset: 0.5,
            debug: false
        })
        .onStepEnter(response => {
            // Add 'active' class to current section
            response.element.classList.add('active');
        })
        .onStepExit(response => {
            // Remove 'active' class when leaving
            response.element.classList.remove('active');
        });

    // Handle window resize
    window.addEventListener('resize', scroller.resize);
}

function setupGSAPAnimations() {
    // Register ScrollTrigger plugin
    gsap.registerPlugin(ScrollTrigger);

    // Hero fade in
    gsap.from('.hero-content', {
        opacity: 0,
        y: 50,
        duration: 1,
        ease: 'power2.out'
    });

    // Section headers
    gsap.utils.toArray('.section-header').forEach(header => {
        gsap.from(header, {
            scrollTrigger: {
                trigger: header,
                start: 'top 80%',
                toggleActions: 'play none none none'
            },
            opacity: 0,
            y: 30,
            duration: 0.8,
            ease: 'power2.out'
        });
    });

    // Content blocks
    gsap.utils.toArray('.content-block').forEach(block => {
        gsap.from(block, {
            scrollTrigger: {
                trigger: block,
                start: 'top 85%',
                toggleActions: 'play none none none'
            },
            opacity: 0,
            y: 40,
            duration: 1,
            ease: 'power2.out'
        });
    });

    // Context cards
    gsap.utils.toArray('.context-card').forEach((card, index) => {
        gsap.from(card, {
            scrollTrigger: {
                trigger: card,
                start: 'top 85%',
                toggleActions: 'play none none none'
            },
            opacity: 0,
            x: index % 2 === 0 ? -50 : 50,
            duration: 0.8,
            delay: index * 0.1,
            ease: 'power2.out'
        });
    });

    // Visualization cards
    gsap.utils.toArray('.viz-card, .article-card').forEach((card, index) => {
        gsap.from(card, {
            scrollTrigger: {
                trigger: card,
                start: 'top 90%',
                toggleActions: 'play none none none'
            },
            opacity: 0,
            scale: 0.9,
            duration: 0.6,
            delay: index * 0.05,
            ease: 'power2.out'
        });
    });

    // Newspaper pages
    gsap.utils.toArray('.newspaper-page').forEach((page, index) => {
        gsap.from(page, {
            scrollTrigger: {
                trigger: page,
                start: 'top 80%',
                toggleActions: 'play none none none'
            },
            opacity: 0,
            y: 60,
            duration: 1,
            delay: index * 0.2,
            ease: 'power2.out'
        });
    });
}

function showDataWarning() {
    const hero = document.getElementById('hero');
    if (!hero) return;

    const warning = document.createElement('div');
    warning.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: var(--color-ripper);
        color: white;
        padding: 1rem 2rem;
        border-radius: 4px;
        z-index: 1000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        text-align: center;
        max-width: 600px;
    `;

    warning.innerHTML = `
        <strong>Data Not Available</strong><br>
        Please run the data processing pipeline:<br>
        <code style="background: rgba(0,0,0,0.2); padding: 0.25rem 0.5rem; border-radius: 3px; font-family: monospace;">
        python3 scripts/run_pipeline.py
        </code>
    `;

    document.body.appendChild(warning);
}

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});
