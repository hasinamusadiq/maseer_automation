import json
import os
import sys
import argparse
import requests
from datetime import datetime

from ai_engine import get_content_for_campaign, CAMPAIGNS
from image_service import generate_image_with_retry
from video_creator import create_campaign_video


META_WIDTH = 1224
META_HEIGHT = 1536


def ensure_logo(logo_data, brand_name):
    if not logo_data:
        return None
    
    if isinstance(logo_data, str):
        if os.path.exists(logo_data):
            return logo_data
        if logo_data.startswith('http'):
            try:
                r = requests.get(logo_data, timeout=10)
                if r.status_code == 200:
                    path = f"logos/{brand_name.replace(' ', '_')}_logo.png"
                    os.makedirs("logos", exist_ok=True)
                    with open(path, 'wb') as f:
                        f.write(r.content)
                    return path
            except Exception as e:
                print(f"   ⚠️ Logo download failed: {e}")
    
    return None


def send_telegram(video_path, caption, is_sample=False):
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


def process_client_campaign(client_data, campaign_type, is_sample=False):
    brand = client_data['brand_name']
    
    print(f"\n{'='*60}")
    print(f"🎯 {brand} | {CAMPAIGNS[campaign_type]['name']}")
    print(f"⏰ {CAMPAIGNS[campaign_type]['time']} | {CAMPAIGNS[campaign_type]['language']}")
    print(f"🎨 {CAMPAIGNS[campaign_type]['style']}")
    print(f"📐 {META_WIDTH}×{META_HEIGHT} | 4:5 Meta-Optimized")
    print(f"{'='*60}")
    
    print("   🤖 Generating campaign content...")
    content = get_content_for_campaign(client_data, campaign_type, is_sample)
    
    if not content:
        print("   ❌ Content failed")
        return False
    
    print(f"   📝 {content.get('headline', '')[:50]}...")
    
    safe_name = brand.replace(' ', '_')
    img_path = generate_image_with_retry(
        content['image_prompt'], 
        f"{safe_name}_{campaign_type}",
        size=(META_WIDTH, META_HEIGHT)
    )
    
    if not img_path:
        print("   ❌ Image failed")
        return False
    
    timestamp = datetime.now().strftime("%m%d_%H%M")
    type_slug = "SAMPLE" if is_sample else campaign_type.upper()
    output = f"output/{safe_name}_{type_slug}_{timestamp}.mp4"
    
    print(f"   🎬 Rendering video...")
    success = create_campaign_video(
        img_path,
        content,
        client_data,
        output,
        campaign_type
    )
    
    if success:
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
        
        send_telegram(output, caption, is_sample)
        
        update_client_record(client_data, campaign_type, is_sample)
        
        return True
    
    return False


def update_client_record(client_data, campaign_type, is_sample):
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


def get_clients_for_campaign(campaign_type, specific_client=None):
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
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"\n📅 Campaign: {CAMPAIGNS[campaign_type]['name']}")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📐 Output: {META_WIDTH}×{META_HEIGHT} (4:5 Aspect)")
    print("─" * 60)
    
    required = ['GROQ_API_KEY', 'HF_TOKEN', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
    missing = [r for r in required if not os.getenv(r)]
    if missing:
        print(f"❌ Missing: {missing}")
        sys.exit(1)
    
    os.makedirs('output', exist_ok=True)
    os.makedirs('logos', exist_ok=True)
    
    clients = get_clients_for_campaign(campaign_type, args.client)
    
    if not clients:
        print(f"\n📭 No clients for {campaign_type} campaign")
        return
    
    print(f"\n📋 Processing {len(clients)} client(s):")
    for c in clients:
        status = "🆕 Sample" if campaign_type == 'sample' else "📺 Regular"
        print(f"   • {c['brand_name']} ({status})")
    
    stats = {'success': 0, 'failed': 0}
    
    for idx, client in enumerate(clients, 1):
        print(f"\n🔔 [{idx}/{len(clients)}]")
        
        success = process_client_campaign(client, campaign_type, args.sample)
        
        if success:
            stats['success'] += 1
        else:
            stats['failed'] += 1
        
        if idx < len(clients):
            import time
            time.sleep(3)
    
    print(f"\n{'='*60}")
    print("📊 CAMPAIGN COMPLETE")
    print(f"{'='*60}")
    print(f"Total: {len(clients)} | ✅ Success: {stats['success']} | ❌ Failed: {stats['failed']}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
