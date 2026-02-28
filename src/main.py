import json
import os
import sys
import time
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from ai_engine import get_content_from_groq
from image_service import generate_image_with_retry
from video_creator import create_broadcast_reel, get_platform_specs


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
    This ensures only ONE video per client per workflow run.
    """
    platforms = client_data.get('platforms', ['instagram_feed'])
    variation = get_variation_index()
    
    # Cycle through platforms based on variation
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
        # Download logo if URL provided
        logo_path = client_data.get('logo_path')
        if logo_path and logo_path.startswith('http'):
            logo_path = download_logo(logo_path, brand_name)
            client_data['logo_path'] = logo_path

        # Generate content for SELECTED platform only
        print("   🤖 Generating broadcast content...")
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
        print("   🖼️ Generating broadcast image...")
        image_path = generate_image_with_retry(content['image_prompt'], clean_name)

        if not image_path:
            print("   ❌ Image generation failed")
            return False

        # Generate SINGLE video (broadcast style)
        timestamp = datetime.now().strftime("%m%d_%H%M")
        output_path = f"output/{clean_name}_{selected_platform}_v{variation+1}_{timestamp}.mp4"
        
        print(f"   🎬 Creating broadcast video...")
        success = create_broadcast_reel(
            image_path,
            content['text'],
            output_path,
            client_data=client_data,
            platform=selected_platform,
            motion=content.get('motion', 'zoom_in')
        )

        if success:
            # Upload with broadcast branding
            caption = (f"📺 NEW CLIENT: {brand_name} | {selected_platform.replace('_', ' ').title()}\n"
                      f"📝 {content['text']}\n"
                      f"🎨 Broadcast Style: B Nazanin Bold + TV Effects\n"
                      f"⏰ Variation {variation + 1} of 4")
            send_to_telegram(output_path, caption)
            print(f"   ✅ Successfully processed new client: {brand_name}")
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
    """
    Get ONLY new clients from clients.json that haven't been processed yet.
    A client is considered "new" if it was added in the last 7 days OR
    if it has no 'last_processed' timestamp.
    
    For new-client-only workflow, we process ALL clients in the file
    assuming the file only contains new signups from frontend.
    """
    try:
        with open('data/clients.json', 'r', encoding='utf-8') as f:
            clients = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("   ℹ️ No clients.json found or empty")
        return []
    
    # Filter out template/comment entries
    valid_clients = []
    for client in clients:
        if isinstance(client, dict) and 'brand_name' in client and not client.get('_comment'):
            valid_clients.append(client)
    
    return valid_clients


def mark_client_processed(client_data):
    """
    Mark a client as processed by adding timestamp.
    This helps track which clients have been serviced.
    """
    try:
        with open('data/clients.json', 'r', encoding='utf-8') as f:
            clients = json.load(f)
        
        # Find and update the client
        for client in clients:
            if isinstance(client, dict) and client.get('brand_name') == client_data['brand_name']:
                client['last_processed'] = datetime.now().isoformat()
                client['processed_count'] = client.get('processed_count', 0) + 1
                break
        
        # Save back
        with open('data/clients.json', 'w', encoding='utf-8') as f:
            json.dump(clients, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        print(f"   ⚠️ Could not mark client as processed: {e}")


def main():
    print("🚀 Maseer Broadcast Pipeline - NEW CLIENTS ONLY")
    print(f"⏰ Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Mode: Process only new clients from frontend signups")
    print("📺 Style: B Nazanin Bold + Impact | Broadcast TV Effects")
    print("-" * 60)

    # Ensure directories exist
    os.makedirs('output', exist_ok=True)
    os.makedirs('logos', exist_ok=True)

    # Get new clients (from frontend signups via GitHub Issues)
    clients = get_new_clients_only()
    
    if not clients:
        print("\n📭 No new clients to process.")
        print("💡 New clients sign up at: https://hasinamusadiq.github.io/maseer-portal/")
        print("   (Form submissions create GitHub Issues that update clients.json)")
        print("\n⏳ Waiting for next scheduled run...")
        return

    print(f"\n📋 Found {len(clients)} new client(s) from frontend signups:")
    for c in clients:
        status = "🆕 New" if not c.get('last_processed') else "🔄 Repeat"
        print(f"   • {c['brand_name']} ({status})")

    # Statistics
    stats = {
        'total_new': len(clients),
        'successful': 0,
        'failed': 0
    }

    # Process each new client
    for idx, client_data in enumerate(clients, 1):
        print(f"\n🔔 Processing client {idx}/{len(clients)}...")
        
        success = process_single_client(client_data)
        
        if success:
            stats['successful'] += 1
            mark_client_processed(client_data)
        else:
            stats['failed'] += 1
        
        # Delay between clients (except last one)
        if idx < len(clients):
            time.sleep(5)

    # Summary
    print(f"\n{'='*60}")
    print("📊 NEW CLIENT PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"New Clients Found: {stats['total_new']}")
    print(f"Successfully Processed: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Videos Generated: {stats['successful']} (1 per client)")
    print(f"{'='*60}")
    
    if stats['successful'] > 0:
        print("✅ New clients have been onboarded! Videos delivered via Telegram.")
    else:
        print("⚠️ No clients were successfully processed this run.")
    
    print("\n🌐 Next new client can sign up at:")
    print("   https://hasinamusadiq.github.io/maseer-portal/")
    print(f"⏰ Next automated run: +6 hours")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
