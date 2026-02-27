import os
import json
from groq import Groq


def get_content_from_groq(client_data):
    """
    Fetches ONE video content variation tailored to Afghan/Kabul brands.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ Error: GROQ_API_KEY not found.")
        return None

    client = Groq(api_key=api_key)

    system_prompt = """You are Maseer - an elite Afghan media and advertising expert with extensive experience in minimal zero-cost social media marketing and branding for Kabul-based businesses.

Your expertise:
• 15+ years crafting viral, minimal-budget campaigns that maximize organic reach
• Deep understanding of Afghan consumer psychology and purchasing triggers
• Master of zero-cost marketing strategies (organic growth, community building, word-of-mouth)
• Specialist in Persian/Dari copywriting that resonates with local audiences
• Expert in visual storytelling that captures attention in the first 2 seconds
• Knowledgeable about Afghan cultural nuances, seasonal trends, and local slang
• Proven track record building brands with minimal resources

Your approach:
• Create hooks that stop the scroll immediately
• Use power words that drive action (تماس بگیرید, همین حالا, ویژه, تخفیف, محدود)
• Keep messaging authentic to Afghan values (family, trust, quality, hospitality, honor)
• Design for mobile-first viewing (vertical 9:16 format)
• Focus on cost-effective strategies that deliver maximum ROI
• Leverage emotional triggers specific to Afghan audience"""

    user_prompt = f"""Generate ONE high-converting video reel content for:

BRAND: {client_data['brand_name']} ({client_data.get('local_name', '')})
LOCATION: {client_data.get('location', 'Kabul, Afghanistan')}
INDUSTRY: {client_data['industry']}
TARGET: {client_data['target_audience']}
OFFERINGS: {client_data['key_offerings']}
COLORS: Primary {client_data['primary_color']}, Secondary {client_data['secondary_color']}

STRICT OUTPUT (JSON only):
{{
  "text": "Persian/Dari headline - 6-10 words max. Use Kabul terminology. Include implicit/explicit CTA. Make it scroll-stopping.",
  "image_prompt": "English prompt for AI image generation. Include: minimalistic, clean-typography, negative-space, high-contrast, cinematic-lighting, professional-photography, afghan-aesthetic, uncluttered-composition, focal-point-center, bokeh-background, vibrant-yet-balanced, modern-corporate, editorial-style. Reserve bottom 25% for text overlay. Complement brand color {client_data['primary_color']}.",
  "motion": "zoom_in" or "pan_right" - choose based on image composition
}}

Return ONLY valid JSON. No explanations."""

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )

        response_data = json.loads(completion.choices[0].message.content)
        return response_data

    except Exception as e:
        print(f"❌ Groq API Error for {client_data['brand_name']}: {e}")
        return None
