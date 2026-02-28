# 📺 Maseer Automation - New Client Broadcast Pipeline

AI-powered broadcast TV-quality video marketing for **new Afghan business signups**.

## 🌐 How It Works

1. **New Client Signup**: Client fills form at [maseer-portal](https://hasinamusadiq.github.io/maseer_portal/)
2. **GitHub Issue Created**: Form submission creates an issue in this repository
3. **Auto-Processing**: GitHub Actions automatically adds client to `clients.json`
4. **Video Generation**: Every 6 hours, pipeline generates ONE broadcast video per new client
5. **Delivery**: Video sent via Telegram with B Nazanin Bold + TV effects

## 🚀 Setup

### Required Secrets (Settings → Secrets → Actions)

| Secret | Description |
|--------|-------------|
| `GROQ_API_KEY` | AI content generation |
| `HF_TOKEN` | Hugging Face image generation |
| `TELEGRAM_BOT_TOKEN` | Video delivery |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |
| `PAT_TOKEN` | GitHub Personal Access Token (for cross-repo triggers) |

### Frontend Repository

The signup form lives at `hasinamusadiq.github.io/maseer_portal/` (separate repo).

## 📋 Client Data Flow
