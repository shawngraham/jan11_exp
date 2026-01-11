# Whitechapel in Shawville

> An interactive digital history exploration of how Jack the Ripper's murders reached rural Quebec through The Equity newspaper, 1888-1895

**Live Site:** [Coming Soon - GitHub Pages URL]

## What you're looking at

My kid and I were listening to a podcast about Jack the Ripper. We started talking, and I mentioned how newspapers would reprint stories from each other. This led to us developing an interesting question: did our local newspaper print anything about the Whitechapel murders, and if so, what would that have meant to the people of this community? I filed the thoughts away for future reference, but then later saw some posts about Anastasia Salter's session at the MLA on agentic coding for the humanities (January 2026). I looked up her course materials, and thought I would follow along with them, using their guidance for prompting Claude Code with our initial question. The result is this repository.

---

## Project Origin

My kid and I were listening to a podcast about Jack the Ripper. We started talking, and I mentioned how newspapers would reprint stories from each other. This led to an interesting question: did our local newspaper print anything about the Whitechapel murders, and if so, what would that have meant to the people of _this_ community? I filed it away for future reference, but then later saw some posts about Anastasia Salter's session at the MLA on agentic coding for the humanities. I looked up her course materials, and thought I would follow along with them, using their guidance for prompting Claude Code with our initial question. The result is this repository.

---

## Project Overview

This project explores a compelling question: **What does Jack the Ripper mean to Shawville?**

Between 1888 and 1895, The Equity newspaper in Shawville, Quebec carried reports of the Whitechapel murders, creating curious intrusions of metropolitan horror into rural colonial life. This interactive website visualizes and analyzes these "motes of space-time"—moments when London's East End violence reached an anglophone village in western Quebec.

### Research Questions

- How did global news reach rural anglophone Quebec in the late 19th century?
- What do these articles reveal about metropolis-hinterland relationships?
- How was British identity constructed and maintained in a colonial context?
- What role did sensational crime play in bridging geographic and cultural distance?

---

## Features

### 📅 Dual Timeline
Interactive visualization showing London murders alongside Shawville publications, revealing the time lag of transatlantic news transmission.

### 📰 Newspaper Page Viewer
Visualizes article layouts with Whitechapel stories highlighted as glowing "portals"—spatial intrusions of London into Shawville.

### 📊 Text Analysis
Word clouds, frequency charts, and sensational language analysis reveal how The Equity framed the murders.

### 🔍 Searchable Archive
Browse and search all extracted articles with filtering by topic, date, and content.

### 🎨 Period Aesthetic
Design evokes 19th-century newspapers with aged paper textures, serif typography, and Victorian styling.

---

## Data Processing Pipeline

### Prerequisites

```bash
# Python 3.8+
python3 --version

# Install dependencies
cd scripts
pip install -r requirements.txt
```

**For Apple Silicon (M1/M2/M3) Macs:**

The pipeline is fully compatible with Apple Silicon. You'll need to install poppler for PDF processing:

```bash
# Install poppler via Homebrew
brew install poppler

# Verify installation
which pdfinfo
```

**Note:** EasyOCR runs in CPU mode on Apple Silicon. GPU acceleration is not required.

### Required Dependencies

- **EasyOCR**: Lightweight OCR engine for text extraction
- **pdf2image**: PDF to image conversion
- **OpenCV**: Image processing and column detection
- **PIL/Pillow**: Image manipulation
- **NumPy**: Numerical operations
- **PyTorch**: Deep learning backend for EasyOCR

### Running the Pipeline

1. **Add PDFs to the `pdfs/` folder**
   - Place your newspaper PDF files in the `pdfs/` directory
   - The pipeline expects PDFs from BAnQ or similar archives

