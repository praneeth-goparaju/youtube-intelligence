# Firebase Functions - Recommendation API

Serverless API endpoints for the YouTube Intelligence System recommendation engine.

## Overview

This module provides Firebase Cloud Functions that expose the recommendation engine as:
- **HTTP REST API** - For any client (web, mobile, scripts)
- **Callable Function** - For Firebase SDK integration

## Quick Start

### Prerequisites

- Node.js 20+
- Firebase CLI (`npm install -g firebase-tools`)
- Firebase project with Firestore and Functions enabled

### Installation

```bash
cd functions
npm install
```

### Configuration

Set the Gemini API key:

```bash
# Using Firebase CLI
firebase functions:secrets:set GOOGLE_API_KEY

# Or using .env.local for emulator
echo "GOOGLE_API_KEY=your_api_key" > .env.local
```

### Local Development

```bash
# Start the emulator
npm run serve

# Test the endpoint
curl -X POST http://localhost:5001/PROJECT_ID/us-central1/recommend \
  -H "Content-Type: application/json" \
  -d '{"topic": "Biryani", "type": "recipe"}'
```

### Deploy

```bash
# Deploy functions
npm run deploy

# Or from project root
firebase deploy --only functions
```

## API Endpoints

### POST /recommend

Generate video recommendations.

**Request:**
```json
{
  "topic": "Hyderabadi Biryani",
  "type": "recipe",
  "angle": "Restaurant secret recipe",
  "audience": "Telugu home cooks"
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `topic` | string | Yes | - | Video topic |
| `type` | string | No | `recipe` | Content type: `recipe`, `vlog`, `tutorial`, `review`, `challenge` |
| `angle` | string | No | - | Unique positioning angle |
| `audience` | string | No | `Telugu audience` | Target audience |

**Response:**
```json
{
  "titles": {
    "primary": {
      "english": "Restaurant Style Hyderabadi Biryani | BEST Recipe",
      "telugu": "హోటల్ స్టైల్ హైదరాబాదీ బిర్యానీ",
      "combined": "Hyderabadi Biryani | హైదరాబాదీ బిర్యానీ | Restaurant Style",
      "predictedCTR": "above-average",
      "reasoning": "Combines high-search keyword with quality modifier"
    },
    "alternatives": [...]
  },
  "thumbnail": {
    "layout": {...},
    "elements": {...},
    "colors": {...}
  },
  "tags": {
    "primary": ["biryani recipe", "hyderabadi biryani"],
    "secondary": [...],
    "telugu": ["బిర్యానీ", "హైదరాబాదీ బిర్యానీ"],
    "longtail": [...]
  },
  "posting": {
    "bestDay": "Saturday",
    "bestTime": "18:00 IST",
    "alternativeTimes": [...],
    "reasoning": "Based on analysis of 50000 videos..."
  },
  "prediction": {
    "expectedViewRange": {"low": 10000, "medium": 50000, "high": 200000},
    "confidence": "medium",
    "positiveFactors": [...],
    "riskFactors": [...]
  },
  "content": {...},
  "metadata": {
    "generatedAt": "2024-01-25T10:30:00Z",
    "modelUsed": "gemini-2.0-flash",
    "insightsVersion": "2024-01-20T00:00:00Z",
    "fallbackUsed": false
  }
}
```

**Example cURL:**
```bash
curl -X POST https://us-central1-YOUR_PROJECT.cloudfunctions.net/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Chicken Biryani",
    "type": "recipe",
    "angle": "Secret restaurant recipe",
    "audience": "Telugu home cooks"
  }'
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2024-01-25T10:30:00Z",
  "version": "1.0.0"
}
```

### Callable Function: getRecommendation

For Firebase SDK integration.

**JavaScript/TypeScript:**
```typescript
import { getFunctions, httpsCallable } from 'firebase/functions';

const functions = getFunctions();
const getRecommendation = httpsCallable(functions, 'getRecommendation');

const result = await getRecommendation({
  topic: 'Biryani',
  type: 'recipe',
  angle: 'Restaurant secret',
  audience: 'Telugu home cooks'
});

