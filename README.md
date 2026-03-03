# 🎯 Maseer Automation

AI-powered video marketing for Afghan businesses. The automation backend for Maseer Portal.

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

### Daily Automation
- **4 Campaigns Daily**: Morning (6AM), Midday (12PM), Evening (6PM), Night (12AM) Kabul time
- **Auto-Cleanup**: Artifacts deleted after 1 day to prevent storage overflow
- **Compression**: All videos compressed with H.264 CRF 23

## 📁 Structure
- `src/ai_engine.py` - Content generation with Groq
- `src/video_creator.py` - 1224×1536 video composition
- `src/image_service.py` - SDXL image generation
- `src/update_clients.py` - Issue parsing
- `.github/workflows/` - CI/CD automation
