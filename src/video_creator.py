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


def get_platform_specs(platform='instagram_feed'):
    """
    Get optimal video specifications for Meta platforms.
    
    Platforms:
    - instagram_feed: 1:1 (1080x1080)
    - instagram_story: 9:16 (1080x1920)
    - instagram_reel: 9:16 (1080x1920), 30-90s
    - facebook_feed: 1:1 or 4:5 recommended (1080x1080 or 1080x1350)
    - facebook_story: 9:16 (1080x1920)
    """
    specs = {
        'instagram_feed': {
            'size': (1080, 1080),
            'aspect_ratio': '1:1',
            'fps': 30,
            'bitrate': '6000k',
            'max_duration': 60,
            'format': 'mp4',
            'safe_zone': {'top': 0.15, 'bottom': 0.20}  # Avoid UI overlays
        },
        'instagram_story': {
            'size': (1080, 1920),
            'aspect_ratio': '9:16',
            'fps': 30,
            'bitrate': '6000k',
            'max_duration': 15,
            'format': 'mp4',
            'safe_zone': {'top': 0.25, 'bottom': 0.20}  # Avoid profile pic & CTA
        },
        'instagram_reel': {
            'size': (1080, 1920),
            'aspect_ratio': '9:16',
            'fps': 30,
            'bitrate': '8000k',
            'max_duration': 90,
            'format': 'mp4',
            'safe_zone': {'top': 0.20, 'bottom': 0.25}  # Avoid caption & buttons
        },
        'facebook_feed': {
            'size': (1080, 1350),  # 4:5 for max screen real estate
            'aspect_ratio': '4:5',
            'fps': 30,
            'bitrate': '6000k',
            'max_duration': 240,
            'format': 'mp4',
            'safe_zone': {'top': 0.10, 'bottom': 0.10}
        },
        'facebook_story': {
            'size': (1080, 1920),
            'aspect_ratio': '9:16',
            'fps': 30,
            'bitrate': '6000k',
            'max_duration': 20,
            'format': 'mp4',
            'safe_zone': {'top': 0.20, 'bottom': 0.20}
        }
    }
    
    return specs.get(platform, specs['instagram_feed'])


