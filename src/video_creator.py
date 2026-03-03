"""
Maseer Video Creator - Final Production Version
Generates 1224×1536 Meta-optimized videos with campaign-specific styling
"""

import os
import sys
import math
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from moviepy.editor import (
    ImageClip, TextClip, CompositeVideoClip, ColorClip,
    VideoFileClip, AudioFileClip
)
from moviepy.video.fx.all import fadein, fadeout, resize
from moviepy.video.compositing.transitions import slide_in
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

META_WIDTH = 1224
META_HEIGHT = 1536
META_DURATION_SAMPLE = 15
META_DURATION_REGULAR = 12
META_FPS = 30


@dataclass
class VideoConfig:
    width: int = META_WIDTH
    height: int = META_HEIGHT
    duration: float = META_DURATION_REGULAR
    fps: int = META_FPS
    campaign_type: str = 'sample'
    primary_color: str = '#6B21A8'
    secondary_color: str = '#EAB308'


class PersianTextRenderer:
    FONT_CANDIDATES = [
        'Noto-Naskh-Arabic',
        'Noto-Sans-Arabic',
        'DejaVu-Sans',
        'DejaVu-Sans-Bold',
        'FreeSans',
        'FreeSans-Bold',
        'Amiri',
        'Arial'
    ]
    
    def __init__(self):
        self.available_font = self._find_available_font()
        
    def _find_available_font(self) -> str:
        for font in self.FONT_CANDIDATES:
            try:
                test = TextClip("تست", fontsize=20, font=font)
                test.close()
                return font
            except:
                continue
        return 'DejaVu-Sans'
    
    def prepare_text(self, text: str) -> str:
        if not text:
            return ""
        try:
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        except Exception as e:
            print(f"   ⚠️ Text reshaping error: {e}")
            return text
    
    def create_text_clip(
        self,
        text: str,
        fontsize: int = 60,
        color: str = 'white',
        bg_color: Optional[str] = None,
        stroke_color: Optional[str] = None,
        stroke_width: int = 0,
        size: Optional[Tuple[int, int]] = None,
        method: str = 'caption',
        align: str = 'center',
        interline: int = -4
    ) -> TextClip:
        prepared_text = self.prepare_text(text)
        
        params = {
            'txt': prepared_text,
            'fontsize': fontsize,
            'color': color,
            'font': self.available_font,
            'method': method,
            'align': align,
            'interline': interline
        }
        
        if size:
            params['size'] = size
        if bg_color:
            params['bg_color'] = bg_color
        if stroke_color and stroke_width:
            params['stroke_color'] = stroke_color
            params['stroke_width'] = stroke_width
            
        return TextClip(**params)


class ColorProcessor:
    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        hex_clean = hex_color.lstrip('#')
        return tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
        return '#{:02x}{:02x}{:02x}'.format(*rgb).upper()
    
    @staticmethod
    def adjust_brightness(hex_color: str, factor: float) -> str:
        rgb = ColorProcessor.hex_to_rgb(hex_color)
        adjusted = tuple(max(0, min(255, int(c * factor))) for c in rgb)
        return ColorProcessor.rgb_to_hex(adjusted)
    
    @staticmethod
    def saturate(hex_color: str, factor: float = 1.3) -> str:
        rgb = ColorProcessor.hex_to_rgb(hex_color)
        boost = lambda x: max(0, min(255, int(x + (x - 128) * (factor - 1))))
        saturated = tuple(boost(c) for c in rgb)
        return ColorProcessor.rgb_to_hex(saturated)
    
    @staticmethod
    def create_gradient(
        width: int,
        height: int,
        color1: str,
        color2: str,
        direction: str = 'vertical'
    ) -> np.ndarray:
        rgb1 = ColorProcessor.hex_to_rgb(color1)
        rgb2 = ColorProcessor.hex_to_rgb(color2)
        
        if direction == 'vertical':
            gradient = np.zeros((height, width, 3), dtype=np.uint8)
            for y in range(height):
                ratio = y / height
                r = int(rgb1[0] + (rgb2[0] - rgb1[0]) * ratio)
                g = int(rgb1[1] + (rgb2[1] - rgb1[1]) * ratio)
                b = int(rgb1[2] + (rgb2[2] - rgb1[2]) * ratio)
                gradient[y, :] = [r, g, b]
        else:
            gradient = np.zeros((height, width, 3), dtype=np.uint8)
            for x in range(width):
                ratio = x / width
                r = int(rgb1[0] + (rgb2[0] - rgb1[0]) * ratio)
                g = int(rgb1[1] + (rgb2[1] - rgb1[1]) * ratio)
                b = int(rgb1[2] + (rgb2[2] - rgb1[2]) * ratio)
                gradient[:, x] = [r, g, b]
        
        return gradient


