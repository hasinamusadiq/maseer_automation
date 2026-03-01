import os
import json
from groq import Groq
from datetime import datetime


# Campaign configurations with specific styles and languages
CAMPAIGNS = {
    'morning': {
        'name': 'Morning Motivation',
        'time': '6:00 AM',
        'language': 'Persian/Dari',
        'style': 'Celestial Minimalism',
        'energy': 'Calm, ethereal, uplifting',
        'visual_elements': [
            'Thin elegant Nastaʿlīq calligraphy fading like morning mist',
            'Deep navy-to-gold gradient background',
            'Floating Zarrin geometric shapes (simplified sun, 2D line-art mountain)',
            'Parallax motion effect',
            'Vastness and fantasy atmosphere'
        ],
        'color_psychology': 'Navy (#1e3a5f) evokes trust and depth, gold (#FFD700) stimulates optimism and premium perception',
        'motion': 'slow_parallax',
        'font_style': 'Nastaʿlīq script, thin weight, elegant',
        'tone': 'inspirational, peaceful, awakening'
    },
    'midday': {
        'name': 'General Information',
        'time': '12:00 PM',
        'language': 'Pashto',
        'style': 'Organic Hujra Aesthetic',
        'energy': 'Cordial, grounded, trustworthy',
        'visual_elements': [
            'Hand-drawn textures resembling linen or craft paper',
            'Warm earthy tones (terracotta, sand, olive)',
            'Soft rounded Pashto typography',
            'Organic wipes (paint strokes, rustling leaves)',
            'Hujra (guest house) warmth and hospitality'
        ],
        'color_psychology': 'Terracotta (#D97706) creates warmth, olive (#65A30D) suggests growth and tradition',
        'motion': 'organic_wipe',
        'font_style': 'Rounded Pashto, soft edges, approachable',
        'tone': 'informative, welcoming, community-focused'
    },
    'evening': {
        'name': 'Service Promotion',
        'time': '6:00 PM',
        'language': 'Persian/Dari',
        'style': 'Modern Classic Detailed',
        'energy': 'Professional, inspiring, authoritative',
        'visual_elements': [
            'High-resolution product/service photography',
            'Crisp sans-serif Dari fonts for readability',
            'Detail callouts with animated lines',
            '3D rotation of featured elements',
            'Kinetic typography for CTA'
        ],
        'color_psychology': 'Deep purple (#581C87) conveys luxury, amber (#F59E0B) drives action and urgency',
        'motion': 'kinetic_detail',
        'font_style': 'Modern sans-serif, bold weights, high contrast',
        'tone': 'persuasive, confident, premium'
    },
    'night': {
        'name': 'Brand Awareness',
        'time': '12:00 AM',
        'language': 'English',
        'style': 'Tactile Stop-Motion',
        'energy': 'Bold, artistic, memorable',
        'visual_elements': [
            'Stop-motion animation with real-world objects',
            'Brand logo physically assembled by hand-moved elements',
            'Paper-cutout animation for brand storytelling',
            '12fps stuttery frame rate',
            'Tactile, human feel against digital smoothness'
        ],
        'color_psychology': 'Midnight blue (#0F172A) creates sophistication, neon accents (#EC4899) for modern edge',
        'motion': 'stop_motion',
        'font_style': 'Bold English, geometric, contemporary',
        'tone': 'bold, artistic, unforgettable'
    },
    'sample': {
        'name': 'Undeniable Sample',
        'time': 'IMMEDIATE',
        'language': 'Persian/Dari',
        'style': 'Maximum Impact Fusion',
        'energy': 'Stunning, undeniable, conversion-focused',
        'visual_elements': [
            'Cinematic lighting with dramatic shadows',
            'Brand colors amplified to maximum saturation',
            'Logo reveal with particle effects',
            'Industry-specific visual metaphors',
            'Parallax + kinetic hybrid motion'
        ],
        'color_psychology': 'Primary color at 120% saturation for brand recognition, gold accents for perceived value',
        'motion': 'cinematic_reveal',
        'font_style': 'Hybrid: Nastaʿlīq elegance + modern boldness',
        'tone': 'irresistible, premium, must-subscribe'
    }
}