def create_meta_optimized_reel(image_path, text, output_path, client_data, 
                                platform='instagram_feed', motion='zoom_in'):
    """
    Creates Meta-optimized video reels with dramatic Ken Burns animations.
    
    Supports: instagram_feed, instagram_story, instagram_reel, 
              facebook_feed, facebook_story
    """
    try:
        # Get platform specifications
        specs = get_platform_specs(platform)
        target_w, target_h = specs['size']
        fps = specs['fps']
        bitrate = specs['bitrate']
        safe_top = specs['safe_zone']['top']
        safe_bottom = specs['safe_zone']['bottom']
        
        # Duration: 10s default, but respect platform limits
        duration = min(10, specs['max_duration'])
        
        display_text = prepare_persian_text(text)
        persian_font = get_available_persian_font()
        print(f"   - Platform: {platform} ({specs['aspect_ratio']})")
        print(f"   - Resolution: {target_w}x{target_h}")
        print(f"   - Using font: {persian_font}")

        # Load and prepare background image
        bg_clip = ImageClip(image_path).set_duration(duration)
        img_w, img_h = bg_clip.size
        
        # Calculate base scale to cover frame with room for motion
        scale_w = target_w / img_w
        scale_h = target_h / img_h
        base_scale = max(scale_w, scale_h) * 1.15  # 15% extra for movement room

        # ============================================================
        # DRAMATIC KEN BURNS EFFECT (Optimized for mobile viewing)
        # ============================================================
        
        if motion == 'zoom_in':
            def calc_transform(t):
                progress = t / duration
                # Dramatic 35% zoom for small screens
                scale = 1.0 + (0.35 * progress)
                # Subtle pan to keep subject in frame
                x_offset = -img_w * 0.08 * progress
                y_offset = -img_h * 0.05 * progress
                return scale, x_offset, y_offset
                
        elif motion == 'zoom_out':
            def calc_transform(t):
                progress = t / duration
                scale = 1.35 - (0.35 * progress)
                x_offset = -img_w * 0.08 * (1 - progress)
                y_offset = -img_h * 0.05 * (1 - progress)
                return scale, x_offset, y_offset
                
        elif motion == 'pan_right':
            def calc_transform(t):
                progress = t / duration
                scale = 1.0 + (0.20 * progress)
                # Strong horizontal movement
                x_offset = -img_w * 0.25 * progress
                y_offset = 0
                return scale, x_offset, y_offset
                
        elif motion == 'pan_left':
            def calc_transform(t):
                progress = t / duration
                scale = 1.0 + (0.20 * progress)
                x_offset = img_w * 0.25 * progress - img_w * 0.25
                y_offset = 0
                return scale, x_offset, y_offset
                
        elif motion == 'pan_up':
            def calc_transform(t):
                progress = t / duration
                scale = 1.0 + (0.20 * progress)
                x_offset = 0
                y_offset = -img_h * 0.20 * progress
                return scale, x_offset, y_offset
                
        elif motion == 'pan_down':
            def calc_transform(t):
                progress = t / duration
                scale = 1.0 + (0.20 * progress)
                x_offset = 0
                y_offset = img_h * 0.20 * progress - img_h * 0.20
                return scale, x_offset, y_offset
                
        else:  # default zoom_in_slow
            def calc_transform(t):
                progress = t / duration
                scale = 1.0 + (0.25 * progress)
                x_offset = -img_w * 0.05 * progress
                y_offset = 0
                return scale, x_offset, y_offset

        # Smooth easing for natural motion
        def ease_in_out_cubic(t):
            if t < 0.5:
                return 4 * t * t * t
            else:
                return 1 - pow(-2 * t + 2, 3) / 2

        def get_frame_position(t):
            progress = ease_in_out_cubic(t / duration)
            scale, x_off, y_off = calc_transform(t)
            
            new_w = img_w * scale * base_scale
            new_h = img_h * scale * base_scale
            
            x = (target_w - new_w) / 2 + x_off * base_scale * scale
            y = (target_h - new_h) / 2 + y_off * base_scale * scale
            
            return x, y

        def get_frame_size(t):
            scale, _, _ = calc_transform(t)
            return img_w * scale * base_scale, img_h * scale * base_scale

        # Apply motion
        bg_clip = bg_clip.set_position(get_frame_position)
        bg_clip = bg_clip.resize(get_frame_size)

        primary_color = client_data.get('primary_color', '#D32F2F')
        secondary_color = client_data.get('secondary_color', '#FFC107')

        # Font sizing optimized for mobile readability
        text_length = len(text)
        if text_length <= 15:
            fontsize = 80 if target_h >= 1920 else 70  # Larger for stories/reels
        elif text_length <= 25:
            fontsize = 65 if target_h >= 1920 else 55
        else:
            fontsize = 50 if target_h >= 1920 else 45

        # Text width: 85% for stories, 70% for feed
        txt_width = int(target_w * (0.85 if target_h > target_w else 0.70))

        # Calculate text dimensions
        temp_text = TextClip(
            display_text,
            fontsize=fontsize,
            color='white',
            font=persian_font,
            method='caption',
            size=(txt_width, None),
            align='center',
            interline=-6
        )
        txt_w, txt_h = temp_text.size
        temp_text.close()
        
        # Overlay positioning with safe zones
        padding = 30
        overlay_height = max(txt_h + (padding * 2), int(target_h * 0.12))
        
        # Position overlay in safe zone (above bottom UI elements)
        overlay_y_final = target_h - overlay_height - int(target_h * safe_bottom)
        
        # Ensure overlay doesn't overlap top safe zone
        if overlay_y_final < int(target_h * safe_top):
            overlay_y_final = int(target_h * safe_top) + 20

        # Text animation
        text_final_y = overlay_y_final + (overlay_height - txt_h) // 2
        text_start_y = text_final_y + 40

        txt_clip = (TextClip(
            display_text,
            fontsize=fontsize,
            color='white',
            font=persian_font,
            method='caption',
            size=(txt_width, None),
            align='center',
            interline=-6
        )
        .set_duration(duration)
        .set_start(0.2)
        .set_position(lambda t: (
            (target_w - txt_w) // 2,  # Center horizontally
            text_start_y + (text_final_y - text_start_y) * min(max((t - 0.2) / 0.7, 0), 1)
        ))
        )
        txt_clip = txt_clip.fadein(0.3)

        # Text shadow
        shadow_clip = (TextClip(
            display_text,
            fontsize=fontsize,
            color='black',
            font=persian_font,
            method='caption',
            size=(txt_width, None),
            align='center',
            interline=-6
        )
        .set_duration(duration)
        .set_start(0.2)
        .set_position(lambda t: (
            (target_w - txt_w) // 2 + 3,
            (text_start_y + (text_final_y - text_start_y) * min(max((t - 0.2) / 0.7, 0), 1)) + 3
        ))
        )
        shadow_clip = shadow_clip.set_opacity(0.5).fadein(0.3)

        # Color stripe overlay
        overlay_y_start = target_h + 10
        overlay = (ColorClip(
            size=(target_w, overlay_height),
            color=hex_to_rgb(primary_color)
        )
        .set_duration(duration)
        .set_opacity(0.92)
        .set_position(lambda t: (
            'center',
            overlay_y_start + (overlay_y_final - overlay_y_start) * min(t / 0.5, 1)
        ))
        )

        # Top gradient for depth
        gradient_height = int(target_h * 0.15)
        top_gradient = (ColorClip(
            size=(target_w, gradient_height),
            color=(0, 0, 0)
        )
        .set_duration(duration)
        .set_opacity(0.25)
        .set_position(('center', 0))
        .fadein(0.4)
        )

        # Build layers
        layers = [bg_clip, top_gradient, overlay, shadow_clip, txt_clip]

        # Add logo if available
        logo_path = client_data.get('logo_path')
        if logo_path and os.path.exists(logo_path):
            logo_clip = create_animated_logo(
                logo_path, target_w, target_h, overlay_height, 
                overlay_y_final, duration
            )
            if logo_clip:
                layers.append(logo_clip)

        # Compose
        final_video = CompositeVideoClip(layers, size=(target_w, target_h))

        # Export with platform-optimized settings
        final_video.write_videofile(
            output_path,
            fps=fps,
            codec='libx264',
            audio=False,
            logger=None,
            threads=4,
            preset='slow',  # Better compression for mobile
            bitrate=bitrate,
            ffmpeg_params=[
                '-pix_fmt', 'yuv420p',  # Universal compatibility
                '-profile:v', 'high',
                '-level', '4.0',
                '-movflags', '+faststart'  # Web optimization
            ]
        )

        # Cleanup
        final_video.close()
        for layer in layers:
            try:
                layer.close()
            except:
                pass

        print(f"   ✓ Created {platform} video: {output_path}")
        return True

    except Exception as e:
        print(f"❌ Video Error: {e}")
        import traceback
        traceback.print_exc()
        return False


# Backward compatibility alias
def create_advanced_video_reel(image_path, text, output_path, client_data, motion='zoom_in'):
    """Legacy wrapper for Instagram Feed (1:1)"""
    return create_meta_optimized_reel(image_path, text, output_path, client_data, 
                                      platform='instagram_feed', motion=motion)
