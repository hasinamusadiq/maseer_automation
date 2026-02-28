import json
import os
import sys
import time
import requests
import random
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from ai_engine import get_content_from_groq
from image_service import generate_image_with_retry
from video_creator import create_meta_optimized_reel, get_platform_specs


def download_logo(logo_url, brand_name):
    """Download logo from URL and save locally."""
    if not logo_url:
        return None

    try:
        response = requests.get(logo_url, timeout=10)
        if response.status_code == 200:
            logo_path = f"logos/{brand_name.replace(' ', '_')}_logo.png"
            os.makedirs("logos", exist_ok=True)
            with open(logo_path, 'wb') as f:
                f.write(response.content)
            return logo_path
    except Exception as e:
        print(f"   ⚠️ Could not download logo: {e}")

    return None


def send_to_telegram(file_path, caption):
    """Sends a single video to Telegram immediately after generation."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("⚠️ Telegram credentials missing. Skipping upload.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"

    try:
        with open(file_path, 'rb') as video:
            payload = {'chat_id': chat_id, 'caption': caption}
            files = {'video': video}
            response = requests.post(url, data=payload, files=files)

            if response.status_code == 200:
                print(f"   📤 Successfully uploaded to Telegram: {os.path.basename(file_path)}")
            else:
                print(f"   ❌ Telegram Upload Failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error during Telegram upload: {e}")


def get_variation_index(brand_name):
    """
    Determine content variation based on time to ensure variety across runs.
    Uses hour of day to rotate through 4 variations (0-5, 6-11, 12-17, 18-23).
    """
    current_hour = datetime.now().hour
    variation = (current_hour // 6) % 4  # 4 variations per day
    return variation


def process_single_platform(image_path, content, client_data, platform, brand_name, 
                           upload_to_telegram=True):
    """
    Generate video for a specific platform.
    
    Args:
        image_path: Path to source image
        content: Content dict with text, motion, etc.
        client_data: Client configuration
        platform: Platform key (e.g., 'instagram_feed')
        brand_name: Clean brand name for filename
        upload_to_telegram: Whether to upload after generation
    
    Returns:
        tuple: (success: bool, output_path: str or None)
    """
    specs = get_platform_specs(platform)
    clean_name = brand_name.replace(' ', '_')
    
    # Create platform-specific filename with timestamp
    timestamp = datetime.now().strftime("%m%d_%H%M")
    output_path = f"output/{clean_name}_{platform}_{timestamp}.mp4"
    
    print(f"\n   🎬 Generating {platform.replace('_', ' ').title()}...")
    print(f"      Resolution: {specs['size'][0]}x{specs['size'][1]} ({specs['aspect_ratio']})")
    
    success = create_meta_optimized_reel(
        image_path,
        content['text'],
        output_path,
        client_data=client_data,
        platform=platform,
        motion=content.get('motion', 'zoom_in')
    )
    
    if success and upload_to_telegram:
        platform_display = platform.replace('_', ' ').title()
        variation_info = f" (Variation {content.get('variation_index', 0) + 1})"
        caption = (f"✅ {platform_display} Video for {client_data['brand_name']}{variation_info}\n\n"
                  f"📝 {content['text']}\n\n"
                  f"📐 {specs['aspect_ratio']} • {specs['size'][0]}x{specs['size'][1]}\n"
                  f"🏷️ {' '.join(content.get('hashtags', [])[:3])}")
        send_to_telegram(output_path, caption)
    
    return success, output_path if success else None


def get_client_platforms(client_data):
    """
    Determine which platforms to generate videos for.
    
    Priority:
    1. client_data['platforms'] list if specified
    2. client_data['platform'] single value
    3. Default: ['instagram_feed'] for backward compatibility
    """
    # Check for explicit platforms list
    if 'platforms' in client_data and isinstance(client_data['platforms'], list):
        return client_data['platforms']
    
    # Check for single platform specification
    if 'platform' in client_data:
        return [client_data['platform']]
    
    # Default fallback
    return ['instagram_feed']


def select_brands_for_run(clients, max_brands_per_run=2):
    """
    Select which brands to process in this run to distribute load.
    Uses day of month to cycle through brands if list is long.
    """
    if len(clients) <= max_brands_per_run:
        return clients
    
    # Cycle through brands based on day of month
    day_of_month = datetime.now().day
    start_index = (day_of_month * max_brands_per_run) % len(clients)
    
    selected = []
    for i in range(max_brands_per_run):
        idx = (start_index + i) % len(clients)
        selected.append(clients[idx])
    
    return selected


def main():
    print("🚀 Starting Maseer Automated Pipeline for Kabul Brands...")
    print(f"⏰ Run started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📱 Meta Platforms: Instagram (Feed/Story/Reel) + Facebook (Feed/Story)")
    print("⏳ Schedule: Every 6 hours (4 runs/day)")

    try:
        with open('data/clients.json', 'r', encoding='utf-8') as f:
            clients = json.load(f)
    except FileNotFoundError:
        print("❌ Error: data/clients.json not found.")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in clients.json: {e}")
        return

    os.makedirs('output', exist_ok=True)
    os.makedirs('logos', exist_ok=True)

    # Select brands for this run (distribute load across day)
    brands_to_process = select_brands_for_run(clients, max_brands_per_run=2)
    print(f"\n📋 Processing {len(brands_to_process)} brand(s) this run:")

    # Statistics tracking
    stats = {
        'total_clients': len(brands_to_process),
        'successful': 0,
        'failed': 0,
        'videos_generated': 0,
        'platforms': {}
    }

    for client_data in brands_to_process:
        brand_name = client_data['brand_name']
        variation_index = get_variation_index(brand_name)
        
        print(f"\n{'='*60}")
        print(f"✨ Processing: {brand_name} ({client_data.get('location', 'Kabul')})")
        print(f"🎲 Content Variation: {variation_index + 1}/4 (based on time slot)")
        print(f"{'='*60}")

        try:
            # Download logo if URL provided
            logo_path = client_data.get('logo_path')
            if logo_path and logo_path.startswith('http'):
                logo_path = download_logo(logo_path, brand_name)
                client_data['logo_path'] = logo_path

            # Determine which platforms to generate for
            platforms = get_client_platforms(client_data)
            print(f"   📱 Platforms: {', '.join(platforms)}")

            # Generate content ONCE per brand (varies by time of day)
            print("   🤖 Generating content with AI...")
            content = get_content_from_groq(
                client_data, 
                platform=platforms[0],  # Primary platform for content generation
                variation_index=variation_index
            )

            if not content:
                print("   ❌ Failed to generate content")
                stats['failed'] += 1
                continue

            print(f"   📝 Text: {content['text'][:60]}...")
            print(f"   🎨 Motion: {content.get('motion', 'zoom_in')}")
            print(f"   🏷️ Hashtags: {', '.join(content.get('hashtags', [])[:3])}")

            # Generate image ONCE (reused for all platforms)
            clean_name = brand_name.replace(' ', '_')
            print("   🖼️ Generating image...")
            image_path = generate_image_with_retry(content['image_prompt'], clean_name)

            if not image_path:
                print("   ❌ Failed to generate image")
                stats['failed'] += 1
                continue

            # Generate videos for each platform using same content/image
            client_success = False
            for platform in platforms:
                if platform not in ['instagram_feed', 'instagram_story', 'instagram_reel',
                                  'facebook_feed', 'facebook_story', 'linkedin']:
                    print(f"   ⚠️ Unknown platform '{platform}', skipping...")
                    continue
                
                # Add variation metadata
                content['variation_index'] = variation_index
                
                success, video_path = process_single_platform(
                    image_path, content, client_data, platform, 
                    brand_name, upload_to_telegram=True
                )
                
                if success:
                    client_success = True
                    stats['videos_generated'] += 1
                    stats['platforms'][platform] = stats['platforms'].get(platform, 0) + 1
                
                # Delay between platforms to avoid rate limits
                time.sleep(3)

            if client_success:
                stats['successful'] += 1
            else:
                stats['failed'] += 1

            # Delay between clients
            time.sleep(5)

        except Exception as e:
            print(f"   ❌ Error processing {brand_name}: {e}")
            import traceback
            traceback.print_exc()
            stats['failed'] += 1

    # Print summary
    print(f"\n{'='*60}")
    print("📊 PIPELINE SUMMARY")
    print(f"{'='*60}")
    print(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Brands Processed: {stats['total_clients']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Total Videos Generated: {stats['videos_generated']}")
    print("\nPlatform Breakdown:")
    for platform, count in sorted(stats['platforms'].items()):
        print(f"  • {platform.replace('_', ' ').title()}: {count}")
    print(f"{'='*60}")
    print("✅ Pipeline complete. Next run in 6 hours.")


if __name__ == "__main__":
    main()