2. **Run the full pipeline:**
   ```bash
   python3 scripts/run_pipeline.py
   ```

   This executes six steps in sequence:

   **Stage 1: Preprocessing (`preprocess.py`)**
   - Converts PDFs to images at optimal DPI (auto-calculated, ~100-150 DPI)
   - Detects vertical column boundaries using **morphological line detection**:
     * Binarizes the image (Otsu's thresholding)
     * Uses morphological operations to enhance vertical lines only
     * Creates projection profile from isolated vertical structures
     * Finds peaks (black divider lines) in the profile
     * Handles tight columns and spanning mastheads
   - Splits pages into 5 columns, saves as separate PNG images
   - Outputs: `data/preprocessed/{pdf_name}/` with column images and metadata
   - **Debug mode:** Use `--debug` flag to save 4-panel visualization

   **Stage 2: OCR (`process_pdfs.py`)**
   - Reads preprocessed column images from Stage 1
   - Runs EasyOCR on each column independently
   - Adjusts bounding boxes back to full-page coordinates
   - Outputs: `data/raw/ocr_output.json` with all text blocks

   **Stage 3: Segmentation (`segment_articles.py`)**
   - Groups text blocks into articles based on proximity and layout
   - Outputs: `data/processed/articles.json`

   **Stage 4: Tagging (`tag_articles.py`)**
   - Auto-tags articles (Whitechapel, crime, British Empire, etc.)
   - Outputs: `data/processed/tagged_articles.json`

   **Stage 5: Timeline (`generate_timeline.py`)**
   - Creates dual timeline (London murders vs Shawville publications)
   - Outputs: `data/processed/timeline.json`

   **Stage 6: Analysis (`analyze_text.py`)**
   - Word frequency and sensational language analysis
   - Outputs: `data/processed/text_analysis.json`

3. **Output:**
   Generated files in `data/processed/`:
   - `articles.json` - All extracted articles
   - `tagged_articles.json` - Articles with classifications
   - `timeline.json` - Timeline events
   - `text_analysis.json` - Word clouds and statistics

### Debugging Column Detection

If column boundaries are not detected correctly, use debug mode:

```bash
python3 scripts/preprocess.py --debug
```

This will save 4-panel visualization images to `data/preprocessed/{pdf_name}/debug/`:
- **Top-left:** Original grayscale image
- **Top-right:** Enhanced vertical lines (morphological filtering)
  - Shows only vertical structures (column dividers)
  - Text and horizontal lines removed
- **Bottom-left:** Projection profile graph
  - Peaks (red dots) = detected black divider lines
  - Shows how prominent each vertical line is
- **Bottom-right:** Original with detected dividers (red lines)

**Common issues:**
- **Too many/few columns detected:** Adjust `expected_columns` parameter in `preprocess.py`
- **Dividers too faint:** Lines may be broken/faded - check "Enhanced vertical lines" panel
- **Wrong lines detected:** Adjust `min_peak_height` parameter (currently 0.2) or `vertical_kernel_height`
- **No boundaries detected:** Falls back to even division - check if divider lines are visible in enhanced image

---

## Project Structure

```
/
├── index.html                  # Main website
├── css/
│   ├── main.css               # Core styles & period aesthetic
│   ├── timeline.css           # Timeline visualization
│   ├── newspaper.css          # Newspaper page viewer
│   └── visualizations.css     # Charts and graphs
├── js/
│   ├── main.js                # Application orchestration
│   ├── utils.js               # Helper functions
│   ├── timeline.js            # Dual timeline component
│   ├── newspaper-viewer.js    # Page layout visualization
│   ├── text-viz.js            # Text analysis charts
│   └── browser.js             # Article search/filter
├── scripts/
│   ├── requirements.txt       # Python dependencies
│   ├── run_pipeline.py        # Master pipeline runner
│   ├── process_pdfs.py        # OCR processing
│   ├── segment_articles.py    # Article extraction
│   ├── tag_articles.py        # Content classification
│   ├── generate_timeline.py   # Timeline generation
│   └── analyze_text.py        # Text analysis
├── data/
│   ├── raw/                   # OCR output
│   └── processed/             # Structured data files
├── pdfs/                      # Source PDFs (add here)
└── assets/
    └── images/                # Images and textures
```

---

## Technology Stack

### Frontend
- **HTML5/CSS3**: Semantic markup and modern styling
- **Vanilla JavaScript**: No framework dependencies
- **D3.js v7**: Data visualizations
- **Scrollama**: Scrollytelling interactions
- **GSAP**: Smooth animations

### Backend/Processing
- **Python 3.8+**: Data processing
- **PaddleOCR**: OCR engine
- **NumPy/OpenCV**: Image processing

### Hosting
- **GitHub Pages**: Static site hosting
- **No server required**: Fully client-side application

---

## Development

### Local Development

1. **Clone and navigate:**
   ```bash
   git clone <repository-url>
   cd jan11_exp
   ```

2. **Add PDFs to `pdfs/` folder**

3. **Run data pipeline:**
   ```bash
   python3 scripts/run_pipeline.py
   ```

4. **Serve locally:**
   ```bash
   # Using Python
   python3 -m http.server 8000

   # Or using Node.js
   npx http-server
   ```

5. **Open browser:**
   Navigate to `http://localhost:8000`

### Testing Without Data

The website will display warnings if data files are missing, but the HTML/CSS/JS structure can still be previewed.

---

## Historical Context

### Shawville, Quebec

Founded by Irish Protestant settlers after 1815, Shawville was incorporated in 1873. The Pontiac and Pacific Junction Railway arrived in 1886, transforming the village into a regional hub. By the 1880s, it was an overwhelmingly anglophone (85%) and Protestant (75%) community in western Quebec's Pontiac County.

### The Equity Newspaper

Founded June 7, 1883 by John Cowan and Henry Thomas Smith, The Equity began in Bryson, Quebec before moving to Shawville in October 1888—the very autumn of the Whitechapel murders. As "the Voice of the Pontiac since 1883," it brought world news to rural readers through telegraph dispatches and syndicated content.

### The Whitechapel Murders

Between August and November 1888, at least five women were murdered in London's Whitechapel district. The case became an international sensation, with newspapers worldwide covering the "Jack the Ripper" killings. These reports reached Shawville within days or weeks, creating transnational moments of shared horror.

---

## Data Sources

### Primary Sources
- **The Equity** (Shawville, Quebec), 1888-1895
- Digitized by Bibliothèque et Archives nationales du Québec (BAnQ)
- Seven newspaper issues containing Whitechapel references

### Historical Context
- QAHN (Quebec Anglophone Heritage Network)
- Municipality of Shawville historical archives
- Whitechapel murder chronologies

---

## Citations

Sugden, Philip. *The Complete History of Jack the Ripper*. Carroll & Graf, 2002.

*The Equity*. "About The Equity." https://theequity.ca/about-the-equity/

QAHN. "Shawville: Historic Hub of the Pontiac." https://qahn.org/article/shawville-historic-hub-pontiac

Municipality of Shawville. "History of Shawville." https://shawville.ca/municipality-of-shawville/history-of-shawville/

Bibliothèque et Archives nationales du Québec (BAnQ). Digital collections.

---

## Credits

**Research & Development:** Dr. Shawn Graham

**Built with:**
- D3.js for data visualization
- Scrollama for scrollytelling
- GSAP for animations
- PaddleOCR for text extraction

---

## License

[Add your chosen license here]

---

## Future Enhancements

- [ ] Add audio narration
- [ ] Include original page images alongside transcriptions
- [ ] Comparative analysis with other colonial newspapers
- [ ] Network visualization of information flow
- [ ] Geographic mapping of news sources
- [ ] Export functionality for research use

---

## Contact

For questions or collaboration inquiries, please [open an issue](https://github.com/yourusername/jan11_exp/issues) or contact Dr. Shawn Graham.

---

*This project demonstrates how digital humanities methods can illuminate the networks connecting metropolis and hinterland in the late 19th century.*