# Industry-specific visual metaphors to avoid overlap
INDUSTRY_METAPHORS = {
    'Jewelry & Gold': {
        'morning': 'Golden sunrise reflecting off polished gemstones, delicate filigree patterns emerging from mist',
        'midday': 'Artisan hands crafting on traditional mat, raw gold nuggets, heritage tools',
        'evening': 'Dramatic lighting on statement pieces, 3D rotation of intricate designs, sparkle effects',
        'night': 'Stop-motion assembly of necklace from scattered elements, paper-cutout luxury box opening',
        'sample': 'Cinematic gold particles forming brand logo, dramatic gemstone refractions, heritage meets modern'
    },
    'Café & Restaurant': {
        'morning': 'Steam rising from traditional chai, golden morning light through lattice windows',
        'midday': 'Hand-drawn spices and herbs, organic textures of bread, communal dining atmosphere',
        'evening': 'Sizzling dishes with detail callouts, 3D rotation of signature meals, appetite-triggering close-ups',
        'night': 'Stop-motion table setting, paper-cutout ingredients dancing, tactile food preparation',
        'sample': 'Cinematic steam, dramatic plating, heritage recipes with modern presentation, irresistible aroma visualization'
    },
    'Fashion & Clothing': {
        'morning': 'Elegant fabrics catching dawn light, delicate embroidery details, ethereal draping',
        'midday': 'Natural dyes and organic cotton textures, artisan weaving processes, earthy elegance',
        'evening': 'High-fashion silhouettes with kinetic typography, 3D accessory rotations, trend-setting poses',
        'night': 'Stop-motion outfit assembly, paper-cutout fashion illustrations, tactile fabric manipulation',
        'sample': 'Cinematic model with dramatic lighting, fabric in motion, brand colors dominating frame, must-have energy'
    },
    'Technology & IT': {
        'morning': 'Clean code interfaces with celestial gradients, dawn breaking over digital horizon',
        'midday': 'Organic circuit patterns, hand-sketched wireframes, human-centered tech',
        'evening': '3D device rotations with spec callouts, kinetic feature highlights, futuristic professionalism',
        'night': 'Stop-motion gadget assembly, paper-cutout innovation story, tactile hardware elements',
        'sample': 'Cinematic tech aesthetic, holographic interfaces, brand colors in neon glow, cutting-edge positioning'
    },
    'Healthcare & Medical': {
        'morning': 'Gentle healing light, traditional herbal wisdom, serene wellness atmosphere',
        'midday': 'Organic medicine preparation, trustworthy hands, community care',
        'evening': 'Advanced equipment with detail callouts, professional expertise, 3D anatomical precision',
        'night': 'Stop-motion wellness journey, paper-cutout health transformation, tactile care elements',
        'sample': 'Cinematic trust and expertise, dramatic healing imagery, brand as premium care provider'
    },
    'Education & Training': {
        'morning': 'Dawn of knowledge, illuminated manuscripts, awakening curiosity',
        'midday': 'Traditional learning circles, organic growth metaphors, community education',
        'evening': 'Modern facilities with feature highlights, 3D learning tools, success-oriented',
        'night': 'Stop-motion knowledge building, paper-cutout graduation journey, tactile achievement',
        'sample': 'Cinematic transformation, dramatic before/after, brand as gateway to success'
    },
    'Real Estate': {
        'morning': 'Golden hour architecture, celestial blueprints, dream homes emerging',
        'midday': 'Organic community planning, trustworthy foundations, earthy materials',
        'evening': 'Luxury properties with detail callouts, 3D spatial rotations, investment potential',
        'night': 'Stop-motion home assembly, paper-cutout neighborhood, tactile architectural elements',
        'sample': 'Cinematic luxury living, dramatic spaces, brand as status symbol'
    },
    'Automotive': {
        'morning': 'Chrome catching dawn light, celestial speed, journey beginning',
        'midday': 'Organic road textures, trustworthy engineering, heritage of travel',
        'evening': 'Vehicle details with spec callouts, 3D feature rotations, performance focus',
        'night': 'Stop-motion car assembly, paper-cutout journey story, tactile mechanical elements',
        'sample': 'Cinematic power and prestige, dramatic motion, brand as aspiration'
    },
    'Beauty & Cosmetics': {
        'morning': 'Dew-kissed skin, ethereal glow, natural awakening',
        'midday': 'Organic ingredients, hand-crafted beauty, natural textures',
        'evening': 'Product details with benefit callouts, 3D packaging, glamour focus',
        'night': 'Stop-motion transformation, paper-cutout beauty ritual, tactile luxury',
        'sample': 'Cinematic allure, dramatic before/after, brand as essential beauty'
    },
    'Construction & Materials': {
        'morning': 'Foundations in dawn light, solid structures emerging, strength beginning',
        'midday': 'Organic materials, trustworthy craftsmanship, earthy reliability',
        'evening': 'Quality details with spec callouts, 3D material rotations, durability focus',
        'night': 'Stop-motion building assembly, paper-cutout construction, tactile strength',
        'sample': 'Cinematic solidity, dramatic scale, brand as foundation of success'
    },
    'Consultancy & Services': {
        'morning': 'Strategic dawn, clarity emerging, wisdom illumination',
        'midday': 'Organic relationship building, trustworthy counsel, community wisdom',
        'evening': 'Results with detail callouts, 3D success metrics, expertise demonstration',
        'night': 'Stop-motion solution building, paper-cutout partnership, tactile progress',
        'sample': 'Cinematic success, dramatic transformation, brand as essential partner'
    },
    'Retail & Shopping': {
        'morning': 'Golden displays, celestial merchandise, shopping awakening',
        'midday': 'Organic market atmosphere, trustworthy quality, community commerce',
        'evening': 'Products with feature callouts, 3D showcase rotations, deal urgency',
        'night': 'Stop-motion display assembly, paper-cutout shopping journey, tactile selection',
        'sample': 'Cinematic desire, dramatic must-have energy, brand as shopping destination'
    },
    'Travel & Hospitality': {
        'morning': 'Dawn destinations, celestial journeys, adventure calling',
        'midday': 'Organic cultural experiences, trustworthy guidance, authentic hospitality',
        'evening': 'Destinations with detail callouts, 3D experience previews, escape focus',
        'night': 'Stop-motion journey assembly, paper-cutout adventure, tactile wanderlust',
        'sample': 'Cinematic escape, dramatic destinations, brand as passport to experience'
    },
    'Agriculture': {
        'morning': 'Golden harvest dawn, celestial growth, nature awakening',
        'midday': 'Organic farming traditions, trustworthy earth, community sustenance',
        'evening': 'Produce with quality callouts, 3D growth cycles, abundance focus',
        'night': 'Stop-motion harvest assembly, paper-cutout cultivation, tactile nature',
        'sample': 'Cinematic abundance, dramatic growth, brand as nurturer of life'
    },
    'Handicrafts': {
        'morning': 'Artisan dawn, celestial craftsmanship, tradition awakening',
        'midday': 'Organic creation process, trustworthy heritage, community artistry',
        'evening': 'Craft details with technique callouts, 3D artistry rotations, mastery focus',
        'night': 'Stop-motion craft assembly, paper-cutout creation story, tactile tradition',
        'sample': 'Cinematic artistry, dramatic craftsmanship, brand as keeper of heritage'
    }
}


