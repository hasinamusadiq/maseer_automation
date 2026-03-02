name: Maseer Daily Campaign Pipeline - 4 Scheduled Runs

on:
  schedule:
    # Kabul Time (UTC+4:30): 6:00, 12:00, 18:00, 00:00
    # UTC: 1:30, 7:30, 13:30, 19:30
    - cron: '30 1,7,13,19 * * *'
  workflow_dispatch:
    inputs:
      campaign_type:
        description: 'Force specific campaign (morning/midday/evening/night)'
        required: false
        type: choice
        options:
          - auto
          - morning
          - midday
          - evening
          - night

jobs:
  generate-campaign:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Create Required Directories
        run: |
          mkdir -p data logos output
          ls -la data/ || echo "Fresh start"

      - name: Restore Client Data
        uses: actions/cache@v3
        with:
          path: data/clients.json
          key: clients-data-${{ github.run_id }}
          restore-keys: clients-data-

      - name: Install System Dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            imagemagick \
            ghostscript \
            fonts-dejavu \
            fonts-freefont-ttf \
            fonts-noto \
            ffmpeg \
            libimagequant-dev \
            wget

      - name: Download Noto Arabic Fonts
        run: |
          mkdir -p ~/.fonts
          cd ~/.fonts
          wget -q "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoNaskhArabic/NotoNaskhArabic-Regular.ttf" || true
          wget -q "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoNaskhArabic/NotoNaskhArabic-Bold.ttf" || true
          wget -q "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Regular.ttf" || true
          fc-cache -f || true
          echo "Fonts downloaded"

      - name: Configure ImageMagick
        run: |
          sudo mkdir -p /etc/ImageMagick-6
          sudo tee /etc/ImageMagick-6/policy.xml > /dev/null << 'EOF'
          <?xml version="1.0" encoding="UTF-8"?>
          <policymap>
            <policy domain="resource" name="memory" value="1GiB"/>
            <policy domain="resource" name="map" value="2GiB"/>
            <policy domain="resource" name="width" value="32KP"/>
            <policy domain="resource" name="height" value="32KP"/>
            <policy domain="resource" name="area" value="256MP"/>
            <policy domain="resource" name="disk" value="4GiB"/>
            <policy domain="coder" rights="read|write" pattern="*" />
            <policy domain="path" rights="read|write" pattern="@*" />
          </policymap>
          EOF

      - name: Install Python Dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt

      - name: Determine Campaign Type
        id: campaign
        run: |
          if [ "${{ github.event.inputs.campaign_type }}" != "" ] && [ "${{ github.event.inputs.campaign_type }}" != "auto" ]; then
            echo "type=${{ github.event.inputs.campaign_type }}" >> $GITHUB_OUTPUT
          else
            # Auto-determine from UTC hour
            HOUR=$(date -u +%H)
            MIN=$(date -u +%M)
            UTC_TIME="${HOUR}${MIN}"
            
            # UTC times: 0130, 0730, 1330, 1930
            case $UTC_TIME in
              0130|01*) echo "type=morning" >> $GITHUB_OUTPUT ;;
              0730|07*) echo "type=midday" >> $GITHUB_OUTPUT ;;
              1330|13*) echo "type=evening" >> $GITHUB_OUTPUT ;;
              1930|19*) echo "type=night" >> $GITHUB_OUTPUT ;;
              *) echo "type=morning" >> $GITHUB_OUTPUT ;;
            esac
          fi
          
          echo "📅 Campaign Type: $(cat $GITHUB_OUTPUT | grep type= | cut -d= -f2)"
          echo "🕐 Current UTC: $(date -u '+%Y-%m-%d %H:%M')"

      - name: Run Campaign Pipeline
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          PAT_TOKEN: ${{ secrets.PAT_TOKEN }}
          CAMPAIGN_TYPE: ${{ steps.campaign.outputs.type }}
        run: |
          echo "🎬 Starting Maseer Campaign Pipeline"
          echo "Campaign: ${CAMPAIGN_TYPE}"
          python src/main.py --campaign ${CAMPAIGN_TYPE}

      - name: Upload Campaign Videos
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: campaign-${{ steps.campaign.outputs.type }}-${{ github.run_id }}
          path: output/*.mp4
          retention-days: 14

      - name: Commit Updated Data
        if: always()
        run: |
          git config --local user.email "maseer@automation.bot"
          git config --local user.name "Maseer Campaign Bot"
          git add data/clients.json
          git diff --cached --quiet || git commit -m "📊 ${CAMPAIGN_TYPE} campaign complete [skip ci]"
          git push || echo "No changes"

      - name: Notify Completion
        if: always()
        run: |
          echo "✅ Campaign pipeline complete"
          ls -lh output/ || echo "No output directory"
