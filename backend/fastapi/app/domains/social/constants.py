"""Social Workspace vocabulary and provider configuration."""

from ...deps import AuthContext
from ...deps import require_auth
from fastapi import Depends
from typing import Annotated
from typing import Any
import logging

AuthDep = Annotated[AuthContext, Depends(require_auth)]

ACCOUNT_NOT_FOUND = "Social account not found."

MESSAGE_NOT_FOUND = "Inbox message not found."

SAVED_REPLY_NOT_FOUND = "Saved reply not found."

JSON_CONTENT_TYPE = "application/json"

REPORT_NOT_FOUND = "Report not found."

UGC_ASSET_NOT_FOUND = "UGC asset not found."

REVIEW_NOT_FOUND = "Review not found."

SCHEDULED_POST_NOT_FOUND = "Scheduled post not found."

START_PAGE_NOT_FOUND = "Start Page not found."

DEFAULT_SOCIAL_TIMEZONE = "America/New_York"

TEN_AM_LABEL = "10:00 AM"

DEFAULT_SOCIAL_AGENT = "Social Desk"

SUPPORTED_NETWORKS = {
    "instagram": {"label": "Instagram", "formats": ["image", "video", "story", "reel", "carousel", "text"]},
    "facebook": {"label": "Facebook", "formats": ["image", "video", "story", "reel", "text"]},
    "linkedin": {"label": "LinkedIn", "formats": ["image", "video", "document", "text"]},
    "x": {"label": "X", "formats": ["image", "video", "voice", "text"]},
    "tiktok": {"label": "TikTok", "formats": ["video", "voice", "text"]},
    "youtube": {"label": "YouTube", "formats": ["video", "short", "text"]},
    "pinterest": {"label": "Pinterest", "formats": ["image", "video", "text"]},
    "google_business_profile": {"label": "Google Business Profile", "formats": ["image", "video", "text"]},
    "threads": {"label": "Threads", "formats": ["image", "video", "text"]},
    "snapchat": {"label": "Snapchat", "formats": ["image", "video", "story", "text"]},
    "reddit": {"label": "Reddit", "formats": ["image", "video", "link", "text"]},
    "tumblr": {"label": "Tumblr", "formats": ["image", "video", "audio", "text"]},
    "discord": {"label": "Discord", "formats": ["image", "video", "voice", "text"]},
    "telegram": {"label": "Telegram", "formats": ["image", "video", "voice", "document", "text"]},
    "whatsapp_business": {"label": "WhatsApp Business", "formats": ["image", "video", "voice", "document", "text"]},
    "wechat": {"label": "WeChat", "formats": ["image", "video", "voice", "text"]},
    "line": {"label": "LINE", "formats": ["image", "video", "voice", "text"]},
    "qq": {"label": "QQ", "formats": ["image", "video", "text"]},
    "vk": {"label": "VK", "formats": ["image", "video", "story", "text"]},
    "odnoklassniki": {"label": "Odnoklassniki", "formats": ["image", "video", "text"]},
    "mastodon": {"label": "Mastodon", "formats": ["image", "video", "text"]},
    "bluesky": {"label": "Bluesky", "formats": ["image", "video", "text"]},
    "twitch": {"label": "Twitch", "formats": ["video", "clip", "text"]},
    "kick": {"label": "Kick", "formats": ["video", "clip", "text"]},
    "rumble": {"label": "Rumble", "formats": ["video", "text"]},
    "vimeo": {"label": "Vimeo", "formats": ["video", "text"]},
    "dailymotion": {"label": "Dailymotion", "formats": ["video", "text"]},
    "quora": {"label": "Quora", "formats": ["link", "text"]},
    "medium": {"label": "Medium", "formats": ["image", "link", "text"]},
    "wordpress": {"label": "WordPress", "formats": ["image", "video", "link", "text"]},
    "substack": {"label": "Substack", "formats": ["image", "audio", "link", "text"]},
    "blogger": {"label": "Blogger", "formats": ["image", "video", "link", "text"]},
    "wechat_channels": {"label": "WeChat Channels", "formats": ["image", "video", "text"]},
    "xiaohongshu": {"label": "Xiaohongshu", "formats": ["image", "video", "text"]},
    "douyin": {"label": "Douyin", "formats": ["video", "text"]},
    "kuaishou": {"label": "Kuaishou", "formats": ["video", "text"]},
    "baidu_tieba": {"label": "Baidu Tieba", "formats": ["image", "link", "text"]},
    "naver_blog": {"label": "Naver Blog", "formats": ["image", "video", "link", "text"]},
    "kakao_story": {"label": "KakaoStory", "formats": ["image", "video", "text"]},
    "flickr": {"label": "Flickr", "formats": ["image", "text"]},
}

