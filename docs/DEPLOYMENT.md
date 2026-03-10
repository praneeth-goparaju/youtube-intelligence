# Deployment Guide

Complete guide for deploying the YouTube Intelligence System in various environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Production Deployment](#production-deployment)
4. [Cloud Deployment Options](#cloud-deployment-options)
5. [Environment Configuration](#environment-configuration)
6. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Prerequisites

### Required Services

| Service | Purpose | Setup Link |
|---------|---------|------------|
| YouTube Data API v3 | Video data collection | [Google Cloud Console](https://console.cloud.google.com/apis/library/youtube.googleapis.com) |
| Firebase | Database & Storage | [Firebase Console](https://console.firebase.google.com) |
| Google AI (Gemini) | AI analysis | [Google AI Studio](https://aistudio.google.com/app/apikey) |

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Node.js | 18.x | 20.x LTS |
| Python | 3.11 | 3.12 |
| RAM | 4 GB | 8 GB |
| Storage | 10 GB | 50 GB |
| Network | Stable connection | Low latency |

---

## Local Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/tranquillity-hub/youtube_channel_analysis.git
cd youtube_channel_analysis
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# YouTube API
YOUTUBE_API_KEY=AIzaSy...

# Firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxx@your-project.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n"
FIREBASE_STORAGE_BUCKET=your-project.appspot.com

# Gemini API
GOOGLE_API_KEY=AIzaSy...

# Optional Settings
API_DELAY_MS=100
QUOTA_WARNING_THRESHOLD=500
REQUEST_DELAY=0.5
```

### 3. Install Dependencies

```bash
# Scraper (TypeScript)
cd scraper
npm install

# Analyzer (Python)
cd ../analyzer
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Insights (Python)
cd ../insights
pip install -r requirements.txt

# Recommender (TypeScript)
cd ../functions
npm install
```

### 4. Validate Setup

```bash
# Test YouTube API and Firebase
cd scraper
npx tsx scripts/validate.ts

# Test Gemini API
cd ../analyzer
python -m src.main --validate
```

### 5. Run the Pipeline

```bash
# Phase 1: Scrape data
cd scraper
npm start

# Phase 2: Analyze (after scraping)
cd ../analyzer
python -m src.main

# Phase 3: Generate insights
cd ../insights
python -m src.main

# Phase 4: Get recommendations
cd ../functions
npm run recommend -- --topic "Test Recipe"
```

---

## Production Deployment

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PRODUCTION ARCHITECTURE                           │
└─────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │   Scheduler     │
                    │  (Cron/Cloud)   │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│    Scraper    │   │   Analyzer    │   │   Insights    │
│   (Node.js)   │   │   (Python)    │   │   (Python)    │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                  ┌─────────────────┐
                  │    Firebase     │
                  │ Firestore + GCS │
                  └─────────────────┘
                            │
                            ▼
                  ┌─────────────────┐
                  │  Recommender    │
                  │  (API/CLI)      │
                  └─────────────────┘
```

### Server Setup (Linux)

#### 1. System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install Python 3.11+
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install PM2 for process management
sudo npm install -g pm2
```

#### 2. Application Setup

```bash
# Create app directory
sudo mkdir -p /opt/youtube-intelligence
sudo chown $USER:$USER /opt/youtube-intelligence

# Clone repository
cd /opt/youtube-intelligence
git clone https://github.com/tranquillity-hub/youtube_channel_analysis.git .

# Install dependencies
cd scraper && npm install --production
cd ../analyzer && python3.11 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cd ../insights && pip install -r requirements.txt
cd ../functions && npm install --production
```

#### 3. Environment Configuration

```bash
# Create production .env
sudo nano /opt/youtube-intelligence/.env

# Set permissions
chmod 600 /opt/youtube-intelligence/.env
```

#### 4. PM2 Configuration

Create `ecosystem.config.js`:

```javascript
module.exports = {
  apps: [
    {
      name: 'yt-scraper',
      cwd: '/opt/youtube-intelligence/scraper',
      script: 'npm',
      args: 'start',
      env: {
        NODE_ENV: 'production'
      },
      cron_restart: '0 1 * * *',  // Run daily at 1 AM
      autorestart: false
    },
    {
      name: 'yt-analyzer',
      cwd: '/opt/youtube-intelligence/analyzer',
      script: 'venv/bin/python',
      args: 'src/main.py',
      env: {
        PYTHONUNBUFFERED: '1'
      },
      cron_restart: '0 6 * * *',  // Run daily at 6 AM
      autorestart: false
    },
    {
      name: 'yt-insights',
      cwd: '/opt/youtube-intelligence/insights',
      script: '../analyzer/venv/bin/python',
      args: 'src/main.py',
      cron_restart: '0 12 * * 0',  // Run weekly on Sunday
      autorestart: false
    }
  ]
};
```

#### 5. Start Services

```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### Scheduled Execution

#### Using Cron

```bash
# Edit crontab
crontab -e

# Add schedules
# Scraper: Daily at 1 AM (after quota reset)
0 1 * * * cd /opt/youtube-intelligence/scraper && npm start >> /var/log/yt-scraper.log 2>&1

# Analyzer: Daily at 6 AM
0 6 * * * cd /opt/youtube-intelligence/analyzer && source ../venv/bin/activate && python -m src.main >> /var/log/yt-analyzer.log 2>&1

# Insights: Weekly on Sunday at noon
0 12 * * 0 cd /opt/youtube-intelligence/insights && source ../venv/bin/activate && python -m src.main >> /var/log/yt-insights.log 2>&1
```

---

## Cloud Deployment Options

### Option 1: Google Cloud Run

#### Scraper Dockerfile

```dockerfile
# scraper/Dockerfile
FROM node:20-slim

WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY . .

CMD ["npm", "start"]
```

#### Analyzer Dockerfile

```dockerfile
# analyzer/Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "src/main.py"]
```

#### Deploy to Cloud Run

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/yt-scraper scraper/
gcloud builds submit --tag gcr.io/PROJECT_ID/yt-analyzer analyzer/

# Deploy
gcloud run deploy yt-scraper \
  --image gcr.io/PROJECT_ID/yt-scraper \
  --memory 2Gi \
  --timeout 3600 \
  --set-env-vars "$(cat .env | xargs)"

gcloud run deploy yt-analyzer \
  --image gcr.io/PROJECT_ID/yt-analyzer \
  --memory 4Gi \
  --timeout 3600 \
  --set-env-vars "$(cat .env | xargs)"
```

### Option 2: AWS Lambda + Step Functions

Use AWS Step Functions to orchestrate the pipeline:

```json
{
  "StartAt": "RunScraper",
  "States": {
    "RunScraper": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:yt-scraper",
      "Next": "WaitForScraper",
      "Retry": [{"ErrorEquals": ["QuotaExceeded"], "IntervalSeconds": 86400}]
    },
    "WaitForScraper": {
      "Type": "Wait",
      "Seconds": 3600,
      "Next": "RunAnalyzer"
    },
    "RunAnalyzer": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:yt-analyzer",
      "Next": "RunInsights"
    },
    "RunInsights": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:yt-insights",
      "End": true
    }
  }
}
```

### Option 3: GitHub Actions

Create `.github/workflows/pipeline.yml`:

```yaml
name: YouTube Intelligence Pipeline

on:
  schedule:
    - cron: '0 1 * * *'  # Daily at 1 AM UTC
  workflow_dispatch:

jobs:
  scraper:
    runs-on: ubuntu-latest
    timeout-minutes: 120
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: cd scraper && npm ci

      - name: Run scraper
        env:
          YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
          FIREBASE_PROJECT_ID: ${{ secrets.FIREBASE_PROJECT_ID }}
          FIREBASE_CLIENT_EMAIL: ${{ secrets.FIREBASE_CLIENT_EMAIL }}
          FIREBASE_PRIVATE_KEY: ${{ secrets.FIREBASE_PRIVATE_KEY }}
          FIREBASE_STORAGE_BUCKET: ${{ secrets.FIREBASE_STORAGE_BUCKET }}
        run: cd scraper && npm start

  analyzer:
    needs: scraper
    runs-on: ubuntu-latest
    timeout-minutes: 240
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run analyzer
        env:
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
          FIREBASE_PROJECT_ID: ${{ secrets.FIREBASE_PROJECT_ID }}
          FIREBASE_CLIENT_EMAIL: ${{ secrets.FIREBASE_CLIENT_EMAIL }}
          FIREBASE_PRIVATE_KEY: ${{ secrets.FIREBASE_PRIVATE_KEY }}
          FIREBASE_STORAGE_BUCKET: ${{ secrets.FIREBASE_STORAGE_BUCKET }}
        run: cd analyzer && python -m src.main

  insights:
    needs: analyzer
    if: github.event.schedule == '0 12 * * 0'  # Only on Sundays
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Generate insights
        env:
          FIREBASE_PROJECT_ID: ${{ secrets.FIREBASE_PROJECT_ID }}
          FIREBASE_CLIENT_EMAIL: ${{ secrets.FIREBASE_CLIENT_EMAIL }}
          FIREBASE_PRIVATE_KEY: ${{ secrets.FIREBASE_PRIVATE_KEY }}
        run: cd insights && python -m src.main
```

---

## Environment Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `YOUTUBE_API_KEY` | YouTube Data API v3 key | `AIzaSy...` |
| `FIREBASE_PROJECT_ID` | Firebase project ID | `my-project-123` |
| `FIREBASE_CLIENT_EMAIL` | Service account email | `firebase-adminsdk@...` |
| `FIREBASE_PRIVATE_KEY` | Service account private key | `-----BEGIN PRIVATE KEY-----...` |
| `FIREBASE_STORAGE_BUCKET` | Storage bucket name | `my-project.appspot.com` |
| `GOOGLE_API_KEY` | Gemini API key | `AIzaSy...` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_DELAY_MS` | `100` | Delay between YouTube API calls |
| `QUOTA_WARNING_THRESHOLD` | `500` | Stop when quota reaches this level |
| `REQUEST_DELAY` | `0.5` | Delay between Gemini API calls |
| `BATCH_SIZE` | `10` | Videos per analysis batch |

### Secrets Management

#### Using Environment Files

```bash
# Never commit .env files
echo ".env" >> .gitignore
echo ".env.*" >> .gitignore

# Use .env.example as template
cp .env.example .env
```

#### Using Cloud Secret Manager

```bash
# Google Secret Manager
gcloud secrets create youtube-api-key --data-file=<(echo -n "YOUR_KEY")
gcloud secrets create firebase-credentials --data-file=firebase-credentials.json

# Access in code
gcloud secrets versions access latest --secret=youtube-api-key
```

---

## Monitoring & Maintenance

### Logging

#### Scraper Logs

```bash
# PM2 logs
pm2 logs yt-scraper

# Log file
tail -f /var/log/yt-scraper.log
```

#### Log Levels

Set `LOG_LEVEL` environment variable:
- `DEBUG`: Verbose output
- `INFO`: Standard output (default)
- `WARN`: Warnings only
- `ERROR`: Errors only

### Health Checks

#### Check Progress

```bash
# View scrape progress in Firestore
firebase firestore:get scrape_progress --project=YOUR_PROJECT

# Check analysis progress
python -c "
from src.firebase_client import get_analysis_progress
print(get_analysis_progress())
"
```

#### API Health

```bash
# Test YouTube API
curl "https://www.googleapis.com/youtube/v3/channels?part=id&id=UC_x5XG1OV2P6uZZ5FSM9Ttw&key=YOUR_API_KEY"

# Test Gemini API
curl "https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_API_KEY"
```

### Backup

#### Firestore Backup

```bash
# Export to Cloud Storage
gcloud firestore export gs://YOUR_BUCKET/backups/$(date +%Y%m%d)
```

#### Scheduled Backups

```bash
# Add to crontab
0 0 * * * gcloud firestore export gs://backup-bucket/firestore/$(date +\%Y\%m\%d) --async
```

### Alerting

#### Setup Alerts (Google Cloud)

```bash
# Create alert policy for errors
gcloud monitoring policies create \
  --policy-from-file=alert-policy.yaml
```

Example `alert-policy.yaml`:

```yaml
displayName: "YouTube Scraper Errors"
conditions:
  - displayName: "Error Rate"
    conditionThreshold:
      filter: 'resource.type="cloud_run_revision" AND metric.type="logging.googleapis.com/user/error_count"'
      comparison: COMPARISON_GT
      thresholdValue: 10
      duration: "300s"
notificationChannels:
  - projects/PROJECT_ID/notificationChannels/CHANNEL_ID
```

### Maintenance Tasks

#### Weekly

- Check quota usage in Google Cloud Console
- Review error logs
- Verify progress tracking is working

#### Monthly

- Update dependencies (`npm update`, `pip install --upgrade`)
- Review storage usage
- Clean up old progress documents

#### Quarterly

- Rotate API keys
- Review and update channel list
- Regenerate insights with fresh data

---

## Troubleshooting Production Issues

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Scraper stops daily | Quota exhausted | Normal - resumes next day |
| Firebase timeout | Large batch writes | Reduce batch size |
| Memory errors | Too many videos in memory | Process in smaller chunks |
| Gemini rate limits | Too fast requests | Wait and retry; delay is hardcoded at 0.5s in `analyzer/src/config.py` |

### Recovery Procedures

#### Reset Stuck Progress

```bash
# Clear progress for a specific channel
firebase firestore:delete scrape_progress/CHANNEL_ID --project=YOUR_PROJECT

# Clear all progress
firebase firestore:delete scrape_progress --recursive --project=YOUR_PROJECT
```

#### Reprocess Failed Videos

```bash
# Re-run analyzer for a specific channel
cd analyzer && python -m src.main --type thumbnail --channel CHANNEL_ID
```

---

For API details, see [API Reference](API_REFERENCE.md).
For troubleshooting, see [Troubleshooting Guide](TROUBLESHOOTING.md).