class MotionEffects:
    @staticmethod
    def apply_motion(clip, campaign_type: str, duration: float) -> ImageClip:
        if campaign_type == 'morning':
            return MotionEffects._parallax_zoom(clip, duration, zoom_factor=0.15, pan_x=-30)
        elif campaign_type == 'midday':
            return MotionEffects._organic_sway(clip, duration, amplitude=20)
        elif campaign_type == 'evening':
            return MotionEffects._kinetic_zoom(clip, duration, zoom_factor=0.25)
        elif campaign_type == 'night':
            return MotionEffects._stop_motion(clip, duration, fps=12)
        else:
            return MotionEffects._cinematic_reveal(clip, duration, zoom_factor=0.35)
    
    @staticmethod
    def _parallax_zoom(clip, duration: float, zoom_factor: float, pan_x: float):
        def transform(t):
            progress = t / duration
            scale = 1.0 + (zoom_factor * progress)
            x_offset = pan_x * progress
            return scale, x_offset, 0
        return MotionEffects._apply_transform(clip, transform, duration)
    
    @staticmethod
    def _organic_sway(clip, duration: float, amplitude: float):
        def transform(t):
            progress = t / duration
            ease = math.sin(progress * math.pi)
            scale = 1.0 + (0.05 * ease)
            x_offset = amplitude * math.sin(progress * math.pi * 2)
            return scale, x_offset, 0
        return MotionEffects._apply_transform(clip, transform, duration)
    
    @staticmethod
    def _kinetic_zoom(clip, duration: float, zoom_factor: float):
        def transform(t):
            progress = t / duration
            ease = progress * progress
            scale = 1.0 + (zoom_factor * ease)
            x_offset = -40 * ease
            return scale, x_offset, 0
        return MotionEffects._apply_transform(clip, transform, duration)
    
    @staticmethod
    def _stop_motion(clip, duration: float, fps: int):
        def transform(t):
            step = int(t * fps) / fps
            progress = step / duration
            scale = 1.0 + (0.08 * progress)
            jitter_x = random.uniform(-2, 2) if random.random() > 0.7 else 0
            return scale, jitter_x, 0
        return MotionEffects._apply_transform(clip, transform, duration)
    
    @staticmethod
    def _cinematic_reveal(clip, duration: float, zoom_factor: float):
        def transform(t):
            progress = t / duration
            ease = 1 - math.pow(1 - progress, 3)
            scale = 1.0 + (zoom_factor * ease)
            x_offset = -50 * ease
            y_offset = -20 * ease
            return scale, x_offset, y_offset
        return MotionEffects._apply_transform(clip, transform, duration)
    
    @staticmethod
    def _apply_transform(clip, transform_func, duration: float):
        original_w, original_h = clip.size
        
        def make_frame(t):
            scale, x_off, y_off = transform_func(t)
            
            new_w = int(original_w * scale)
            new_h = int(original_h * scale)
            
            frame = clip.get_frame(t)
            
            pil_img = Image.fromarray(frame)
            resized = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            left = (new_w - original_w) // 2 + int(x_off)
            top = (new_h - original_h) // 2 + int(y_off)
            
            left = max(0, min(left, new_w - original_w))
            top = max(0, min(top, new_h - original_h))
            
            cropped = resized.crop((left, top, left + original_w, top + original_h))
            
            return np.array(cropped)
        
        from moviepy.video.io.VideoFileClip import VideoClip
        return VideoClip(make_frame, duration=duration).set_fps(META_FPS)


