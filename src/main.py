import json
import os
import sys
import argparse
import requests
import time
from datetime import datetime
from typing import Dict, Optional

from ai_engine import get_content_for_campaign, CAMPAIGNS
from image_service import generate_image_with_retry
from video_creator import create_campaign_video


META_WIDTH = 1224
META_HEIGHT = 1536


def ensure_logo(logo_data: str, brand_name: str) -> Optional[str]:
    """Download or save logo from various sources."""
    if not logo_data:
        return None
    
    safe_name = brand_name.replace(' ', '_').replace('/', '_')
    logo_dir = 'logos'
    os.makedirs(logo_dir, exist_ok=True)
    
    if isinstance(logo_data, str):
        # URL
        if logo_data.startswith('http'):
            try:
                r = requests.get(logo_data, timeout=10)
                if r.status_code == 200:
                    path = f"{logo_dir}/{safe_name}_logo.png"
                    with open(path, 'wb') as f:
                        f.write(r.content)
                    print(f"   ✅ Logo downloaded: {path}")
                    return path
            except Exception as e:
                print(f"   ⚠️ Logo download failed: {e}")
        
        # Base64
        elif len(logo_data) > 100:
            try:
                import base64
                if ',' in logo_data:
                    _, logo_data = logo_data.split(',', 1)
                
                logo_bytes = base64.b64decode(logo_data)
                path = f"{logo_dir}/{safe_name}_logo.png"
                
                with open(path, 'wb') as f:
                    f.write(logo_bytes)
                
                print(f"   ✅ Logo saved: {path} ({len(logo_bytes)} bytes)")
                return path
                
            except Exception as e:
                print(f"   ⚠️ Logo decode failed: {e}")
    
    return None


