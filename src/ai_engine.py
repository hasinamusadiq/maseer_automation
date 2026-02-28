import os
import json
from groq import Groq


def get_content_from_groq(client_data, platform='instagram_feed', variation_index=0):
    """
    Fetches video content tailored to Afghan/Kabul brands with platform-specific optimization.
    
    Args:
        client_data: Dictionary containing brand information
        platform: Target platform (instagram_feed, instagram_story, etc.)
        variation_index: Index for generating multiple variations (0, 1, 2...)
    
    Returns:
        Dictionary with text, image_prompt, motion, and platform-specific metadata
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ Error: GROQ_API_KEY not found.")
        return None

    client = Groq(api_key=api_key)

    # Platform-specific context for AI
    platform_context = {
        'instagram_feed': {
            'aspect': '1:1 square',
            'duration': '10 seconds',
            'style': 'balanced composition, center-focused',
            'text_position': 'bottom third',
            'best_motion': ['zoom_in', 'pan_right']
        },
        'instagram_story': {
            'aspect': '9:16 vertical',
            'duration': '10 seconds',
            'style': 'vertical emphasis, top-safe for profile',
            'text_position': 'middle or lower third',
            'best_motion': ['pan_up', 'zoom_in']
        },
        'instagram_reel': {
            'aspect': '9:16 vertical',
            'duration': '10 seconds',
            'style': 'dynamic, fast-paced, hook in first 2 seconds',
            'text_position': 'center or bottom with safe margins',
            'best_motion': ['zoom_in', 'pan_down', 'pan_right']
        },
        'facebook_feed': {
            'aspect': '4:5 vertical',
            'duration': '10 seconds',
            'style': 'slightly more text-friendly, community-focused',
            'text_position': 'bottom third',
            'best_motion': ['zoom_in', 'pan_left']
        },
        'facebook_story': {
            'aspect': '9:16 vertical',
            'duration': '10 seconds',
            'style': 'similar to Instagram story',
            'text_position': 'middle or lower third',
            'best_motion': ['pan_up', 'zoom_in']
        },
        'linkedin': {
            'aspect': '1:1 or 4:5',
            'duration': '10 seconds',
            'style': 'professional, clean, corporate aesthetic',
            'text_position': 'bottom third',
            'best_motion': ['pan_right', 'zoom_out']
        }
    }

    # Content variation strategies for multiple posts
    variation_strategies = [
        "focus on product quality and craftsmanship",
        "focus on emotional connection and family values", 
        "focus on urgency and limited-time appeal",
        "focus on social proof and community trust",
        "focus on innovation and modernity"
    ]
    
    current_strategy = variation_strategies[variation_index % len(variation_strategies)]
    platform_info = platform_context.get(platform, platform_context['instagram_feed'])

    # Build dynamic system prompt based on client sophistication
    system_prompt = f"""You are Maseer - Afghanistan's premier AI-driven media engine, architecting viral, zero-budget social media campaigns for Kabul's most ambitious brands.

CORE IDENTITY:
• 15+ years mastering Afghan consumer psychology and digital behavior patterns
• Pioneer of "Maseer Method": Maximum Reach, Minimum Spend (MRMS)
• Fluent in the visual language of Kabul's streets, markets, and digital spaces
• Expert in Persian/Dari neurolinguistic programming for immediate action triggers
• Specialist in platform-native content that feels organic, not advertorial

CULTURAL INTELLIGENCE:
• Afghan purchasing decisions are EMOTIONAL first, logical second (family honor, social status, hospitality reciprocity)
• "Nan-o-namak" (bread and salt) philosophy: Trust is currency, relationships are transactions
• Kabul's youth (18-35) are mobile-first, data-conscious, authenticity-hungry
• Seasonal awareness: Nowruz, Ramadan, Eid drive 70% of annual consumer spending
• Power words that bypass rational filters: "همین حالا", "فقط امروز", "ویژه شما", "ضمانت اصالت", "تحویل فوری"

ZERO-COST MARKETING ARSENAL:
• Pattern interrupts that stop thumb-scrolling in 0.8 seconds
• Color psychology leveraging Afghan aesthetic preferences (warm earth tones, gold accents, deep reds)
• Visual hierarchy that guides eye movement to CTA without explicit "Buy Now" buttons
• Social proof integration (crowd psychology, scarcity, FOMO)
• Storytelling that positions customer as hero, brand as guide

PLATFORM MASTERY - {platform.upper()}:
• Format: {platform_info['aspect']} | Duration: {platform_info['duration']}
• Visual Style: {platform_info['style']}
• Text Safe Zone: {platform_info['text_position']}
• Motion Psychology: Use {platform_info['best_motion'][0]} for intimacy, {platform_info['best_motion'][1]} for exploration