def get_campaign_config(campaign_type='morning'):
    """Get configuration for specific campaign type."""
    return CAMPAIGNS.get(campaign_type, CAMPAIGNS['morning'])


def get_industry_metaphor(industry, campaign_type):
    """Get industry-specific visual metaphor for campaign."""
    industry_data = INDUSTRY_METAPHORS.get(industry, INDUSTRY_METAPHORS['Retail & Shopping'])
    return industry_data.get(campaign_type, industry_data['morning'])


def get_content_for_campaign(client_data, campaign_type='morning', is_sample=False):
    """
    Generate content optimized for specific campaign with industry metaphors.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY not found")
        return None

    client = Groq(api_key=api_key)
    
    # Get campaign configuration
    campaign = get_campaign_config('sample' if is_sample else campaign_type)
    industry = client_data.get('industry', 'Retail & Shopping')
    metaphor = get_industry_metaphor(industry, 'sample' if is_sample else campaign_type)
    
    # Language-specific instructions
    lang_instructions = {
        'Persian/Dari': 'Use elegant Persian/Dari (Farsi). Nastaʿlīq script style. Kabul dialect preferred.',
        'Pashto': 'Use clear Pashto. Traditional script. Peshawar/Kabul dialect balance.',
        'English': 'Use bold, concise English. Modern sans-serif feel. Impact-focused.'
    }
    
    # Build system prompt with campaign specifics
    system_prompt = f"""You are Maseer Media's elite AI creative director, specializing in Afghan market psychology and Meta-optimized content.