def send_telegram(video_path: str, caption: str, is_sample: bool = False) -> bool:
    """Send video via Telegram Bot."""
    bot = os.getenv('TELEGRAM_BOT_TOKEN')
    chat = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot or not chat:
        print("   ⚠️ Telegram not configured")
        return False
    
    url = f"https://api.telegram.org/bot{bot}/sendVideo"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with open(video_path, 'rb') as v:
                payload = {
                    'chat_id': chat,
                    'caption': caption,
                    'parse_mode': 'HTML',
                    'width': META_WIDTH,
                    'height': META_HEIGHT
                }
                if is_sample:
                    payload['disable_notification'] = False
                
                r = requests.post(url, data=payload, files={'video': v}, timeout=120)
                
                if r.status_code == 200:
                    print(f"   📤 Telegram: {os.path.basename(video_path)}")
                    return True
                else:
                    print(f"   ⚠️ Telegram attempt {attempt+1} error: {r.status_code}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        
        except Exception as e:
            print(f"   ⚠️ Telegram attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    
    print(f"   ❌ Telegram failed after {max_retries} attempts")
    return False


def upload_to_firebase_storage(video_path: str, firebase_uid: str) -> Optional[str]:
    """Upload video to Firebase Storage and return public URL."""
    try:
        import firebase_admin
        from firebase_admin import credentials, storage
        
        # Initialize if not already
        if not firebase_admin._apps:
            # Try service account file first
            cred_path = 'firebase-service-account.json'
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
            else:
                # Try environment variable
                import base64
                service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
                if service_account_json:
                    # Decode if base64 encoded
                    try:
                        decoded = base64.b64decode(service_account_json)
                        account_info = json.loads(decoded)
                    except:
                        account_info = json.loads(service_account_json)
                    
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                        json.dump(account_info, f)
                        cred = credentials.Certificate(f.name)
                else:
                    print("   ⚠️ No Firebase credentials found")
                    return None
            
            firebase_admin.initialize_app(cred, {
                'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
            })
        
        bucket = storage.bucket()
        blob_path = f'videos/{firebase_uid}/sample.mp4'
        blob = bucket.blob(blob_path)
        
        # Upload with metadata
        print(f"   ☁️  Uploading to Firebase Storage...")
        blob.upload_from_filename(
            video_path,
            content_type='video/mp4',
            metadata={
                'firebaseUid': firebase_uid,
                'uploadedAt': datetime.now().isoformat()
            }
        )
        
        # Make publicly readable (or use signed URLs)
        blob.make_public()
        
        print(f"   ✅ Firebase Storage: {blob.public_url}")
        return blob.public_url
        
    except Exception as e:
        print(f"   ⚠️ Firebase upload failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def notify_firebase_video_ready(firebase_uid: str, video_url: str, brand_name: str) -> bool:
    """Notify Firebase that video is ready."""
    try:
        function_url = os.getenv('FIREBASE_FUNCTION_URL')
        if not function_url:
            print("   ⚠️ FIREBASE_FUNCTION_URL not set")
            return False
        
        # Use PAT_TOKEN as bearer token for authentication
        github_token = os.getenv('PAT_TOKEN')
        
        response = requests.post(
            function_url,
            headers={
                'Authorization': f'Bearer {github_token}',
                'Content-Type': 'application/json'
            },
            json={
                'firebaseUid': firebase_uid,
                'videoUrl': video_url,
                'brandName': brand_name
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"   ✅ Firebase notified: video ready")
            return True
        else:
            print(f"   ⚠️ Firebase notify failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ⚠️ Firebase notify error: {e}")
        return False


def process_client_campaign(client_data: Dict, campaign_type: str, is_sample: bool = False) -> bool:
    """Process a single client campaign."""
    brand = client_data['brand_name']
    firebase_uid = client_data.get('firebase_uid', 'unknown')
    
    print(f"\n{'='*60}")
    print(f"🎯 {brand} | {CAMPAIGNS[campaign_type]['name']}")
    print(f"⏰ {CAMPAIGNS[campaign_type]['time']} | {CAMPAIGNS[campaign_type]['language']}")
    print(f"🎨 {CAMPAIGNS[campaign_type]['style']}")
    print(f"📐 {META_WIDTH}×{META_HEIGHT} | 4:5 Meta-Optimized")
    print(f"🔥 Firebase UID: {firebase_uid}")
    print(f"{'='*60}")
    
    # Generate content
    print("   🤖 Generating campaign content...")
    content = get_content_for_campaign(client_data, campaign_type, is_sample)
    
    if not content:
        print("   ❌ Content generation failed")
        return False
    
    print(f"   📝 Headline: {content.get('headline', '')[:50]}...")
    
    # Generate image
    safe_name = brand.replace(' ', '_').replace('/', '_')
    img_path = generate_image_with_retry(
        content['image_prompt'], 
        f"{safe_name}_{campaign_type}",
        size=(META_WIDTH, META_HEIGHT)
    )
    
    if not img_path:
        print("   ❌ Image generation failed")
        return False
    
    # Create video
    timestamp = datetime.now().strftime("%m%d_%H%M")
    type_slug = "SAMPLE" if is_sample else campaign_type.upper()
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = f"{output_dir}/{safe_name}_{type_slug}_{timestamp}.mp4"
    
    print(f"   🎬 Rendering video...")
    success = create_campaign_video(
        img_path,
        content,
        client_data,
        output_path,
        campaign_type
    )
    
    if not success:
        print("   ❌ Video creation failed")
        return False
    
    # Delivery and notifications
    campaign = CAMPAIGNS[campaign_type]
    
    if is_sample:
        caption = (
            f"<b>🎬 UNDENIABLE SAMPLE - {brand}</b>\n\n"
            f"✨ <b>{content.get('headline', '')}</b>\n\n"
            f"📐 <b>Meta-Optimized:</b> {META_WIDTH}×{META_HEIGHT}px (4:5)\n"
            f"🎨 <b>Style:</b> Maximum Impact Fusion\n"
            f"⚡ <b>Generation Time:</b> Under 5 minutes\n\n"
            f"<b>Your Daily Schedule:</b>\n"
            f"🌅 6AM Celestial | 🏛️ 12PM Organic\n"
            f"💼 6PM Kinetic | 🎭 12AM Tactile\n\n"
            f"<i>Reply SUBSCRIBE to activate daily delivery</i>"
        )
    else:
        caption = (
            f"<b>{brand}</b> | {campaign['name']}\n"
            f"⏰ {campaign['time']} Kabul Time\n"
            f"🌐 {campaign['language']}\n\n"
            f"<b>{content.get('headline', '')}</b>\n\n"
            f"🎨 {campaign['style']}\n"
            f"⚡ {campaign['energy']}\n\n"
            f"<i>Maseer Media • 1224×1536 • Meta-Optimized</i>"
        )
    
    # Send to Telegram
    telegram_sent = send_telegram(output_path, caption, is_sample)
    
    # For samples, also upload to Firebase for frontend streaming
    if is_sample and firebase_uid != 'unknown':
        print("   ☁️  Uploading to Firebase for web streaming...")
        
        firebase_url = upload_to_firebase_storage(output_path, firebase_uid)
        
        if firebase_url:
            # Notify Firebase that video is ready
            notify_firebase_video_ready(firebase_uid, firebase_url, brand)
            
            # Also create GitHub Release as backup
            print("   📦 Creating GitHub Release...")
            create_github_release(output_path, brand, firebase_uid)
    
    # Update client record
    update_client_record(client_data, campaign_type, is_sample)
    
    return True


def create_github_release(video_path: str, brand_name: str, firebase_uid: str):
    """Create GitHub Release with video as asset."""
    try:
        import subprocess
        
        tag = f"sample-{firebase_uid[:8]}-{int(time.time())}"
        
        # Create release using gh CLI or API
        pat = os.getenv('PAT_TOKEN')
        repo = os.getenv('GITHUB_REPOSITORY', 'hasinamusadiq/maseer_automation')
        
        # Use GitHub API
        url = f"https://api.github.com/repos/{repo}/releases"
        headers = {
            'Authorization': f'token {pat}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Create release
        release_data = {
            'tag_name': tag,
            'name': f'Sample: {brand_name}',
            'body': f'Firebase UID: {firebase_uid}\nBrand: {brand_name}',
            'draft': False,
            'prerelease': True
        }
        
        r = requests.post(url, headers=headers, json=release_data)
        if r.status_code != 201:
            print(f"   ⚠️ Release creation failed: {r.status_code}")
            return
        
        release_id = r.json()['id']
        upload_url = r.json()['upload_url'].replace('{?name,label}', '')
        
        # Upload asset
        video_name = os.path.basename(video_path)
        with open(video_path, 'rb') as f:
            headers['Content-Type'] = 'video/mp4'
            r = requests.post(
                f"{upload_url}?name={video_name}",
                headers=headers,
                data=f
            )
        
        if r.status_code == 201:
            print(f"   ✅ GitHub Release: {tag}")
        else:
            print(f"   ⚠️ Asset upload failed: {r.status_code}")
            
    except Exception as e:
        print(f"   ⚠️ GitHub Release error: {e}")


def update_client_record(client_data: Dict, campaign_type: str, is_sample: bool):
    """Update client record in clients.json."""
    try:
        with open('data/clients.json', 'r') as f:
            clients = json.load(f)
        
        for c in clients:
            if c.get('brand_name') == client_data['brand_name']:
                c['last_processed'] = datetime.now().isoformat()
                
                if is_sample:
                    c['sample_generated'] = True
                    c['sample_date'] = datetime.now().isoformat()
                else:
                    campaigns_done = c.get('campaigns_completed', [])
                    if campaign_type not in campaigns_done:
                        campaigns_done.append(campaign_type)
                    c['campaigns_completed'] = campaigns_done
                    c['total_videos'] = c.get('total_videos', 0) + 1
                
                break
        
        with open('data/clients.json', 'w') as f:
            json.dump(clients, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        print(f"   ⚠️ Record update failed: {e}")


def get_clients_for_campaign(campaign_type: str, specific_client: Optional[str] = None):
    """Get eligible clients for campaign."""
    try:
        with open('data/clients.json', 'r') as f:
            clients = json.load(f)
    except:
        return []
    
    eligible = []
    
    for client in clients:
        if not isinstance(client, dict):
            continue
            
        if specific_client and client.get('brand_name') != specific_client:
            continue
        
        if campaign_type == 'sample':
            if client.get('request_sample') and not client.get('sample_generated'):
                eligible.append(client)
            continue
        
        campaigns_done = client.get('campaigns_completed', [])
        
        # Reset daily
        last = client.get('last_processed', '')
        today = datetime.now().strftime('%Y-%m-%d')
        if last and not last.startswith(today):
            client['campaigns_completed'] = []
            campaigns_done = []
        
        if campaign_type not in campaigns_done:
            eligible.append(client)
    
    return eligible


def main():
    parser = argparse.ArgumentParser(description='Maseer Campaign Pipeline')
    parser.add_argument('--campaign', choices=['morning', 'midday', 'evening', 'night', 'sample'],
                       default='morning', help='Campaign type to run')
    parser.add_argument('--client', type=str, help='Process specific client only')
    parser.add_argument('--sample', action='store_true', help='Generate sample video')
    args = parser.parse_args()
    
    campaign_type = 'sample' if args.sample else args.campaign
    
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║           MASEER MEDIA - CAMPAIGN PIPELINE                   ║")
    print("║           1224×1536 Meta-Optimized Video Generation          ║")
    print("║           Firebase + Telegram + GitHub Integration           ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"\n📅 Campaign: {CAMPAIGNS[campaign_type]['name']}")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📐 Output: {META_WIDTH}×{META_HEIGHT} (4:5 Aspect)")
    print("─" * 60)
    
    # Check required secrets
    required = ['GROQ_API_KEY', 'HF_TOKEN']
    if args.sample:
        required.extend(['FIREBASE_STORAGE_BUCKET', 'FIREBASE_FUNCTION_URL', 'PAT_TOKEN'])
    
    missing = [r for r in required if not os.getenv(r)]
    if missing:
        print(f"❌ Missing required environment variables: {missing}")
        sys.exit(1)
    
    # Optional warnings
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        print("   ⚠️ TELEGRAM_BOT_TOKEN not set - Telegram delivery disabled")
    
    os.makedirs('output', exist_ok=True)
    os.makedirs('logos', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    clients = get_clients_for_campaign(campaign_type, args.client)
    
    if not clients:
        print(f"\n📭 No clients for {campaign_type} campaign")
        return
    
    print(f"\n📋 Processing {len(clients)} client(s):")
    for c in clients:
        status = "🆕 Sample" if campaign_type == 'sample' else "📺 Regular"
        fb_info = f" | FB: {c.get('facebook_page', 'N/A')[:30]}..." if c.get('facebook_page') else ""
        print(f"   • {c['brand_name']} ({status}){fb_info}")
    
    stats = {'success': 0, 'failed': 0}
    
    for idx, client in enumerate(clients, 1):
        print(f"\n🔔 [{idx}/{len(clients)}]")
        
        success = process_client_campaign(client, campaign_type, args.sample)
        
        if success:
            stats['success'] += 1
        else:
            stats['failed'] += 1
        
        if idx < len(clients):
            time.sleep(3)
    
    print(f"\n{'='*60}")
    print("📊 CAMPAIGN COMPLETE")
    print(f"{'='*60}")
    print(f"Total: {len(clients)} | ✅ Success: {stats['success']} | ❌ Failed: {stats['failed']}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