console.log(result.data);
```

**Flutter/Dart:**
```dart
final callable = FirebaseFunctions.instance.httpsCallable('getRecommendation');
final result = await callable.call({
  'topic': 'Biryani',
  'type': 'recipe',
});
print(result.data);
```

## Architecture

```
functions/
├── src/
│   ├── index.ts         # Function definitions (HTTP, callable)
│   ├── engine.ts        # Recommendation engine
│   ├── firebase.ts      # Firestore client for insights
│   ├── gemini.ts        # Gemini AI client
│   ├── templates.ts     # Fallback templates
│   └── types.ts         # TypeScript interfaces
├── package.json
├── tsconfig.json
└── README.md
```

## How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  Firebase   │────▶│   Engine    │
│  Request    │     │  Function   │     │             │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
            ┌─────────────┐           ┌─────────────┐           ┌─────────────┐
            │  Firestore  │           │   Gemini    │           │  Templates  │
            │  Insights   │           │     AI      │           │  (Fallback) │
            └─────────────┘           └─────────────┘           └─────────────┘
```

1. **Request received** - HTTP or callable function
2. **Load insights** - Fetch from Firestore (if available)
3. **Build context** - Format insights for AI prompt
4. **Generate with AI** - Call Gemini for creative recommendations
5. **Fallback** - Use templates if AI fails or no insights
6. **Return response** - Complete recommendation JSON

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Gemini API key | Yes |

### Function Settings

Configured in `index.ts`:

```typescript
setGlobalOptions({
  region: 'us-central1',
  memory: '1GiB',
  timeoutSeconds: 60,
});
```

### CORS

CORS is enabled for the HTTP endpoint to allow web clients.

## Error Handling

### HTTP Errors

| Status | Meaning |
|--------|---------|
| 400 | Invalid request (missing topic, invalid type) |
| 405 | Method not allowed (use POST) |
| 500 | Internal error (AI failed, Firebase error) |

### Callable Errors

| Code | Meaning |
|------|---------|
| `invalid-argument` | Missing or invalid parameters |
| `internal` | Server-side error |

## Testing

### Local Testing

```bash
# Start emulator
npm run serve

# Run tests
npm test
```

### Manual Testing

```bash
# Health check
curl http://localhost:5001/PROJECT_ID/us-central1/health

# Generate recommendation
curl -X POST http://localhost:5001/PROJECT_ID/us-central1/recommend \
  -H "Content-Type: application/json" \
  -d '{"topic": "Test Recipe"}'
```

## Deployment

### First Deployment

```bash
# Login to Firebase
firebase login

# Select project
firebase use YOUR_PROJECT_ID

# Set API key
firebase functions:secrets:set GOOGLE_API_KEY

# Deploy
npm run deploy
```

### Update Deployment

```bash
npm run deploy
```

### View Logs

```bash
npm run logs

# Or specific function
firebase functions:log --only recommend
```

## Pricing

Firebase Functions pricing (as of 2024):

| Resource | Free Tier | Cost After |
|----------|-----------|------------|
| Invocations | 2M/month | $0.40/million |
| GB-seconds | 400K/month | $0.0000025/GB-s |
| Networking | 5 GB/month | $0.12/GB |

**Estimated cost for this function:**
- ~5-10 second execution time
- ~1 GB memory
- Cost per request: ~$0.000025-0.00005

## Troubleshooting

### "GOOGLE_API_KEY not configured"

```bash
# Set the secret
firebase functions:secrets:set GOOGLE_API_KEY

# Verify
firebase functions:secrets:access GOOGLE_API_KEY
```

### "Missing or insufficient permissions"

- Verify Firebase project has Firestore enabled
- Check that insights collection exists (run Phase 3 first)
- Verify function has access to Firestore

### Cold Start Latency

First request after deployment may take 5-10 seconds. Subsequent requests are faster (~2-5 seconds).

### Rate Limits

If you see 429 errors:
- Gemini free tier: 60 requests/minute
- Consider upgrading to paid tier for production

## Integration Examples

### React/Next.js

```typescript
// lib/recommendations.ts
const API_URL = 'https://us-central1-PROJECT.cloudfunctions.net/recommend';

export async function getRecommendation(topic: string, type: string = 'recipe') {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, type }),
  });

  if (!response.ok) {
    throw new Error('Failed to get recommendation');
  }

  return response.json();
}
```

### Python

```python
import requests

def get_recommendation(topic: str, content_type: str = 'recipe'):
    url = 'https://us-central1-PROJECT.cloudfunctions.net/recommend'
    response = requests.post(url, json={
        'topic': topic,
        'type': content_type,
    })
    response.raise_for_status()
    return response.json()
```

---

For more details, see the [main documentation](../README.md).
