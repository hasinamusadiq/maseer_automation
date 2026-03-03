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
                    print(f"   ⚠️ Telegram attempt {attempt+1} error