class VideoCompositor:
    def __init__(self, config: VideoConfig):
        self.config = config
        self.text_renderer = PersianTextRenderer()
        self.color_processor = ColorProcessor()
        
    def create_video(
        self,
        image_path: str,
        headline: str,
        subheadline: str = "",
        client_data: Dict = None,
        output_path: str = None
    ) -> bool:
        try:
            print(f"   🎬 Compositing {self.config.campaign_type} video...")
            
            bg_clip = self._prepare_background(image_path)
            
            motion_clip = MotionEffects.apply_motion(
                bg_clip, 
                self.config.campaign_type, 
                self.config.duration
            )
            
            text_layers = self._create_text_layers(headline, subheadline)
            
            overlay = self._create_color_overlay()
            
            logo_layer = None
            if client_data and client_data.get('logo_path'):
                logo_layer = self._create_logo_layer(client_data['logo_path'])
            
            badge_layer = None
            if self.config.campaign_type == 'sample':
                badge_layer = self._create_sample_badge()
            
            layers = [motion_clip, overlay]
            layers.extend(text_layers)
            if logo_layer:
                layers.append(logo_layer)
            if badge_layer:
                layers.append(badge_layer)
            
            final = CompositeVideoClip(
                layers,
                size=(self.config.width, self.config.height)
            ).set_duration(self.config.duration)
            
            self._export_video(final, output_path)
            
            final.close()
            for layer in layers:
                try:
                    layer.close()
                except:
                    pass
            
            print(f"   ✅ Created: {output_path}")
            return True
            
        except Exception as e:
            print(f"   ❌ Video creation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _prepare_background(self, image_path: str) -> ImageClip:
        img = Image.open(image_path)
        
        target_ratio = self.config.width / self.config.height
        img_ratio = img.width / img.height
        
        if img_ratio > target_ratio:
            new_height = self.config.height
            new_width = int(new_height * img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            left = (new_width - self.config.width) // 2
            img = img.crop((left, 0, left + self.config.width, self.config.height))
        else:
            new_width = self.config.width
            new_height = int(new_width / img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            top = (new_height - self.config.height) // 3
            img = img.crop((0, top, self.config.width, top + self.config.height))
        
        temp_path = f"temp_bg_{self.config.campaign_type}.png"
        img.save(temp_path, quality=95)
        
        clip = ImageClip(temp_path).set_duration(self.config.duration)
        
        try:
            os.remove(temp_path)
        except:
            pass
            
        return clip
    
    def _create_text_layers(self, headline: str, subheadline: str) -> List:
        layers = []
        
        headline_len = len(headline)
        if headline_len <= 20:
            fontsize = 90 if self.config.campaign_type == 'sample' else 80
        elif headline_len <= 40:
            fontsize = 70 if self.config.campaign_type == 'sample' else 60
        else:
            fontsize = 50
        
        primary = self.config.primary_color
        if self.config.campaign_type == 'sample':
            primary = self.color_processor.saturate(primary, 1.4)
        
        text_y = int(self.config.height * 0.62)
        
        shadow = self.text_renderer.create_text_clip(
            headline,
            fontsize=fontsize,
            color='black',
            size=(int(self.config.width * 0.9), None),
            stroke_color='black',
            stroke_width=0
        ).set_duration(self.config.duration)
        
        shadow = shadow.set_position(('center', text_y + 4))
        shadow = shadow.set_opacity(0.4)
        shadow = fadein(shadow, 0.4)
        layers.append(shadow)
        
        main_text = self.text_renderer.create_text_clip(
            headline,
            fontsize=fontsize,
            color='white',
            size=(int(self.config.width * 0.9), None),
            stroke_color='black',
            stroke_width=2 if self.config.campaign_type == 'sample' else 1
        ).set_duration(self.config.duration)
        
        main_text = main_text.set_position(('center', text_y))
        main_text = fadein(main_text, 0.5)
        layers.append(main_text)
        
        if subheadline and len(subheadline) > 3:
            sub_size = int(fontsize * 0.55)
            sub_y = text_y + fontsize + 20
            
            sub_shadow = self.text_renderer.create_text_clip(
                subheadline,
                fontsize=sub_size,
                color='black',
                size=(int(self.config.width * 0.85), None)
            ).set_duration(self.config.duration)
            sub_shadow = sub_shadow.set_position(('center', sub_y + 2))
            sub_shadow = sub_shadow.set_opacity(0.3)
            layers.append(sub_shadow)
            
            sub_text = self.text_renderer.create_text_clip(
                subheadline,
                fontsize=sub_size,
                color='white',
                size=(int(self.config.width * 0.85), None)
            ).set_duration(self.config.duration)
            sub_text = sub_text.set_position(('center', sub_y))
            sub_text = fadein(sub_text, 0.6)
            layers.append(sub_text)
        
        return layers
    
    def _create_color_overlay(self) -> ColorClip:
        bar_height = int(self.config.height * 0.12)
        
        color = self.config.primary_color
        if self.config.campaign_type == 'sample':
            color = self.color_processor.saturate(color, 1.3)
        
        rgb = self.color_processor.hex_to_rgb(color)
        
        overlay = ColorClip(
            size=(self.config.width, bar_height),
            color=rgb
        ).set_duration(self.config.duration)
        
        overlay = overlay.set_position(('center', self.config.height - bar_height))
        overlay = overlay.set_opacity(0.92)
        overlay = fadein(overlay, 0.3)
        
        return overlay
    
    def _create_logo_layer(self, logo_path: str) -> Optional[ImageClip]:
        try:
            if not os.path.exists(logo_path):
                return None
            
            logo_img = Image.open(logo_path)
            
            bar_height = int(self.config.height * 0.12)
            max_width = int(self.config.width * 0.18)
            max_height = int(bar_height * 0.7)
            
            logo_ratio = logo_img.width / logo_img.height
            if logo_ratio > 1:
                logo_width = max_width
                logo_height = int(logo_width / logo_ratio)
            else:
                logo_height = max_height
                logo_width = int(logo_height * logo_ratio)
            
            logo_img = logo_img.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
            
            temp_logo = f"temp_logo_{self.config.campaign_type}.png"
            logo_img.save(temp_logo)
            
            logo_clip = ImageClip(temp_logo).set_duration(self.config.duration)
            
            padding = 40
            x_pos = self.config.width - logo_width - padding
            y_pos = self.config.height - bar_height + (bar_height - logo_height) // 2
            
            start_x = self.config.width + 50
            logo_clip = logo_clip.set_position(
                lambda t: (
                    start_x + (x_pos - start_x) * min(t / 0.8, 1),
                    y_pos
                )
            )
            logo_clip = fadein(logo_clip, 0.6)
            
            try:
                os.remove(temp_logo)
            except:
                pass
            
            return logo_clip
            
        except Exception as e:
            print(f"   ⚠️ Logo processing failed: {e}")
            return None
    
    def _create_sample_badge(self) -> TextClip:
        badge = TextClip(
            "SAMPLE",
            fontsize=32,
            color='white',
            font='DejaVu-Sans-Bold',
            bg_color=self.color_processor.hex_to_rgb(self.config.secondary_color),
            method='caption',
            size=(160, 44),
            align='center'
        ).set_duration(self.config.duration)
        
        badge = badge.set_position((20, 20))
        badge = fadein(badge, 0.3)
        
        return badge
    
    def _export_video(self, clip, output_path: str):
        fps = 12 if self.config.campaign_type == 'night' else META_FPS
        
        clip.write_videofile(
            output_path,
            fps=fps,
            codec='libx264',
            audio=False,
            preset='slow',
            bitrate='8000k',
            threads=4,
            logger=None,
            ffmpeg_params=[
                '-pix_fmt', 'yuv420p',
                '-profile:v', 'high',
                '-level', '4.2',
                '-movflags', '+faststart',
                '-vf', 'format=yuv420p,scale=1224:1536:force_original_aspect_ratio=decrease,pad=1224:1536:(ow-iw)/2:(oh-ih)/2'
            ]
        )


def create_campaign_video(
    image_path: str,
    content: Dict,
    client_data: Dict,
    output_path: str,
    campaign_type: str = 'sample'
) -> bool:
    config = VideoConfig(
        width=META_WIDTH,
        height=META_HEIGHT,
        duration=META_DURATION_SAMPLE if campaign_type == 'sample' else META_DURATION_REGULAR,
        campaign_type=campaign_type,
        primary_color=client_data.get('primary_color', '#6B21A8'),
        secondary_color=client_data.get('secondary_color', '#EAB308')
    )
    
    compositor = VideoCompositor(config)
    
    headline = content.get('headline', content.get('text', 'Your Brand'))
    subheadline = content.get('subheadline', '')
    
    return compositor.create_video(
        image_path=image_path,
        headline=headline,
        subheadline=subheadline,
        client_data=client_data,
        output_path=output_path
    )


def create_broadcast_reel(*args, **kwargs):
    return create_campaign_video(*args, **kwargs)


def create_meta_optimized_reel(*args, **kwargs):
    return create_campaign_video(*args, **kwargs)


if __name__ == '__main__':
    test_config = VideoConfig(campaign_type='sample')
    compositor = VideoCompositor(test_config)
    print(f"VideoCompositor initialized: {META_WIDTH}x{META_HEIGHT}")