FACEBOOK_OAUTH_AUTHORIZE_URL = "https://www.facebook.com/v20.0/dialog/oauth"

GOOGLE_OAUTH_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"

READ_WRITE_SCOPE = "read write"

DEFAULT_BACKGROUND_MEDIA = "AI Videos"

DEFAULT_SUBTITLES_LANGUAGE = "Auto (detect)"

DEFAULT_FONT_FAMILY = "Hanken Grotesk"

UNSUPPORTED_SOCIAL_NETWORK = "Unsupported social network."

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"

PUBLISH_MODE_PATTERN = "^(auto|now|draft)$"

INTEGRATIONS_WEBHOOKS_ROUTE = "/social/integrations/webhooks"

_SW_AI_ALLOWED_ACTIONS = {"rephrase", "shorten", "expand", "casual", "formal", "generate", "repurpose", "respond"}

_SW_AI_DEFAULT_POLICY = {
    "allow_actions": sorted(_SW_AI_ALLOWED_ACTIONS),
    "block_prompt_injection": True,
    "block_pii": True,
    "block_toxicity": True,
    "redact_html": True,
}

_SW_AI_LOGGER = logging.getLogger(__name__)

OAUTH_PROVIDERS = {
    "instagram": {
        "label": "Instagram",
        "client_id_env": "SOCIAL_OAUTH_INSTAGRAM_CLIENT_ID",
        "authorize_url": FACEBOOK_OAUTH_AUTHORIZE_URL,
        "scope": "instagram_basic,instagram_manage_comments,instagram_content_publish,pages_show_list,pages_read_engagement,business_management",
    },
    "facebook": {
        "label": "Facebook",
        "client_id_env": "SOCIAL_OAUTH_FACEBOOK_CLIENT_ID",
        "authorize_url": FACEBOOK_OAUTH_AUTHORIZE_URL,
        "scope": "pages_show_list,pages_manage_posts,pages_read_engagement,pages_manage_metadata,business_management",
    },
    "linkedin": {
        "label": "LinkedIn",
        "client_id_env": "SOCIAL_OAUTH_LINKEDIN_CLIENT_ID",
        "authorize_url": "https://www.linkedin.com/oauth/v2/authorization",
        "scope": "r_basicprofile,r_organization_social,w_organization_social",
    },
    "x": {
        "label": "X",
        "client_id_env": "SOCIAL_OAUTH_X_CLIENT_ID",
        "authorize_url": "https://twitter.com/i/oauth2/authorize",
        "scope": "tweet.read tweet.write users.read offline.access",
    },
    "tiktok": {
        "label": "TikTok",
        "client_id_env": "SOCIAL_OAUTH_TIKTOK_CLIENT_ID",
        "authorize_url": "https://www.tiktok.com/v2/auth/authorize/",
        "scope": "user.info.basic,video.publish,video.list",
    },
    "youtube": {
        "label": "YouTube",
        "client_id_env": "SOCIAL_OAUTH_YOUTUBE_CLIENT_ID",
        "authorize_url": GOOGLE_OAUTH_AUTHORIZE_URL,
        "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly",
    },
    "pinterest": {
        "label": "Pinterest",
        "client_id_env": "SOCIAL_OAUTH_PINTEREST_CLIENT_ID",
        "authorize_url": "https://www.pinterest.com/oauth/",
        "scope": "pins:read,pins:write,boards:read,boards:write",
    },
    "google_business_profile": {
        "label": "Google Business Profile",
        "client_id_env": "SOCIAL_OAUTH_GBP_CLIENT_ID",
        "authorize_url": GOOGLE_OAUTH_AUTHORIZE_URL,
        "scope": "https://www.googleapis.com/auth/business.manage",
    },
    "threads": {
        "label": "Threads",
        "client_id_env": "SOCIAL_OAUTH_THREADS_CLIENT_ID",
        "authorize_url": FACEBOOK_OAUTH_AUTHORIZE_URL,
        "scope": "threads_basic,threads_content_publish,threads_manage_replies",
    },
    "snapchat": {
        "label": "Snapchat",
        "client_id_env": "SOCIAL_OAUTH_SNAPCHAT_CLIENT_ID",
        "authorize_url": "https://accounts.snapchat.com/accounts/oauth2/auth",
        "scope": "snapchat-marketing-api",
    },
    "reddit": {
        "label": "Reddit",
        "client_id_env": "SOCIAL_OAUTH_REDDIT_CLIENT_ID",
        "authorize_url": "https://www.reddit.com/api/v1/authorize",
        "scope": "identity,read,submit",
    },
    "tumblr": {
        "label": "Tumblr",
        "client_id_env": "SOCIAL_OAUTH_TUMBLR_CLIENT_ID",
        "authorize_url": "https://www.tumblr.com/oauth2/authorize",
        "scope": "basic,write",
    },
    "discord": {
        "label": "Discord",
        "client_id_env": "SOCIAL_OAUTH_DISCORD_CLIENT_ID",
        "authorize_url": "https://discord.com/oauth2/authorize",
        "scope": "identify,guilds,messages.read",
    },
    "telegram": {
        "label": "Telegram",
        "client_id_env": "SOCIAL_OAUTH_TELEGRAM_CLIENT_ID",
        "authorize_url": "https://oauth.telegram.org/auth",
        "scope": "basic,write",
    },
    "whatsapp_business": {
        "label": "WhatsApp Business",
        "client_id_env": "SOCIAL_OAUTH_WHATSAPP_CLIENT_ID",
        "authorize_url": FACEBOOK_OAUTH_AUTHORIZE_URL,
        "scope": "whatsapp_business_messaging,whatsapp_business_management,business_management",
    },
    "wechat": {
        "label": "WeChat",
        "client_id_env": "SOCIAL_OAUTH_WECHAT_CLIENT_ID",
        "authorize_url": "https://open.weixin.qq.com/connect/qrconnect",
        "scope": "snsapi_login",
    },
    "line": {
        "label": "LINE",
        "client_id_env": "SOCIAL_OAUTH_LINE_CLIENT_ID",
        "authorize_url": "https://access.line.me/oauth2/v2.1/authorize",
        "scope": "profile openid",
    },
    "qq": {
        "label": "QQ",
        "client_id_env": "SOCIAL_OAUTH_QQ_CLIENT_ID",
        "authorize_url": "https://graph.qq.com/oauth2.0/authorize",
        "scope": "get_user_info,add_share",
    },
    "vk": {
        "label": "VK",
        "client_id_env": "SOCIAL_OAUTH_VK_CLIENT_ID",
        "authorize_url": "https://oauth.vk.com/authorize",
        "scope": "wall,photos,video,offline",
    },
    "odnoklassniki": {
        "label": "Odnoklassniki",
        "client_id_env": "SOCIAL_OAUTH_ODNOKLASSNIKI_CLIENT_ID",
        "authorize_url": "https://connect.ok.ru/oauth/authorize",
        "scope": "VALUABLE_ACCESS",
    },
    "mastodon": {
        "label": "Mastodon",
        "client_id_env": "SOCIAL_OAUTH_MASTODON_CLIENT_ID",
        "authorize_url": "https://mastodon.social/oauth/authorize",
        "scope": "read write follow",
    },
    "bluesky": {
        "label": "Bluesky",
        "client_id_env": "SOCIAL_OAUTH_BLUESKY_CLIENT_ID",
        "authorize_url": "https://bsky.social/oauth/authorize",
        "scope": "atproto content.write content.read",
    },
    "twitch": {
        "label": "Twitch",
        "client_id_env": "SOCIAL_OAUTH_TWITCH_CLIENT_ID",
        "authorize_url": "https://id.twitch.tv/oauth2/authorize",
        "scope": "user:read:email channel:manage:broadcast",
    },
    "kick": {
        "label": "Kick",
        "client_id_env": "SOCIAL_OAUTH_KICK_CLIENT_ID",
        "authorize_url": "https://id.kick.com/oauth/authorize",
        "scope": "profile content.write content.read",
    },
    "rumble": {
        "label": "Rumble",
        "client_id_env": "SOCIAL_OAUTH_RUMBLE_CLIENT_ID",
        "authorize_url": "https://rumble.com/oauth/authorize",
        "scope": READ_WRITE_SCOPE,
    },
    "vimeo": {
        "label": "Vimeo",
        "client_id_env": "SOCIAL_OAUTH_VIMEO_CLIENT_ID",
        "authorize_url": "https://api.vimeo.com/oauth/authorize",
        "scope": "public private upload",
    },
    "dailymotion": {
        "label": "Dailymotion",
        "client_id_env": "SOCIAL_OAUTH_DAILYMOTION_CLIENT_ID",
        "authorize_url": "https://www.dailymotion.com/oauth/authorize",
        "scope": READ_WRITE_SCOPE + " manage_videos",
    },
    "quora": {
        "label": "Quora",
        "client_id_env": "SOCIAL_OAUTH_QUORA_CLIENT_ID",
        "authorize_url": "https://www.quora.com/oauth/authorize",
        "scope": READ_WRITE_SCOPE,
    },
    "medium": {
        "label": "Medium",
        "client_id_env": "SOCIAL_OAUTH_MEDIUM_CLIENT_ID",
        "authorize_url": "https://medium.com/m/oauth/authorize",
        "scope": "basicProfile,publishPost,listPublications",
    },
    "wordpress": {
        "label": "WordPress",
        "client_id_env": "SOCIAL_OAUTH_WORDPRESS_CLIENT_ID",
        "authorize_url": "https://public-api.wordpress.com/oauth2/authorize",
        "scope": "global",
    },
    "substack": {
        "label": "Substack",
        "client_id_env": "SOCIAL_OAUTH_SUBSTACK_CLIENT_ID",
        "authorize_url": "https://substack.com/oauth/authorize",
        "scope": "read write publications",
    },
    "blogger": {
        "label": "Blogger",
        "client_id_env": "SOCIAL_OAUTH_BLOGGER_CLIENT_ID",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "scope": "https://www.googleapis.com/auth/blogger",
    },
    "wechat_channels": {
        "label": "WeChat Channels",
        "client_id_env": "SOCIAL_OAUTH_WECHAT_CHANNELS_CLIENT_ID",
        "authorize_url": "https://open.weixin.qq.com/connect/qrconnect",
        "scope": "snsapi_login",
    },
    "xiaohongshu": {
        "label": "Xiaohongshu",
        "client_id_env": "SOCIAL_OAUTH_XIAOHONGSHU_CLIENT_ID",
        "authorize_url": "https://api.xiaohongshu.com/oauth/authorize",
        "scope": READ_WRITE_SCOPE,
    },
    "douyin": {
        "label": "Douyin",
        "client_id_env": "SOCIAL_OAUTH_DOUYIN_CLIENT_ID",
        "authorize_url": "https://open.douyin.com/platform/oauth/connect",
        "scope": "video.publish,user_info",
    },
    "kuaishou": {
        "label": "Kuaishou",
        "client_id_env": "SOCIAL_OAUTH_KUAISHOU_CLIENT_ID",
        "authorize_url": "https://open.kuaishou.com/oauth/authorize",
        "scope": "video.publish,user_info",
    },
    "baidu_tieba": {
        "label": "Baidu Tieba",
        "client_id_env": "SOCIAL_OAUTH_BAIDU_TIEBA_CLIENT_ID",
        "authorize_url": "https://openapi.baidu.com/oauth/2.0/authorize",
        "scope": "basic netdisk",
    },
    "naver_blog": {
        "label": "Naver Blog",
        "client_id_env": "SOCIAL_OAUTH_NAVER_BLOG_CLIENT_ID",
        "authorize_url": "https://nid.naver.com/oauth2.0/authorize",
        "scope": "profile write",
    },
    "kakao_story": {
        "label": "KakaoStory",
        "client_id_env": "SOCIAL_OAUTH_KAKAO_STORY_CLIENT_ID",
        "authorize_url": "https://kauth.kakao.com/oauth/authorize",
        "scope": "profile story_publish",
    },
    "flickr": {
        "label": "Flickr",
        "client_id_env": "SOCIAL_OAUTH_FLICKR_CLIENT_ID",
        "authorize_url": "https://www.flickr.com/services/oauth/authorize",
        "scope": READ_WRITE_SCOPE,
    },
}

