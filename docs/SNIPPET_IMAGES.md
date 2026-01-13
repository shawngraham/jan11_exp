# Adding Snippet Images to the Visualization

The visualization supports displaying actual newspaper snippet images alongside the OCR-transcribed text when you click on an article.

## Image Format

The system expects snippet images at the following path:

```
data/preprocessed/{source_pdf}/{article_id}.jpg
```

### Example Paths

For article `83471_1890-01-09_p6_a031` from PDF `83471_1890-01-09`:
```
data/preprocessed/83471_1890-01-09/83471_1890-01-09_p6_a031.jpg
```

For article `83471_1894-03-22_p2_a023` from PDF `83471_1894-03-22`:
```
data/preprocessed/83471_1894-03-22/83471_1894-03-22_p2_a023.jpg
```

## Directory Structure

```
data/
├── raw/                          # Original PDFs
├── processed/                    # JSON data files
│   ├── articles.json
│   ├── tagged_articles.json
│   └── timeline.json
└── preprocessed/                 # Snippet images (add these)
    ├── 83471_1890-01-09/
    │   ├── 83471_1890-01-09_p6_a031.jpg
    │   ├── 83471_1890-01-09_p6_a032.jpg
    │   └── ...
    ├── 83471_1891-02-26/
    │   ├── 83471_1891-02-26_p2_a033.jpg
    │   └── ...
    └── ...
```

## Generating Snippet Images

If you have the original newspaper PDFs and the article bounding box data, you can extract snippet images using a script like this:

```python
#!/usr/bin/env python3
"""
Extract article snippet images from newspaper PDFs using bbox coordinates
"""
import json
import os
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image

def extract_snippets(articles_json_path, pdf_dir, output_dir):
    """Extract snippet images for all articles."""

    # Load articles data
    with open(articles_json_path, 'r') as f:
        data = json.load(f)

    articles = data.get('articles', [])

    # Group articles by source PDF
    by_pdf = {}
    for article in articles:
        pdf_name = article['source_pdf']
        if pdf_name not in by_pdf:
            by_pdf[pdf_name] = []
        by_pdf[pdf_name].append(article)

    # Process each PDF
    for pdf_name, pdf_articles in by_pdf.items():
        print(f"Processing {pdf_name}...")

        # Convert PDF to images (one per page)
        pdf_path = Path(pdf_dir) / f"{pdf_name}.pdf"
        if not pdf_path.exists():
            print(f"  Warning: PDF not found at {pdf_path}")
            continue

        # Convert PDF pages to images
        pages = convert_from_path(str(pdf_path), dpi=300)

        # Create output directory for this PDF
        pdf_output_dir = Path(output_dir) / pdf_name
        pdf_output_dir.mkdir(parents=True, exist_ok=True)

        # Extract each article snippet
        for article in pdf_articles:
            bbox = article.get('bbox')
            page_num = article.get('page_number', 1)
            article_id = article['article_id']

            if not bbox or page_num > len(pages):
                continue

            # Get the page image (page_number is 1-indexed)
            page_image = pages[page_num - 1]

            # Extract snippet using bbox coordinates
            snippet = page_image.crop((
                bbox['x'],
                bbox['y'],
                bbox['x'] + bbox['width'],
                bbox['y'] + bbox['height']
            ))

            # Save snippet
            output_path = pdf_output_dir / f"{article_id}.jpg"
            snippet.save(output_path, 'JPEG', quality=95)

        print(f"  Extracted {len(pdf_articles)} snippets")

if __name__ == '__main__':
    extract_snippets(
        articles_json_path='data/processed/tagged_articles.json',
        pdf_dir='data/raw',
        output_dir='data/preprocessed'
    )
```

### Requirements

```bash
pip install pdf2image Pillow
```

You may also need to install `poppler-utils`:
```bash
# Ubuntu/Debian
sudo apt-get install poppler-utils

# macOS
brew install poppler
```

## How It Works

1. When a user clicks on an article snippet in the visualization
2. The modal attempts to load the image from the expected path
3. If the image exists:
   - It displays side-by-side with the OCR text (on desktop)
   - Image appears on left, text on right
4. If the image doesn't exist:
   - The image section is hidden
   - Only the OCR-transcribed text is shown

## Whitechapel Articles

There are **19 Whitechapel/Ripper articles** across **6 pages**:

- `83471_1890-01-09` (page 6): 2 articles
- `83471_1891-02-26` (page 2): 2 articles
- `83471_1891-05-07` (page 2): 1 article
- `83471_1894-03-22` (page 2): 7 articles
- `83471_1895-05-16` (page 3): 2 articles
- `83471_1895-10-03` (page 2): 5 articles

Prioritize extracting snippets for these articles to enhance the "Motes of Space-Time" visualization!

## Image Specifications

- **Format**: JPEG or PNG
- **Recommended DPI**: 150-300 for web display
- **Color**: Grayscale or color (grayscale recommended for historical newspapers)
- **Size**: Images are scaled automatically to fit the modal

## Testing

After adding snippet images, test by:

1. Opening `index.html` in a browser
2. Scrolling to the "Motes of Space-Time" section
3. Clicking on a Whitechapel article (highlighted in red)
4. Verifying the modal shows both the image and OCR text