OUTPUT MANDATE:
Generate scroll-stopping, culturally-resonant, platform-native content that drives immediate action without paid promotion."""

    # Construct nuanced user prompt with all available data
    tone = client_data.get('content_tone', 'authentic and engaging')
    motion_pref = client_data.get('preferred_motion', platform_info['best_motion'][0])
    special_notes = client_data.get('special_notes', '')
    posting_freq = client_data.get('posting_schedule', 'weekly')
    
    # Industry-specific conversion triggers
    industry_hooks = {
        'Café & Restaurant': ['عطر غذای اصیل', 'طعم کابل', 'مهمان‌نوازی افغانی', 'سفره‌ی مخصوص'],
        'Consultancy': ['راهکار هوشمند', 'موفقیت تضمینی', 'بازنگری استراتژیک', 'رشد پایدار'],
        'Fashion': ['استایل منحصر‌به‌فرد', 'مد کابل', 'زیبایی اصیل', 'تخفیف ویژه'],
        'Technology': ['نوآوری افغان', 'راهکار دیجیتال', 'آینده‌ی هوشمند', 'تکنولوژی بومی'],
        'Healthcare': ['سلامت خانواده', 'درمان تخصصی', 'اعتماد و تجربه', 'مراقبت واقعی'],
        'Education': ['آینده‌ی فرزندان', 'یادگیری نوین', 'موفقیت تحصیلی', 'استعداد یابی']
    }
    
    industry = client_data['industry']
    hooks = industry_hooks.get(industry, ['کیفیت برتر', 'قیمت مناسب', 'تحویل سریع', 'اعتماد شما'])
    
    # Select hook based on variation index
    primary_hook = hooks[variation_index % len(hooks)]
    
    user_prompt = f"""Generate high-converting video content for:

BRAND DNA:
• Name: {client_data['brand_name']} ({client_data.get('local_name', '')})
• Industry: {industry}
• Location: {client_data.get('location', 'Kabul, Afghanistan')}
• Target: {client_data['target_audience']}
• Core Offer: {client_data['key_offerings']}
• Brand Colors: {client_data['primary_color']} (primary), {client_data['secondary_color']} (secondary)
• Voice: {tone}
• Strategic Focus: {current_strategy}
• Special Context: {special_notes}

PLATFORM SPECIFICATIONS:
• Platform: {platform}
• Format: {platform_info['aspect']}
• Visual Approach: {platform_info['style']}
• Recommended Motion: {motion_pref}

CONTENT VARIATION STRATEGY:
{current_strategy.capitalize()}. This is variation {variation_index + 1} in a {posting_freq} content series.

MANDATORY OUTPUT FORMAT (JSON):
{{
  "text": "Persian/Dari headline - 5-8 words maximum. Start with power word or number. Include implicit CTA. Use this hook: {primary_hook}. Kabul dialect preferred. No English.",
  "image_prompt": "Ultra-detailed English prompt for AI image generation. Include: {platform_info['style']}, professional photography, Afghan aesthetic, color palette {client_data['primary_color']} and {client_data['secondary_color']}, cinematic lighting, shallow depth of field, negative space for text overlay in {platform_info['text_position']}, 8k resolution, editorial composition, culturally authentic details, {current_strategy} mood. Avoid: cluttered backgrounds, western faces, generic stock photo look.",
  "motion": "{motion_pref}",
  "hashtags": ["کابل", "{client_data['brand_name'].replace(' ', '')}", "{industry.replace(' ', '')}", "مسیریابی", "برندینگ"],
  "engagement_hook": "One-sentence engagement prompt for caption (e.g., 'نظر شما چیست؟' or 'تگ دوستتان کنید')",
  "best_posting_time": "Based on Afghan social media usage patterns"
}}

CRITICAL RULES:
1. Text must feel native to Kabul, not translated
2. Image prompt must specify {platform_info['aspect']} composition
3. Motion must match {platform} viewing behavior
4. Colors must harmonize with brand palette
5. Content must align with {current_strategy}

Return ONLY valid JSON. No markdown, no explanations."""

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,  # Balance creativity with consistency
            max_tokens=800
        )

        response_data = json.loads(completion.choices[0].message.content)
        
        # Enrich response with metadata
        response_data['platform'] = platform
        response_data['variation_strategy'] = current_strategy
        response_data['brand_name'] = client_data['brand_name']
        
        return response_data

    except Exception as e:
        print(f"❌ Groq API Error for {client_data['brand_name']} ({platform}): {e}")
        return None


def generate_content_series(client_data, platforms=None, variations_per_platform=1):
    """
    Generate multiple content variations across platforms for a single client.
    
    Args:
        client_data: Brand information dictionary
        platforms: List of platforms (defaults to client_data['platforms'])
        variations_per_platform: Number of variations per platform
    
    Returns:
        List of content dictionaries
    """
    if platforms is None:
        platforms = client_data.get('platforms', ['instagram_feed'])
    
    all_content = []
    
    for platform in platforms:
        for variation in range(variations_per_platform):
            content = get_content_from_groq(client_data, platform, variation)
            if content:
                all_content.append(content)
    
    return all_content