AVATAR_PRESET_CATALOG: list[dict[str, str]] = [
    {
        "id": "ava-creator-01",
        "name": "Mila Harper",
        "ethnicity": "European",
        "gender": "female",
        "age_range": "25-34",
        "style": "Modern Casual",
        "face_type": "Oval",
        "eye_style": "Almond",
        "body_shape": "Athletic",
        "body_proportions": "Balanced",
        "location": "New York, US",
    },
    {
        "id": "ava-creator-02",
        "name": "Arjun Mehta",
        "ethnicity": "Indian",
        "gender": "male",
        "age_range": "25-34",
        "style": "Business Casual",
        "face_type": "Square",
        "eye_style": "Deep Set",
        "body_shape": "Lean",
        "body_proportions": "Balanced",
        "location": "Mumbai, IN",
    },
    {
        "id": "ava-creator-03",
        "name": "Aiko Tanaka",
        "ethnicity": "East Asian",
        "gender": "female",
        "age_range": "18-24",
        "style": "Streetwear",
        "face_type": "Heart",
        "eye_style": "Monolid",
        "body_shape": "Slim",
        "body_proportions": "Long Torso",
        "location": "Tokyo, JP",
    },
    {
        "id": "ava-creator-04",
        "name": "Kwame Nkrumah",
        "ethnicity": "African",
        "gender": "male",
        "age_range": "35-44",
        "style": "Minimal Premium",
        "face_type": "Round",
        "eye_style": "Hooded",
        "body_shape": "Muscular",
        "body_proportions": "Broad Shoulders",
        "location": "Accra, GH",
    },
    {
        "id": "ava-creator-05",
        "name": "Lina Haddad",
        "ethnicity": "Middle Eastern",
        "gender": "female",
        "age_range": "25-34",
        "style": "Editorial",
        "face_type": "Diamond",
        "eye_style": "Round",
        "body_shape": "Curvy",
        "body_proportions": "Balanced",
        "location": "Dubai, AE",
    },
    {
        "id": "ava-creator-06",
        "name": "Sofia Reyes",
        "ethnicity": "Latin American",
        "gender": "female",
        "age_range": "25-34",
        "style": "Creator Chic",
        "face_type": "Oval",
        "eye_style": "Almond",
        "body_shape": "Petite",
        "body_proportions": "Long Legs",
        "location": "Mexico City, MX",
    },
]

