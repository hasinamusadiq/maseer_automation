import json
import os
import sys
import time
import requests
import base64
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from ai_engine import get_content_from_groq
from image_service import generate_image_with_retry
from video_creator import create_broadcast_reel, get_platform_specs


def ensure_logo_local(logo_path_or_data, brand_name):
    """
    Ensures logo is available as local file path.
    Handles: local path, URL, or base64 string.
    """
    if not logo_path_or_data:
        return None
    
    # Already a local file path
    if isinstance(logo_path_or_data, str) and os.path.exists(logo_path_or_data):
        print(f"   ✅ Logo already local: {logo_path_or_data}")
        return logo_path_or_data
    
    # URL - download it
    if isinstance(logo_path_or_data, str) and logo_path_or_data.startswith('http'):
        return download_logo_from_url(logo_path_or_data, brand_name)
    
    return None


def download_logo_from_url(logo_url, brand_name):
    """Download logo from URL and save locally."""
    if not logo_url or not logo_url.startswith('http'):
        return None

    try:
        response = requests.get(logo_url, timeout=10)
        if response.status_code == 200:
            safe_name = brand_name.replace(' ', '_')
            logo_path = f"logos/{safe_name}_logo.png"
            os.makedirs("logos", exist_ok=True)
            with open(logo_path, 'wb') as f:
                f.write(response.content)
            print(f"   ✅ Logo downloaded: {logo_path}")
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
                print(f"   📤 Uploaded: {os.path.basename(file_path)}")
            else:
                print(f"   ❌ Telegram Upload Failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error during Telegram upload: {e}")


def get_variation_index():
    """Determine content variation based on time (4 variations per day)."""
    current_hour = datetime.now().hour
    return (current_hour // 6) % 4


def get_platform_for_run(client_data):
    """
    Select SINGLE platform for this run based on time rotation.
    """
    platforms = client_data.get('platforms', ['instagram_feed'])
    variation = get_variation_index()
    
    platform_index = variation % len(platforms)
    selected = platforms[platform_index]
    
    return selected, variation


def process_single_client(client_data):
    """
    Process a single client - generate ONE video.
    Returns True if successful, False otherwise.
    """
    brand_name = client_data['brand_name']
    selected_platform, variation = get_platform_for_run(client_data)
    
    print(f"\n{'='*60}")
    print(f"✨ New Client: {brand_name}")
    print(f"🎲 Variation {variation + 1}/4 | Platform: {selected_platform}")
    print(f"{'='*60}")

    try:
        # Handle logo - ensure it's a local file path
        logo_input = client_data.get('logo_path')
        logo_path = ensure_logo_local(logo_input, brand_name)
        client_data['logo_path'] = logo_path  # Update with local path

        # Generate content for SELECTED platform only
        print("   🤖 Generating content with AI...")
        content = get_content_from_groq(
            client_data, 
            platform=selected_platform,
            variation_index=variation
        )

        if not content:
            print("   ❌ Content generation failed")
            return False

        print(f"   📝 {content['text'][:50]}...")
        print(f"   🎨 Motion: {content.get('motion', 'zoom_in')}")

        # Generate image
        clean_name = brand_name.replace(' ', '_')
        print("   🖼️ Generating image...")
        image_path = generate_image_with_retry(content['image_prompt'], clean_name)

        if not image_path:
            print("   ❌ Image generation failed")
            return False

        # Generate SINGLE video
        timestamp = datetime.now().strftime("%m%d_%H%M")
        output_path = f"output/{clean_name}_{selected_platform}_v{variation+1}_{timestamp}.mp4"
        
        print(f"   🎬 Creating video...")
        success = create_broadcast_reel(
            image_path,
            content['text'],
            output_path,
            client_data=client_data,
            platform=selected_platform,
            motion=content.get('motion', 'zoom_in')
        )

        if success:
            # Upload with Ariana Coach branding
            caption = (f"🎯 ARIANA COACH: {brand_name} | {selected_platform.replace('_', ' ').title()}\n"
                      f"📝 {content['text']}\n"
                      f"🎨 Professional AI Marketing Video\n"
                      f"⏰ Variation {variation + 1} of 4")
            send_to_telegram(output_path, caption)
            print(f"   ✅ Successfully processed: {brand_name}")
            return True
        else:
            print(f"   ❌ Video creation failed for: {brand_name}")
            return False

    except Exception as e:
        print(f"   ❌ Error processing {brand_name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_new_clients_only():
    """Get new clients from clients.json."""
    try:
        with open('data/clients.json', 'r', encoding='utf-8') as f:
            clients = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("   ℹ️ No clients.json found or empty")
        return []
    
    valid_clients = []
    for client in clients:
        if isinstance(client, dict) and 'brand_name' in client and not client.get('_comment'):
            valid_clients.append(client)
    
    return valid_clients


def mark_client_processed(client_data):
    """Mark a client as processed by adding timestamp."""
    try:
        with open('data/clients.json', 'r', encoding='utf-8') as f:
            clients = json.load(f)
        
        for client in clients:
            if isinstance(client, dict) and client.get('brand_name') == client_data['brand_name']:
                client['last_processed'] = datetime.now().isoformat()
                client['processed_count'] = client.get('processed_count', 0) + 1
                break
        
        with open('data/clients.json', 'w', encoding='utf-8') as f:
            json.dump(clients, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        print(f"   ⚠️ Could not mark client as processed: {e}")


def main():
    print("🎯 Ariana Coach - AI Marketing Pipeline")
    print(f"⏰ Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Mode: Process new clients from Ariana Coach Portal")
    print("💾 Logo: Supports URL and base64 uploads")
    print("-" * 60)

    # Ensure directories exist
    os.makedirs('output', exist_ok=True)
    os.makedirs('logos', exist_ok=True)

    # Get new clients
    clients = get_new_clients_only()
    
    if not clients:
        print("\n📭 No new clients to process.")
        print("💡 New clients sign up at: https://hasinamusadiq.github.io/maseer-portal/")
        print("\n⏳ Waiting for next scheduled run...")
        return

    print(f"\n📋 Found {len(clients)} new client(s):")
    for c in clients:
        status = "🆕 New" if not c.get('last_processed') else "🔄 Repeat"
        logo_status = "🖼️ Has logo" if c.get('logo_path') else "⚠️ No logo"
        print(f"   • {c['brand_name']} ({status}) - {logo_status}")

    # Statistics
    stats = {
        'total_new': len(clients),
        'successful': 0,
        'failed': 0
    }

    # Process each client
    for idx, client_data in enumerate(clients, 1):
        print(f"\n🔔 Processing client {idx}/{len(clients)}...")
        
        success = process_single_client(client_data)
        
        if success:
            stats['successful'] += 1
            mark_client_processed(client_data)
        else:
            stats['failed'] += 1
        
        if idx < len(clients):
            time.sleep(5)

    # Summary
    print(f"\n{'='*60}")
    print("📊 PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"Clients Found: {stats['total_new']}")
    print(f"Successfully Processed: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Videos Generated: {stats['successful']}")
    print(f"{'='*60}")
    
    if stats['successful'] > 0:
        print("✅ Videos delivered via Telegram!")
    else:
        print("⚠️ No clients were successfully processed this run.")
    
    print("\n🌐 Ariana Coach Portal:")
    print("   https://hasinamusadiq.github.io/maseer-portal/")
    print(f"⏰ Next automated run: +6 hours")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