CAMPAIGN BRIEF:
• Type: {campaign['name']} ({campaign['time']})
• Language: {campaign['language']}
• Style: {campaign['style']}
• Energy: {campaign['energy']}
• Visual Direction: {' | '.join(campaign['visual_elements'])}
• Color Psychology: {campaign['color_psychology']}
• Typography: {campaign['font_style']}

INDUSTRY CONTEXT:
• Sector: {industry}
• Visual Metaphor: {metaphor}

CRITICAL RULES:
1. Text MUST be in {campaign['language']} - {lang_instructions[campaign['language']]}
2. Maximum 6 words for headlines (sample: 4 words for impact)
3. Use power words that trigger Afghan consumer psychology
4. Avoid generic stock photo descriptions
5. Every visual element must serve the {campaign['energy']} energy
6. Color usage must follow: {campaign['color_psychology']}"""

    # Brand colors with psychology amplification
    primary = client_data.get('primary_color', '#6B21A8')
    secondary = client_data.get('secondary_color', '#EAB308')
    
    # For sample, amplify colors
    if is_sample:
        color_instruction = f"AMPLIFY brand colors: Primary {primary} at maximum saturation, Secondary {secondary} for gold accents. Create undeniable visual impact."
    else:
        color_instruction = f"Use Primary {primary} and Secondary {secondary} following campaign color psychology."

    user_prompt = f"""Create content for {client_data['brand_name']} ({industry})

BRAND DNA:
• Local Name: {client_data.get('local_name', client_data['brand_name'])}
• Offerings: {client_data.get('key_offerings', 'Premium products/services')}
• Unique Value: {client_data.get('unique_value', 'Quality and trust')}
• Audience: {client_data.get('target_audience', 'General Afghan market')}

VISUAL METAPHOR TO DEPLOY:
{metaphor}

COLOR STRATEGY:
{color_instruction}

OUTPUT JSON:
{{
  "headline": "6 words max, {campaign['language']}, {campaign['tone']}, power words",
  "subheadline": "Optional 4-word supporting line",
  "image_prompt": "Ultra-detailed 1224x1536 composition: {campaign['style']}, {metaphor}, {campaign['font_style']}, colors {primary}/{secondary}, {campaign['energy']}, Meta-optimized 4:5, no text in image, cinematic lighting, 8K detail, Afghan cultural authenticity",
  "motion_style": "{campaign['motion']}",
  "cta_text": "2-word call-to-action in {campaign['language']}",
  "engagement_hook": "Question or statement for caption",
  "color_usage": "Specific how {primary} and {secondary} are used",
  "psychology_trigger": "Primary emotional trigger used"
}}

Return valid JSON only."""

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.75 if is_sample else 0.7,  # Higher creativity for sample
            max_tokens=900
        )

        content = json.loads(completion.choices[0].message.content)
        
        # Enrich with metadata
        content['campaign_type'] = 'sample' if is_sample else campaign_type
        content['campaign_name'] = campaign['name']
        content['language'] = campaign['language']
        content['industry'] = industry
        content['brand_name'] = client_data['brand_name']
        content['is_sample'] = is_sample
        
        return content

    except Exception as e:
        print(f"❌ Content generation error: {e}")
        return None


def generate_all_campaigns(client_data):
    """Generate content for all 4 campaigns + sample if needed."""
    campaigns = {}
    
    # Generate sample if requested
    if client_data.get('request_sample') and not client_data.get('sample_generated'):
        campaigns['sample'] = get_content_for_campaign(client_data, is_sample=True)
    
    # Generate all daily campaigns
    for campaign_type in ['morning', 'midday', 'evening', 'night']:
        campaigns[campaign_type] = get_content_for_campaign(client_data, campaign_type)
    
    return campaigns
