# Phase 4: Recommendation Engine

The recommendation engine for the YouTube Intelligence System. Generates data-driven video recommendations based on discovered patterns and AI.

## Overview

This module provides the recommendation engine with two usage options:

| Usage | Best For | Command |
|-------|----------|---------|
| **CLI** | Local development, scripts, batch processing | `npm run recommend -- --topic "Biryani"` |
| **API** | Web apps, mobile apps, serverless | `POST /recommend` or `httpsCallable` |

Both use the same engine and produce identical recommendations.

## Quick Start (CLI)

```bash
cd functions
npm install

# Run a recommendation
npm run recommend -- --topic "Biryani" --type recipe

# With all options
npm run recommend -- --topic "Biryani" --type recipe --angle "Secret recipe" --output result.json

# Show help
npm run recommend -- --help
```

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--topic, -t` | Video topic (required) | - |
| `--type` | Content type: recipe, vlog, tutorial, review, challenge | recipe |
| `--angle, -a` | Unique positioning angle | - |
| `--audience` | Target audience | Telugu audience (configurable) |
| `--output, -o` | Save to JSON file | stdout |
| `--no-thumbnail` | Skip AI thumbnail generation | false |
| `--ideas, -i` | Generate data-backed video ideas | false |

### Environment Variables

See [Deployment Guide](../docs/DEPLOYMENT.md) for full environment variable reference.

> The default audience reflects the system's original use case. Pass `--audience "Your audience"` to customize.

## Quick Start (API)

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

## Authentication

All API endpoints (except `/health`) require authentication:

```bash
# Required header
Authorization: Bearer YOUR_API_KEY
```

Set the API key as a Firebase secret:
```bash
firebase functions:secrets:set RECOMMEND_API_KEY
```

Rate limiting: 100 requests per hour per API key.

## API Endpoints

### POST /recommend

Generate video recommendations.

**Request:**
```json
{
  "topic": "Hyderabadi Biryani",
  "type": "recipe",
  "angle": "Restaurant secret recipe",
  "audience": "Home cooks"
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `topic` | string | Yes | - | Video topic |
| `type` | string | No | `recipe` | Content type: `recipe`, `vlog`, `tutorial`, `review`, `challenge` |
| `angle` | string | No | - | Unique positioning angle |
| `audience` | string | No | `Telugu audience` | Target audience (configurable) |

**Response:**

> Fields named `telugu` reflect the system's built-in bilingual support. These contain localized content for the configured target language.

```json
{
  "titles": {
    "primary": {
      "english": "Restaurant Style Hyderabadi Biryani | BEST Recipe",
      "telugu": "(localized title in target language)",
      "combined": "Hyderabadi Biryani | (localized) | Restaurant Style",
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
    "telugu": ["(localized tags in target language)"],
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
    "modelUsed": "gemini-2.5-flash",
    "insightsVersion": "2024-01-20T00:00:00Z",
    "fallbackUsed": false
  }
}
```

**Example cURL:**
```bash
curl -X POST https://us-central1-YOUR_PROJECT.cloudfunctions.net/recommend \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "topic": "Chicken Biryani",
    "type": "recipe",
    "angle": "Secret restaurant recipe",
    "audience": "Home cooks"
  }'
```

### POST /ideas

Generate data-backed video ideas.

**Request:**
```json
{
  "type": "recipe"
}
```

### POST /generations-save

Save a generation result.

### GET /generations-list

List saved generations.

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
  audience: 'Food enthusiasts'
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
│   ├── cli.ts                  # CLI entry point (local usage)
│   ├── index.ts                # Firebase Function definitions (API)
│   ├── engine.ts               # Recommendation engine (API)
│   ├── recommendation-core.ts  # Shared recommendation logic
│   ├── firebase.ts             # Firestore client for insights
│   ├── gemini.ts               # Gemini AI client
│   ├── templates.ts            # Fallback templates
│   ├── types.ts                # TypeScript interfaces
│   ├── rate-limiter.ts         # Firestore-based distributed rate limiting
│   ├── formatter.ts            # Output formatting
│   └── thumbnail-gen.ts        # AI thumbnail generation
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

See [Deployment Guide](../docs/DEPLOYMENT.md) for full environment variable reference.

For Firebase Functions deployment, set secrets via `firebase functions:secrets:set` (see [Authentication](#authentication)).

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
| 401 | Unauthorized (missing or invalid API key) |
| 405 | Method not allowed (use POST) |
| 429 | Rate limit exceeded (100 requests/hour) |
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

# Generate recommendation (auth required even on emulator)
curl -X POST http://localhost:5001/PROJECT_ID/us-central1/recommend \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
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
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${process.env.RECOMMEND_API_KEY}`,
    },
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

def get_recommendation(topic: str, content_type: str = 'recipe', api_key: str = ''):
    url = 'https://us-central1-PROJECT.cloudfunctions.net/recommend'
    response = requests.post(url, json={
        'topic': topic,
        'type': content_type,
    }, headers={
        'Authorization': f'Bearer {api_key}',
    })
    response.raise_for_status()
    return response.json()
```

## Related Documentation

- [Deployment Guide](../docs/DEPLOYMENT.md) — Environment setup and deployment
- [API Reference](../docs/API_REFERENCE.md) — Programmatic interface documentation
- [Troubleshooting](../docs/TROUBLESHOOTING.md#phase-4-recommender-issues) — Common recommender issues
- [Root README](../README.md) — Project overview