VOICEOVER_GLOBAL_LIBRARY: list[dict[str, Any]] = [
    {
        "name": "Liam",
        "gender": "male",
        "language": "English",
        "accent": "US",
        "style": "Narration",
        "tone": "Confident",
        "premium": True,
    },
    {
        "name": "Layla",
        "gender": "female",
        "language": "English",
        "accent": "US",
        "style": "Presentation",
        "tone": "Warm",
        "premium": True,
    },
    {
        "name": "Adrian",
        "gender": "male",
        "language": "English",
        "accent": "UK",
        "style": "Tutorial",
        "tone": "Professional",
        "premium": False,
    },
    {
        "name": "Maya",
        "gender": "female",
        "language": "English",
        "accent": "AU",
        "style": "Character",
        "tone": "Playful",
        "premium": False,
    },
    {
        "name": "Aarav",
        "gender": "male",
        "language": "English",
        "accent": "IN",
        "style": "Narration",
        "tone": "Calm",
        "premium": False,
    },
    {
        "name": "Isabella",
        "gender": "female",
        "language": "Spanish",
        "accent": "MX",
        "style": "Presentation",
        "tone": "Energetic",
        "premium": True,
    },
    {
        "name": "Noah",
        "gender": "male",
        "language": "French",
        "accent": "FR",
        "style": "Tutorial",
        "tone": "Neutral",
        "premium": True,
    },
    {
        "name": "Yuki",
        "gender": "female",
        "language": "Japanese",
        "accent": "JP",
        "style": "Narration",
        "tone": "Soft",
        "premium": True,
    },
]

_STOP_WORDS = {
    "and",
    "the",
    "for",
    "with",
    "your",
    "from",
    "this",
    "that",
    "into",
    "are",
    "you",
    "our",
    "about",
    "their",
    "have",
    "has",
    "will",
    "can",
    "all",
    "more",
    "best",
    "new",
    "get",
    "its",
    "www",
    "http",
    "https",
    "com",
}

_DEFAULT_KEYWORDS = ["social media", "marketing"]

_INDUSTRY_RULES: dict[str, set[str]] = {
    "saas": {"saas", "software", "platform", "automation"},
    "ecommerce": {"shop", "store", "ecommerce", "retail"},
    "finance": {"finance", "fintech", "bank", "payments", "invest"},
    "healthcare": {"health", "medical", "wellness", "clinic"},
    "education": {"education", "learning", "course", "academy"},
    "travel": {"travel", "tour", "hotel", "trip"},
}
