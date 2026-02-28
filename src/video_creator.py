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
                        start_x + (final_x - start_x) * min(t / 1.5, 1),
                        final_y
                    ))
                    )
        
        # Use fadein instead of lambda opacity
        logo_clip = logo_clip.fadein(0.5)
        
        return logo_clip
    except Exception as e:
        print(f"   Warning: Logo processing error: {e}")
        return None


def create_advanced_video_reel(image_path, text, output_path, client_data, motion='zoom_in'):
    """
    Creates a premium 10-second video reel with dramatic Ken Burns animations.
    
    Animation Specifications:
    - Duration: 10 seconds
    - FPS: 30 (smooth motion, standard for video)
    - Zoom: 15-25% scale increase over duration
    - Pan: 10-20% of image width/height
    - Easing: Smooth interpolation for natural motion
    """
    try:
        duration = 10
        fps = 30  # Increased from 20 for smoother motion perception
        display_text = prepare_persian_text(text)
        
        persian_font = get_available_persian_font()
        print(f"   - Using font: {persian_font}")

        # Load background image
        bg_clip = ImageClip(image_path).set_duration(duration)
        
        # Calculate dimensions for animation math
        img_w, img_h = bg_clip.size
        target_w, target_h = 1920, 1080  # Standard 1080p output
        
        # Ensure image covers the frame with room to move
        base_scale = max(target_w / img_w, target_h / img_h)
        
        # ============================================================
        # DRAMATIC KEN BURNS EFFECT CONFIGURATION
        # ============================================================
        
        if motion == 'zoom_in':
            # Start: Slightly zoomed out (95%), End: Zoomed in (125%)
            # This creates a dramatic 30% scale change over 10 seconds
            # Movement: Slow pan from left to center while zooming
            def calc_transform(t):
                progress = t / duration
                # Scale: 0.95 -> 1.25 (30% zoom)
                scale = 0.95 + (0.30 * progress)
                # Pan: Start 5% left, end centered
                x_offset = -img_w * 0.05 * (1 - progress)
                y_offset = -img_h * 0.02 * progress  # Slight vertical drift
                return scale, x_offset, y_offset
                
        elif motion == 'zoom_out':
            # Reverse: Start zoomed in, pull back to reveal context
            def calc_transform(t):
                progress = t / duration
                scale = 1.25 - (0.30 * progress)  # 1.25 -> 0.95
                x_offset = -img_w * 0.05 * progress
                y_offset = -img_h * 0.02 * (1 - progress)
                return scale, x_offset, y_offset
                
        elif motion == 'pan_right':
            # Dramatic rightward pan with subtle zoom
            def calc_transform(t):
                progress = t / duration
                scale = 1.0 + (0.15 * progress)  # 15% zoom
                # Pan from left to right (20% of image width)
                x_offset = -img_w * 0.20 * progress
                y_offset = 0
                return scale, x_offset, y_offset
                
        elif motion == 'pan_left':
            # Dramatic leftward pan with subtle zoom
            def calc_transform(t):
                progress = t / duration
                scale = 1.0 + (0.15 * progress)
                x_offset = img_w * 0.20 * progress - img_w * 0.20
                y_offset = 0
                return scale, x_offset, y_offset
                
        elif motion == 'pan_up':
            # Vertical pan upward with zoom
            def calc_transform(t):
                progress = t / duration
                scale = 1.0 + (0.15 * progress)
                x_offset = 0
                y_offset = -img_h * 0.15 * progress
                return scale, x_offset, y_offset
                
        elif motion == 'pan_down':
            # Vertical pan downward with zoom
            def calc_transform(t):
                progress = t / duration
                scale = 1.0 + (0.15 * progress)
                x_offset = 0
                y_offset = img_h * 0.15 * progress - img_h * 0.15
                return scale, x_offset, y_offset
                
        else:  # default: subtle zoom_in
            def calc_transform(t):
                progress = t / duration
                scale = 1.0 + (0.20 * progress)
                x_offset = -img_w * 0.03 * progress
                y_offset = 0
                return scale, x_offset, y_offset

        # Apply the transformation with smooth easing
        def ease_in_out_quad(t):
            """Smooth easing function for natural motion feel"""
            if t < 0.5:
                return 2 * t * t
            else:
                return 1 - pow(-2 * t + 2, 2) / 2

        def get_frame_position(t):
            progress = ease_in_out_quad(t / duration)
            scale, x_off, y_off = calc_transform(t)
            
            # Calculate scaled dimensions
            new_w = img_w * scale * base_scale
            new_h = img_h * scale * base_scale
            
            # Center the image and apply offset
            x = (target_w - new_w) / 2 + x_off * base_scale * scale
            y = (target_h - new_h) / 2 + y_off * base_scale * scale
            
            return x, y

        def get_frame_size(t):
            scale, _, _ = calc_transform(t)
            return img_w * scale * base_scale, img_h * scale * base_scale

        # Apply dynamic positioning and sizing
        bg_clip = bg_clip.set_position(get_frame_position)
        bg_clip = bg_clip.resize(get_frame_size)

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

        txt_width = int(target_w * 0.60)

        # Calculate overlay dimensions first
        temp_text = TextClip(
            display_text,
            fontsize=fontsize,
            color='white',
            font=persian_font,
            method='caption',
            size=(txt_width, None),
            align='center',
            interline=-8
        )
        txt_w, txt_h = temp_text.size
        temp_text.close()
        
        padding = 40
        overlay_height = max(txt_h + (padding * 2), int(target_h * 0.18))
        overlay_y_final = target_h - overlay_height - 60

        # Create main text with slide-up animation
        text_final_y = overlay_y_final + (overlay_height - txt_h) // 2
        text_start_y = text_final_y + 50  # Start 50px lower for more dramatic entrance

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
        .set_start(0.3)  # Slightly earlier start
        .set_position(lambda t: (
            int(target_w * 0.05),
            text_start_y + (text_final_y - text_start_y) * min(max((t - 0.3) / 0.8, 0), 1)
        ))
        )
        
        # Fade in text
        txt_clip = txt_clip.fadein(0.4)

        # Create shadow for text
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
        .set_start(0.3)
        .set_position(lambda t: (
            int(target_w * 0.05) + 4,
            (text_start_y + (text_final_y - text_start_y) * min(max((t - 0.3) / 0.8, 0), 1)) + 4
        ))
        )
        shadow_clip = shadow_clip.set_opacity(0.4)
        shadow_clip = shadow_clip.fadein(0.4)

        # Create animated color stripe (slide up from bottom)
        overlay_y_start = target_h + 20

        overlay = (ColorClip(
            size=(target_w, overlay_height),
            color=hex_to_rgb(primary_color)
        )
        .set_duration(duration)
        .set_opacity(0.90)
        .set_position(lambda t: (
            'center',
            overlay_y_start + (overlay_y_final - overlay_y_start) * min(t / 0.6, 1)
        ))
        )

        # Add top gradient for visual polish
        gradient_height = 200
        top_gradient = (ColorClip(
            size=(target_w, gradient_height),
            color=(0, 0, 0)
        )
        .set_duration(duration)
        .set_opacity(0.3)
        .set_position(('center', 0))
        )
        
        # Fade in gradient
        top_gradient = top_gradient.fadein(0.5)

        # Build composition layers (bottom to top)
        layers = [
            bg_clip,
            top_gradient,
            overlay,
            shadow_clip,
            txt_clip,
        ]

        # Add animated logo
        logo_path = client_data.get('logo_path')
        if logo_path and os.path.exists(logo_path):
            logo_clip = create_animated_logo(
                logo_path, target_w, target_h, overlay_height, 
                overlay_y_final, duration
            )
            if logo_clip:
                layers.append(logo_clip)

        # Compose final video with fixed output size
        final_video = CompositeVideoClip(layers, size=(target_w, target_h))

        # Export with high quality settings
        final_video.write_videofile(
            output_path,
            fps=fps,
            codec='libx264',
            audio=False,
            logger=None,
            threads=4,
            preset='medium',
            bitrate='8000k'  # Increased bitrate for sharper motion
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
