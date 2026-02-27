import json
import os
import sys
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))

from ai_engine import get_content_from_groq
from image_service import generate_image_with_retry
from video_creator import create_advanced_video_reel


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
                print(f"   ?? Successfully uploaded to Telegram: {file_path}")
            else:
                print(f"   ❌ Telegram Upload Failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error during Telegram upload: {e}")


def main():
    print("?? Starting Maseer Automated Pipeline for Kabul Brands...")

    try:
        with open('data/clients.json', 'r', encoding='utf-8') as f:
            clients = json.load(f)
    except FileNotFoundError:
        print("❌ Error: data/clients.json not found.")
        return

    os.makedirs('output', exist_ok=True)
    os.makedirs('logos', exist_ok=True)

    for client_data in clients:
        brand_name = client_data['brand_name']
        print(f"\n✨ Processing: {brand_name} ({client_data.get('location', 'Kabul')})")

        try:
            logo_path = client_data.get('logo_path')
            if logo_path and logo_path.startswith('http'):
                logo_path = download_logo(logo_path, brand_name)
                client_data['logo_path'] = logo_path

            content = get_content_from_groq(client_data)

            if not content:
                continue

            clean_name = brand_name.replace(' ', '_')
            image_path = generate_image_with_retry(content['image_prompt'], clean_name)

            if not image_path:
                continue

            video_output_path = f"output/{clean_name}_final.mp4"
            success = create_advanced_video_reel(
                image_path,
                content['text'],
                video_output_path,
                client_data=client_data,
                motion=content.get('motion', 'zoom_in')
            )

            if success:
                caption = f"✅ جدیدترین تبلیغات برای {brand_name}\n\n?? {content['text']}"
                send_to_telegram(video_output_path, caption)

            time.sleep(3)

        except Exception as e:
            print(f"   ❌ Error processing {brand_name}: {e}")

    print("\n?? Pipeline complete. All Afghan client videos processed.")


if __name__ == "__main__":
    main()
