import os
from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, ColorClip
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image as PILImage


def prepare_persian_text(text):
    """Reshape and reorder Persian/Arabic text for proper RTL display."""
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        return get_display(reshaped_text)
    except Exception as e:
        print(f"   ⚠️ Text reshaping error: {e}")
        return text


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def get_available_persian_font():
    """Find an available font that supports Persian text on Linux."""
    font_candidates = [
        'DejaVu-Sans',
        'DejaVu-Sans-Bold',
        'FreeSans',
        'FreeSans-Bold',
        'Noto-Sans-Arabic',
        'Noto-Naskh-Arabic',
        'Amiri',
        'Arial-Unicode-MS',
        'Arial',
    ]
    
    for font in font_candidates:
        try:
            test_clip = TextClip("تست", fontsize=20, font=font)
            test_clip.close()
            return font
        except:
            continue
    
    return 'DejaVu-Sans'


def create_logo_clip_on_stripe(logo_path, video_width, video_height, overlay_height, overlay_y, duration):
    """Creates a logo clip positioned at the RIGHT END of the bottom color stripe."""
    try:
        if not logo_path or not os.path.exists(logo_path):
            return None

        logo_img = PILImage.open(logo_path)
        
        max_logo_height = int(overlay_height * 0.7)
        aspect_ratio = logo_img.width / logo_img.height
        logo_height = max_logo_height
        logo_width = int(logo_height * aspect_ratio)
        
        max_logo_width = int(video_width * 0.18)
        if logo_width > max_logo_width:
            logo_width = max_logo_width
            logo_height = int(logo_width / aspect_ratio)

        logo_clip = ImageClip(logo_path).set_duration(duration)
        logo_clip = logo_clip.resize((logo_width, logo_height))

        padding_right = 40
        logo_x = video_width - logo_width - padding_right
        logo_y = overlay_y + (overlay_height - logo_height) // 2
        
        logo_clip = logo_clip.set_position((logo_x, logo_y))

        return logo_clip
    except Exception as e:
        print(f"   ⚠️ Logo processing error: {e}")
        return None


def create_advanced_video_reel(image_path, text, output_path, client_data, motion='zoom_in'):
    """Creates a premium 10-second video reel with logo on bottom-right stripe."""
    try:
        duration = 10
        display_text = prepare_persian_text(text)
        
        persian_font = get_available_persian_font()
        print(f"   - Using font: {persian_font}")

        clip = ImageClip(image_path).set_duration(duration)
        if motion == 'zoom_in':
            clip = clip.resize(lambda t: 1 + 0.04 * (t / duration))
        elif motion == 'pan_right':
            clip = clip.set_position(lambda t: (-clip.w * 0.1 * (t / duration), 'center'))

        primary_color = client_data.get('primary_color', '#FFFFFF')
        secondary_color = client_data.get('secondary_color', '#000000')

        text_length = len(text)
        if text_length <= 15:
            fontsize = 85
        elif text_length <= 25:
            fontsize = 70
        else:
            fontsize = 55

        txt_width = int(clip.w * 0.65)

        txt_clip = TextClip(
            display_text,
            fontsize=fontsize,
            color='white',
            font=persian_font,
            method='caption',
            size=(txt_width, None),
            align='center',
            interline=-10
        ).set_duration(duration)

        txt_w, txt_h = txt_clip.size
        padding = 35
        overlay_height = txt_h + (padding * 2)
        
        min_overlay_height = int(clip.h * 0.15)
        if overlay_height < min_overlay_height:
            overlay_height = min_overlay_height

        overlay = ColorClip(
            size=(clip.w, overlay_height),
            color=hex_to_rgb(primary_color)
        ).set_duration(duration).set_opacity(0.85)

        overlay_y = clip.h - overlay_height - 80
        overlay = overlay.set_position(('center', overlay_y))

        text_x = int(clip.w * 0.05)
        txt_clip = txt_clip.set_position((text_x, overlay_y + (overlay_height - txt_h) // 2))

        shadow_clip = TextClip(
            display_text,
            fontsize=fontsize,
            color='black',
            font=persian_font,
            method='caption',
            size=(txt_width, None),
            align='center',
            interline=-10
        ).set_duration(duration).set_opacity(0.5)

        shadow_clip = shadow_clip.set_position(
            (text_x + 3, overlay_y + (overlay_height - txt_h) // 2 + 3)
        )

        gradient_height = 150
        top_gradient = ColorClip(
            size=(clip.w, gradient_height),
            color=(0, 0, 0)
        ).set_duration(duration).set_opacity(0.2)

        top_gradient = top_gradient.set_position(('center', 0))

        txt_clip = txt_clip.set_start(0.3).fadein(0.6)
        overlay = overlay.set_start(0.3).fadein(0.6)
        shadow_clip = shadow_clip.set_start(0.3).fadein(0.6)

        layers = [
            clip,
            top_gradient,
            shadow_clip,
            overlay,
            txt_clip
        ]

        logo_path = client_data.get('logo_path')
        if logo_path:
            logo_clip = create_logo_clip_on_stripe(
                logo_path, clip.w, clip.h, overlay_height, overlay_y, duration
            )
            if logo_clip:
                logo_clip = logo_clip.set_start(0.3).fadein(0.6)
                layers.append(logo_clip)

        final_video = CompositeVideoClip(layers, size=clip.size)

        final_video.write_videofile(
            output_path,
            fps=30,
            codec='libx264',
            audio=False,
            logger=None,
            threads=4,
            preset='medium'
        )

        return True

    except Exception as e:
        print(f"❌ Video Error: {e}")
        return False
