# 🎯 Maseer Media Inc.

AI-powered video marketing for Afghan businesses. The automation backend for Ariana Coach Portal.

## 🌐 How It Works

1. **Client Signup**: Business fills form at [Ariana Coach Portal](https://hasinamusadiq.github.io/maseer_portal/)
2. **GitHub Issue Created**: Form submission creates an issue in this repository
3. **Auto-Processing**: GitHub Actions parses the issue and adds client to `clients.json`
4. **Video Generation**: Every 6 hours, pipeline generates ONE professional video per client
5. **Delivery**: Video sent via Telegram with branded graphics

## 🚀 Setup

### Required Secrets (Settings → Secrets → Actions)

| Secret | Description |
|--------|-------------|
| `GROQ_API_KEY` | AI content generation |
| `HF_TOKEN` | Hugging Face image generation |
| `TELEGRAM_BOT_TOKEN` | Video delivery |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |
| `PAT_TOKEN` | GitHub Personal Access Token (repo scope) |

### Frontend Repository
The signup form lives at `hasinamusadiq.github.io/maseer-portal/` (separate repo).

## 📋 Client Data Flow
