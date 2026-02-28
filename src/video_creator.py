import os
from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, ColorClip, concatenate_videoclips
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image as PILImage


def prepare_persian_text(text):
    """Reshape and reorder Persian/Arabic text for proper RTL display."""
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        return get_display(reshaped_text)
    except Exception as e:
        print(f"   Warning: Text reshaping error: {e}")
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
    ]
    
    for font in font_candidates:
        try:
            test_clip = TextClip("تست", fontsize=20, font=font)
            test_clip.close()
            return font
        except:
            continue
    
    return 'DejaVu-Sans'


def create_animated_logo(logo_path, video_width, video_height, overlay_height, overlay_y, duration):
    """Create logo with slide-in animation from right."""
    try:
        if not logo_path or not os.path.exists(logo_path):
            return None

        logo_img = PILImage.open(logo_path)
        
        max_logo_height = int(overlay_height * 0.65)
        aspect_ratio = logo_img.width / logo_img.height
        logo_height = max_logo_height
        logo_width = int(logo_height * aspect_ratio)
        
        max_logo_width = int(video_width * 0.15)
        if logo_width > max_logo_width:
            logo_width = max_logo_width
            logo_height = int(logo_width / aspect_ratio)

        # Final position (right side of stripe)
        padding_right = 50
        final_x = video_width - logo_width - padding_right
        final_y = overlay_y + (overlay_height - logo_height) // 2
        
        # Start position (off-screen to the right)
        start_x = video_width + 50

        # Create animated logo with slide-in effect
        logo_clip = (ImageClip(logo_path)
                    .set_duration(duration)
                    .resize((logo_width, logo_height))
                    .set_position(lambda t: (
                        start_x + (final_x - start_x) * min(t / 1.5, 1),  # Slide in over 1.5 seconds
                        final_y
                    ))
                    .set_opacity(lambda t: min(t * 2, 1))  # Fade in
                    )
        
        return logo_clip
    except Exception as e:
        print(f"   Warning: Logo processing error: {e}")
        return None


