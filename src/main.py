#!/usr/bin/env python3
"""
Maseer Media Inc. - AI Video Marketing Pipeline
Main orchestrator for processing client queue and generating videos.
Located at: src/main.py
"""

import json
import os
import sys
import time
import requests
import base64
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_engine import get_content_from_groq
from image_service import generate_image_with_retry
from video_creator import create_meta_optimized_reel, get_platform_specs


# ============================================================================
# PATH CONFIGURATION
# ============================================================================

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, 'data')
LOGOS_DIR = os.path.join(REPO_ROOT, 'logos')
OUTPUT_DIR = os.path.join(REPO_ROOT, 'output')
CLIENTS_FILE = os.path.join(DATA_DIR, 'clients.json')

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGOS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================================
# LOGO HANDLING
# ============================================================================

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
            safe_name = brand_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            logo_path = os.path.join(LOGOS_DIR, f"{safe_name}_logo.png")
            
            with open(logo_path, 'wb') as f:
                f.write(response.content)
            
            print(f"   ✅ Logo downloaded: {logo_path}")
            return logo_path
    except Exception as e:
        print(f"   ⚠️ Could not download logo: {e}")

    return None


# ============================================================================
# TELEGRAM DELIVERY
# ============================================================================

def send_to_telegram(file_path, caption):
    """Sends a single video to Telegram immediately after generation."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("   ⚠️ Telegram credentials missing. Skipping upload.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"

    try:
        with open(file_path, 'rb') as video:
            payload = {'chat_id': chat_id, 'caption': caption}
            files = {'video': video}
            response = requests.post(url, data=payload, files=files, timeout=60)

            if response.status_code == 200:
                print(f"   📤 Uploaded to Telegram: {os.path.basename(file_path)}")
                return True
            else:
                print(f"   ❌ Telegram upload failed: {response.status_code}")
                print(f"      Response: {response.text[:200]}")
                return False
    except Exception as e:
        print(f"   ❌ Telegram error: {e}")
        return False


# ============================================================================
# CONTENT ROTATION LOGIC
# ============================================================================

def get_variation_index():
    """Determine content variation based on time (4 variations per day)."""
    current_hour = datetime.now().hour
    return (current_hour // 6) % 4


def get_platform_for_run(client_data):
    """
    Select SINGLE platform for this run based on time rotation.
    """
    platforms = client_data.get('platforms', ['instagram_feed', 'instagram_story'])
    variation = get_variation_index()
    
    platform_index = variation % len(platforms)
    selected = platforms[platform_index]
    
    return selected, variation


# ============================================================================
# CLIENT PROCESSING
# ============================================================================

def process_single_client(client_data):
    """
    Process a single client - generate ONE video.
    Returns True if successful, False otherwise.
    """
    brand_name = client_data.get('brand_name', 'Unknown')
    selected_platform, variation = get_platform_for_run(client_data)
    
    print(f"\n{'='*60}")
    print(f"✨ Processing: {brand_name}")
    print(f"🎲 Variation {variation + 1}/4 | Platform: {selected_platform}")
    print(f"{'='*60}")

    try:
        # Handle logo - ensure it's a local file path
        logo_input = client_data.get('logo_path')
        logo_path = ensure_logo_local(logo_input, brand_name)
        client_data['logo_path'] = logo_path  # Update with local path

        # Generate content for SELECTED platform only
        print("   🤖 Generating AI content...")
        content = get_content_from_groq(
            client_data, 
            platform=selected_platform,
            variation_index=variation
        )

        if not content:
            print("   ❌ Content generation failed")
            return False

        print(f"   📝 Headline: {content['text'][:60]}...")
        print(f"   🎨 Motion: {content.get('motion', 'zoom_in')}")

        # Generate image
        clean_name = brand_name.replace(' ', '_').replace('/', '_')
        print("   🖼️ Generating image...")
        image_path = generate_image_with_retry(content['image_prompt'], clean_name)

        if not image_path or not os.path.exists(image_path):
            print("   ❌ Image generation failed")
            return False

        # Generate video
        timestamp = datetime.now().strftime("%m%d_%H%M")
        output_filename = f"{clean_name}_{selected_platform}_v{variation+1}_{timestamp}.mp4"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        print(f"   🎬 Creating video...")
        success = create_meta_optimized_reel(
            image_path,
            content['text'],
            output_path,
            client_data=client_data,
            platform=selected_platform,
            motion=content.get('motion', 'zoom_in')
        )

        if success and os.path.exists(output_path):
            # Upload with Maseer branding
            caption = (
                f"📺 MASEER MEDIA: {brand_name}\n"
                f"📱 Platform: {selected_platform.replace('_', ' ').title()}\n"
                f"📝 {content['text']}\n"
                f"🎨 Professional AI Marketing Video\n"
                f"⏰ Variation {variation + 1} of 4\n\n"
                f"Powered by Ariana Coach | Kabul, Afghanistan"
            )
            
            send_to_telegram(output_path, caption)
            
            # Update client record
            client_data['last_processed'] = datetime.now().isoformat()
            client_data['processed_count'] = client_data.get('processed_count', 0) + 1
            client_data['last_video'] = output_filename
            
            print(f"   ✅ Success: {brand_name}")
            return True
        else:
            print(f"   ❌ Video creation failed")
            return False

    except Exception as e:
        print(f"   ❌ Error processing {brand_name}: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# CLIENT QUEUE MANAGEMENT
# ============================================================================

def load_clients():
    """Load clients from JSON database."""
    try:
        with open(CLIENTS_FILE, 'r', encoding='utf-8') as f:
            clients = json.load(f)
            if isinstance(clients, list):
                return clients
            return []
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"   ℹ️ No existing clients.json found")
        return []


def save_clients(clients):
    """Save updated clients to JSON database."""
    try:
        with open(CLIENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(clients, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"   ⚠️ Could not save clients.json: {e}")
        return False


def get_clients_to_process(clients):
    """
    Get list of clients that need processing.
    Includes new clients and existing clients (for rotation).
    """
    to_process = []
    
    for client in clients:
        if not isinstance(client, dict):
            continue
            
        if 'brand_name' not in client:
            continue
        
        # Process if:
        # 1. Never processed (new client)
        # 2. Processed more than 6 hours ago (rotation)
        last_processed = client.get('last_processed')
        if not last_processed:
            to_process.append(client)
        else:
            try:
                last_time = datetime.fromisoformat(last_processed)
                hours_since = (datetime.now() - last_time).total_seconds() / 3600
                if hours_since >= 6:
                    to_process.append(client)
            except:
                to_process.append(client)
    
    return to_process


def update_client_in_db(updated_client):
    """Update a specific client in the database."""
    clients = load_clients()
    
    for i, client in enumerate(clients):
        if isinstance(client, dict) and client.get('brand_name') == updated_client.get('brand_name'):
            clients[i] = updated_client
            break
    
    return save_clients(clients)


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    """Main entry point for the video generation pipeline."""
    print("🚀 Maseer Media Inc. - AI Marketing Pipeline")
    print(f"⏰ Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📺 Mode: Process client queue")
    print(f"💾 Directories: data={DATA_DIR}, logos={LOGOS_DIR}, output={OUTPUT_DIR}")
    print("⚡ Powered by Ariana Coach")
    print("-" * 60)

    # Verify environment
    required_env = ['GROQ_API_KEY', 'HF_TOKEN']
    missing = [env for env in required_env if not os.getenv(env)]
    if missing:
        print(f"❌ Missing required environment variables: {missing}")
        return

    # Load clients
    clients = load_clients()
    
    if not clients:
        print("\n📭 No clients in database.")
        print("💡 New clients sign up at: https://hasinamusadiq.github.io/maseer_portal/")
        print("\n⏳ Waiting for next scheduled run...")
        return

    # Get queue
    to_process = get_clients_to_process(clients)
    
    if not to_process:
        print(f"\n📭 No clients ready for processing (checked {len(clients)} clients).")
        print("⏳ All clients processed within last 6 hours.")
        return

    print(f"\n📋 Found {len(to_process)} client(s) to process:")
    for c in to_process:
        status = "🆕 New" if not c.get('last_processed') else "🔄 Rotation"
        logo_status = "🖼️ Has logo" if c.get('logo_path') else "⚠️ No logo"
        print(f"   • {c['brand_name']} ({status}) - {logo_status}")

    # Statistics
    stats = {
        'total': len(to_process),
        'successful': 0,
        'failed': 0
    }

    # Process each client
    for idx, client_data in enumerate(to_process, 1):
        print(f"\n🔔 Processing {idx}/{len(to_process)}...")
        
        success = process_single_client(client_data)
        
        if success:
            stats['successful'] += 1
            update_client_in_db(client_data)
        else:
            stats['failed'] += 1
        
        # Brief pause between clients
        if idx < len(to_process):
            time.sleep(2)

    # Summary
    print(f"\n{'='*60}")
    print("📊 MASEER MEDIA INC. - PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"Clients Processed: {stats['total']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Videos Generated: {stats['successful']}")
    print(f"{'='*60}")
    
    if stats['successful'] > 0:
        print("✅ Videos delivered via Telegram!")
    else:
        print("⚠️ No videos generated this run.")
    
    print("\n🌐 Portal: https://hasinamusadiq.github.io/maseer_portal/")
    print(f"⚡ Powered by Ariana Coach")
    print(f"⏰ Next run: +6 hours")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
