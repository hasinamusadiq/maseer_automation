import os
import time
from huggingface_hub import InferenceClient
from PIL import Image, ImageDraw, ImageFilter
import numpy as np


# Fixed Meta dimensions
TARGET_SIZE = (1224, 1536)


def generate_image_with_retry(prompt, filename_base, size=TARGET_SIZE, max_retries=3):
    """
    Generate campaign-optimized image at 1224×1536.
    """
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        print("   ⚠️ No HF_TOKEN, using placeholder")
        return create_placeholder(filename_base, size)

    client = InferenceClient(token=hf_token)
    
    # Enhance prompt for 1224×1536
    enhanced_prompt = (
        f"{prompt}, professional photography, 8K UHD, sharp focus, "
        f"vertical composition 4:5 aspect ratio, {size[0]}x{size[1]} pixels, "
        f"negative space for text overlay in lower third, "
        f"cinematic lighting, color grading, Afghan aesthetic authenticity"
    )
    
    output_path = f"scene_{filename_base}.png"
    
    print(f"   🎨 Generating {size[0]}×{size[1]} image...")
    
    for attempt in range(max_retries):
        try:
            # Use SDXL with optimal settings for vertical
            image = client.text_to_image(
                enhanced_prompt,
                model="stabilityai/stable-diffusion-xl-base-1.0",
                height=size[1],
                width=size[0],
                num_inference_steps=50,
                guidance_scale=7.5
            )
            
            # Post-process for text readiness
            image = optimize_for_text(image, size)
            image.save(output_path, quality=95)
            
            print(f"   ✅ Saved: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"   ⚠️ Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return create_placeholder(filename_base, size)
    
    return create_placeholder(filename_base, size)


def optimize_for_text(image, target_size):
    """Prepare image for text overlay."""
    # Ensure exact size
    if image.size != target_size:
        image = image.resize(target_size, Image.Resampling.LANCZOS)
    
    # Slight blur in text area for readability
    draw = ImageDraw.Draw(image)
    
    # Create mask for lower third
    mask = Image.new('L', target_size, 0)
    mask_draw = ImageDraw.Draw(mask)
    
    # Gradient mask for text area (bottom 35%)
    for y in range(int(target_size[1] * 0.65), target_size[1]):
        alpha = int(255 * ((y - target_size[1] * 0.65) / (target_size[1] * 0.35)) * 0.3)
        mask_draw.line([(0, y), (target_size[0], y)], fill=alpha)
    
    # Apply slight darkening
    dark = Image.new('RGB', target_size, (0, 0, 0))
    image = Image.composite(dark, image, mask)
    
    return image


def create_placeholder(filename_base, size=TARGET_SIZE):
    """Create branded placeholder."""
    path = f"fallback_{filename_base}.png"
    
    # Create gradient background
    img = Image.new('RGB', size, (20, 20, 30))
    draw = ImageDraw.Draw(img)
    
    # Diagonal gradient
    for i in range(size[0] + size[1]):
        alpha = min(255, int(255 * (i / (size[0] + size[1]))))
        color = (30 + alpha//10, 20, 40 + alpha//8)
        draw.line([(i, 0), (0, i)], fill=color, width=1)
    
    # Add Maseer branding
    try:
        # Center text
        text = "Maseer Media"
        # Use default font
        draw.text((size[0]//2, size[1]//2 - 50), text, 
                 fill=(107, 33, 168), anchor="mm")
        draw.text((size[0]//2, size[1]//2 + 20), 
                 "Generating Your Video...", 
                 fill=(200, 200, 200), anchor="mm")
    except:
        pass
    
    img.save(path)
    print(f"   ⚠️ Placeholder: {path}")
    return path