def create_advanced_video_reel(image_path, text, output_path, client_data, motion='zoom_in'):
    """Creates a premium 10-second video reel with dynamic animations."""
    try:
        duration = 10
        fps = 20  # Higher FPS for smoother motion
        display_text = prepare_persian_text(text)
        
        persian_font = get_available_persian_font()
        print(f"   - Using font: {persian_font}")

        # Load background image with dynamic motion
        bg_clip = ImageClip(image_path).set_duration(duration)
        
        # Enhanced zoom + pan motion (Ken Burns effect)
        if motion == 'zoom_in':
            # Start zoomed out, slowly zoom in while panning slightly
            bg_clip = bg_clip.resize(lambda t: 1 + 0.08 * (t / duration))  # 8% zoom over 10s
            # Add subtle pan
            bg_clip = bg_clip.set_position(lambda t: (
                -bg_clip.w * 0.02 * (t / duration),  # Pan right slowly
                'center'
            ))
        elif motion == 'pan_right':
            bg_clip = bg_clip.set_position(lambda t: (
                -bg_clip.w * 0.15 * (t / duration),
                'center'
            ))
        elif motion == 'pan_left':
            bg_clip = bg_clip.set_position(lambda t: (
                bg_clip.w * 0.15 * (t / duration) - bg_clip.w * 0.15,
                'center'
            ))
        else:
            # Default: slow zoom with subtle pan
            bg_clip = bg_clip.resize(lambda t: 1 + 0.06 * (t / duration))

        primary_color = client_data.get('primary_color', '#D32F2F')
        secondary_color = client_data.get('secondary_color', '#FFC107')

        # Dynamic font sizing
        text_length = len(text)
        if text_length <= 15:
            fontsize = 90
        elif text_length <= 25:
            fontsize = 75
        else:
            fontsize = 60

        txt_width = int(bg_clip.w * 0.60)  # Leave room for logo

        # Create main text with animation
        txt_clip = (TextClip(
            display_text,
            fontsize=fontsize,
            color='white',
            font=persian_font,
            method='caption',
            size=(txt_width, None),
            align='center',
            interline=-8
        )
        .set_duration(duration)
        .set_start(0.5)  # Slight delay
        )

        # Animate text: slide up + fade in
        text_final_y = 0  # Will be calculated relative to overlay
        txt_clip = txt_clip.set_position(lambda t: (
            'center',
            50 + max(0, 30 - 30 * min(t / 1.0, 1))  # Slide up over 1 second
        )).set_opacity(lambda t: min(t * 2, 1))  # Fade in

        # Get text dimensions for overlay
        txt_w, txt_h = txt_clip.size
        padding = 40
        overlay_height = max(txt_h + (padding * 2), int(bg_clip.h * 0.18))

        # Create animated color stripe (slide up from bottom)
        overlay_y_final = bg_clip.h - overlay_height - 60
        overlay_y_start = bg_clip.h + 20

        overlay = (ColorClip(
            size=(bg_clip.w, overlay_height),
            color=hex_to_rgb(primary_color)
        )
        .set_duration(duration)
        .set_opacity(0.90)
        .set_position(lambda t: (
            'center',
            overlay_y_start + (overlay_y_final - overlay_y_start) * min(t / 0.8, 1)  # Slide up in 0.8s
        ))
        )

        # Create shadow for text (offset slightly)
        shadow_clip = (TextClip(
            display_text,
            fontsize=fontsize,
            color='black',
            font=persian_font,
            method='caption',
            size=(txt_width, None),
            align='center',
            interline=-8
        )
        .set_duration(duration)
        .set_start(0.5)
        .set_opacity(0.4)
        )

        # Position text and shadow on the stripe (left side, leaving room for logo)
        text_x = int(bg_clip.w * 0.05)
        
        def get_text_y(t):
            # Text sits on the overlay
            overlay_y = overlay_y_start + (overlay_y_final - overlay_y_start) * min(t / 0.8, 1)
            return overlay_y + (overlay_height - txt_h) // 2

        txt_clip = txt_clip.set_position(lambda t: (text_x, get_text_y(t)))
        shadow_clip = shadow_clip.set_position(lambda t: (text_x + 4, get_text_y(t) + 4))

        # Add top gradient for visual polish (fades in)
        gradient_height = 200
        top_gradient = (ColorClip(
            size=(bg_clip.w, gradient_height),
            color=(0, 0, 0)
        )
        .set_duration(duration)
        .set_opacity(lambda t: 0.3 * min(t, 1))  # Fade to 30%
        .set_position(('center', 0))
        )

        # Build composition layers (bottom to top)
        layers = [
            bg_clip,           # Animated background
            top_gradient,      # Top vignette
            overlay,           # Animated color stripe
            shadow_clip,       # Text shadow
            txt_clip,          # Main text
        ]

        # Add animated logo
        logo_path = client_data.get('logo_path')
        if logo_path and os.path.exists(logo_path):
            logo_clip = create_animated_logo(
                logo_path, bg_clip.w, bg_clip.h, overlay_height, 
                overlay_y_final, duration
            )
            if logo_clip:
                layers.append(logo_clip)

        # Compose final video
        final_video = CompositeVideoClip(layers, size=bg_clip.size)

        # Export with high quality settings
        final_video.write_videofile(
            output_path,
            fps=fps,           # 20 FPS for smooth motion
            codec='libx264',
            audio=False,
            logger=None,
            threads=4,
            preset='medium',
            bitrate='5000k'    # Higher quality
        )

        # Clean up
        final_video.close()
        for layer in layers:
            try:
                layer.close()
            except:
                pass

        return True

    except Exception as e:
        print(f"❌ Video Error: {e}")
        import traceback
        traceback.print_exc()
        return False
