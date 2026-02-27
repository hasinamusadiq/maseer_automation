import os
import time
from huggingface_hub import InferenceClient
from PIL import Image, ImageDraw


def generate_image_with_retry(prompt, index, max_retries=2):
    """
    Generates images with high-quality Afghan-centric prompts.
    """
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        return create_placeholder(index)

    client = InferenceClient(token=hf_token)
    primary_model = "stabilityai/stable-diffusion-xl-base-1.0"
    output_path = f"scene_{index}.png"

    optimized_prompt = f"{prompt}, professional photography, high resolution, 4K quality, sharp focus"
    optimized_prompt += ", clear bottom area for text placement, uncluttered lower composition"

    print(f"   - Generating Image: {optimized_prompt[:80]}...")
    try:
        image = client.text_to_image(optimized_prompt, model=primary_model)
        image.save(output_path)
        return output_path
    except Exception as e:
        print(f"   ⚠️ Primary failed, attempting fallback or placeholder...")
        return create_placeholder(index)


def create_placeholder(index):
    path = f"fallback_{index}.png"
    img = Image.new('RGB', (1080, 1920), color=(25, 25, 30))
    draw = ImageDraw.Draw(img)
    for i in range(0, 1920, 40):
        alpha = int(255 * (1 - i / 1920))
        draw.rectangle([(0, i), (1080, i + 40)], fill=(35, 35, 40))
    img.save(path)
    return path
