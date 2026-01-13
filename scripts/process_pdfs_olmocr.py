#!/usr/bin/env python3
"""
Process images listed in all_metadata.json using olmOCR and output results as JSONL.
"""

import json
import sys
import base64
from pathlib import Path
from io import BytesIO

import torch
from PIL import Image
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
from olmocr.prompts import build_no_anchoring_v4_yaml_prompt


def load_model():
    """
    Initialize and return the olmOCR model and processor.
    """
    print("Loading olmOCR model...")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        "allenai/olmOCR-2-7B-1025", 
        torch_dtype=torch.bfloat16
    ).eval()
    
    processor = AutoProcessor.from_pretrained("Qwen/Qwen2.5-VL-7B-Instruct")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    model.to(device)
    
    return model, processor, device


def image_to_base64(image_path: str) -> str:
    """
    Convert an image file to base64 string.
    """
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extract_text_from_image(
    image_path: str, 
    model, 
    processor, 
    device,
    max_new_tokens: int = 4096
) -> str:
    """
    Extract text from an image using olmOCR.
    
    Args:
        image_path: Path to the image file
        model: The loaded model
        processor: The loaded processor
        device: torch device
        max_new_tokens: Maximum tokens to generate
        
    Returns:
        Extracted text from the image
    """
    # Load and encode the image
    image_base64 = image_to_base64(image_path)
    
    # Determine image type from extension
    ext = Path(image_path).suffix.lower()
    mime_type = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }.get(ext, 'image/jpeg')
    
    # Build the prompt
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": build_no_anchoring_v4_yaml_prompt()},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
            ],
        }
    ]
    
    # Apply the chat template and processor
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    main_image = Image.open(image_path)
    
    inputs = processor(
        text=[text],
        images=[main_image],
        padding=True,
        return_tensors="pt",
    )
    inputs = {key: value.to(device) for (key, value) in inputs.items()}
    
    # Generate the output
    with torch.no_grad():
        output = model.generate(
            **inputs,
            temperature=0.1,
            max_new_tokens=max_new_tokens,
            num_return_sequences=1,
            do_sample=True,
        )
    
    # Decode the output
    prompt_length = inputs["input_ids"].shape[1]
    new_tokens = output[:, prompt_length:]
    text_output = processor.tokenizer.batch_decode(
        new_tokens, skip_special_tokens=True
    )
    
    return text_output[0] if text_output else ""


def process_metadata(
    metadata_path: str, 
    output_path: str,
    model,
    processor,
    device
) -> None:
    """
    Process all images listed in metadata and write results as JSONL.
    
    Args:
        metadata_path: Path to all_metadata.json
        output_path: Path for output JSONL file
        model: The loaded model
        processor: The loaded processor
        device: torch device
    """
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    # Count total snippets for progress
    total_snippets = sum(
        len(page.get('snippets', []))
        for doc in metadata 
        for page in doc.get('pages', [])
    )
    
    print(f"Found {total_snippets} images to process")
    
    with open(output_path, 'w') as out_file:
        processed = 0
        
        for doc in metadata:
            source_pdf = doc.get('source_pdf', '')
            
            for page in doc.get('pages', []):
                page_num = page.get('page_num')
                
                for snippet in page.get('snippets', []):
                    image_path = snippet.get('path', '')
                    column = snippet.get('column')
                    
                    processed += 1
                    print(f"Processing [{processed}/{total_snippets}]: {Path(image_path).name}")
                    
                    try:
                        # Extract text from image
                        text = extract_text_from_image(
                            image_path, model, processor, device
                        )
                        
                        # Create output record
                        record = {
                            "pub": source_pdf,
                            "page": page_num,
                            "col": column,
                            "text": text
                        }
                        
                        # Write as JSONL (one JSON object per line)
                        out_file.write(json.dumps(record) + '\n')
                        out_file.flush()
                        
                    except Exception as e:
                        print(f"  Error: {e}", file=sys.stderr)
                        # Write error record
                        record = {
                            "pub": source_pdf,
                            "page": page_num,
                            "col": column,
                            "text": "",
                            "error": str(e)
                        }
                        out_file.write(json.dumps(record) + '\n')
                        out_file.flush()
    
    print(f"\nComplete! Output written to: {output_path}")


def main():
    # Default paths - adjust as needed
    metadata_path = "data/preprocessed/all_metadata.json"
    output_path = "data/preprocessed/extracted_text_olmocr.jsonl"
    
    # Allow command-line overrides
    if len(sys.argv) >= 2:
        metadata_path = sys.argv[1]
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    
    # Validate input exists
    if not Path(metadata_path).exists():
        print(f"Error: Metadata file not found: {metadata_path}", file=sys.stderr)
        sys.exit(1)
    
    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Load model once
    model, processor, device = load_model()
    
    # Process all images
    process_metadata(metadata_path, output_path, model, processor, device)


if __name__ == "__main__":
    main()