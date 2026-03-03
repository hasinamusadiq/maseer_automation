"""
Maseer Automation - AI Video Marketing for Afghan Businesses
Version 2.0.0 - 1224×1536 Meta-Optimized
"""

__version__ = "2.0.0"
__author__ = "Maseer Media Team"
__description__ = "Automated 1224×1536 video generation with 4 daily campaigns"

from . import ai_engine
from . import image_service
from . import video_creator
from . import update_clients
from . import main

from .ai_engine import (
    get_content_for_campaign,
    generate_all_campaigns,
    CAMPAIGNS,
    INDUSTRY_METAPHORS
)
from .video_creator import (
    create_campaign_video,
    VideoCompositor,
    VideoConfig,
    META_WIDTH,
    META_HEIGHT
)
from .image_service import generate_image_with_retry
from .update_clients import parse_issue, save_client

__all__ = [
    'get_content_for_campaign',
    'generate_all_campaigns',
    'create_campaign_video',
    'VideoCompositor',
    'VideoConfig',
    'generate_image_with_retry',
    'parse_issue',
    'save_client',
    'CAMPAIGNS',
    'INDUSTRY_METAPHORS',
    'META_WIDTH',
    'META_HEIGHT',
]
