# Troubleshooting Guide

Common issues and solutions for the YouTube Intelligence System.

## Table of Contents

1. [Phase 1: Scraper Issues](#phase-1-scraper-issues)
2. [Phase 2: Analyzer Issues](#phase-2-analyzer-issues)
3. [Phase 3: Insights Issues](#phase-3-insights-issues)
4. [Phase 4: Recommender Issues](#phase-4-recommender-issues)
5. [Firebase Issues](#firebase-issues)
6. [API Issues](#api-issues)
7. [Performance Issues](#performance-issues)

---

## Phase 1: Scraper Issues

### Quota Exceeded

**Symptoms:**
```
Error: quotaExceeded - The request cannot be completed because you have exceeded your quota.
```

**Cause:** YouTube API daily quota (10,000 units) exhausted.

**Solution:**
1. This is normal behavior - the scraper saves progress automatically
2. Wait until midnight Pacific Time (quota resets)
3. Run the scraper again - it will resume from where it stopped

**Prevention:**
- Avoid using `search.list` (100 units each)
- Use `@handle` URLs instead of `/c/` URLs
- Set `QUOTA_WARNING_THRESHOLD=500` to stop earlier

### Channel Not Found

**Symptoms:**
```
Error: channelNotFound - The channel specified in the channel parameter cannot be found.
```

**Cause:** Invalid channel URL, deleted channel, or wrong format.

**Solution:**
1. Verify the URL works in a browser
2. Check URL format is supported:
   - `@handle` ✓
   - `/channel/UCxxx` ✓
   - `/user/name` ✓
   - `/c/name` ✓ (but expensive)
3. Update `config/channels.json` to remove invalid URLs

### Progress Not Resuming

**Symptoms:**
- Scraper starts from beginning instead of resuming
- Duplicate videos in database

**Cause:** Corrupted or missing progress document.

**Solution:**
```bash
# Check progress document
firebase firestore:get scrape_progress/CHANNEL_ID

# Reset progress for specific channel
npx tsx scripts/reset-progress.ts --channel CHANNEL_ID

# Reset all progress (start fresh)
npx tsx scripts/reset-progress.ts --all
```

### Thumbnail Download Failures

**Symptoms:**
```
Warning: Failed to download thumbnail for video XXX
```

**Cause:** Network issue, YouTube CDN temporary failure, or video deleted.

**Solution:**
1. Thumbnails are retried automatically (3 attempts)
2. Check if video still exists on YouTube
3. Run scraper again - it will retry failed thumbnails
4. Check Firebase Storage permissions

### Firebase Permission Denied

**Symptoms:**
```
Error: 7 PERMISSION_DENIED: Missing or insufficient permissions
```

**Cause:** Invalid Firebase credentials or Firestore security rules.

**Solution:**
1. Verify environment variables:
   ```bash
   echo $FIREBASE_PROJECT_ID
   echo $FIREBASE_CLIENT_EMAIL
   ```
2. Check `FIREBASE_PRIVATE_KEY` includes newlines (`\n`)
3. Verify Firestore rules allow service account access
4. Regenerate service account JSON if needed

---

## Phase 2: Analyzer Issues

### Gemini Rate Limit

**Symptoms:**
```
Error: 429 Resource has been exhausted (e.g. check quota).
```

**Cause:** Too many requests to Gemini API.

**Solution:**
1. Increase `REQUEST_DELAY` in environment:
   ```bash
   REQUEST_DELAY=1.0  # or higher
   ```
2. Reduce batch size:
   ```bash
   BATCH_SIZE=5
   ```
3. Wait a few minutes and retry

### Invalid JSON from Gemini

**Symptoms:**
```
Error: JSONDecodeError: Expecting value
```

**Cause:** Gemini returned non-JSON response.

**Solution:**
1. Automatic retry handles most cases (3 attempts)
2. If persistent, check prompt formatting in `src/prompts/`
3. Verify Gemini API key is valid
4. Try with smaller batch size

### Thumbnail Not Found

**Symptoms:**
```
Error: Thumbnail not found at path: thumbnails/UCxxx/videoId.jpg
```

**Cause:** Thumbnail wasn't downloaded in Phase 1.

**Solution:**
1. Verify scraper completed for that channel
2. Check Firebase Storage for the file
3. Re-run scraper for specific channel:
   ```bash
   # Clear progress and re-scrape
   npx tsx scripts/reset-progress.ts --channel UCxxx
   npm start
   ```

### Analysis Stuck or Slow

**Symptoms:**
- Progress bar not moving
- Very slow processing

**Cause:** Large videos queue, rate limiting, or memory issues.

**Solution:**
1. Process smaller batches:
   ```bash
   python src/main.py --type thumbnail --limit 100
   ```
2. Process one channel at a time:
   ```bash
   python src/main.py --channel UCxxx --limit 50
   ```
3. Increase delay to prevent rate limits:
   ```bash
   REQUEST_DELAY=2.0
   ```

### Memory Error

**Symptoms:**
```
MemoryError: Unable to allocate array
```

**Cause:** Too many videos loaded in memory.

**Solution:**
1. Process in smaller batches
2. Restart with fresh memory
3. Use `--limit` flag to reduce videos per run
4. Increase system swap space

---

## Phase 3: Insights Issues

### Not Enough Data

**Symptoms:**
```
Warning: Not enough videos for meaningful profiling
```

**Cause:** Phase 2 didn't complete enough videos, or a content type has too few videos.

**Solution:**
1. Check analysis progress — both thumbnail and title_description analysis should be complete
2. Complete more Phase 2 analysis
3. Content types with very few videos will be skipped automatically

### Insights Not Generating

**Symptoms:**
- Empty insights documents
- Missing content type profiles

**Cause:** Analysis data missing or in wrong format.

**Solution:**
1. Verify Phase 2 completed:
   ```bash
   # Check for analysis documents
   firebase firestore:get channels/UCxxx/videos/videoId/analysis/thumbnail
   firebase firestore:get channels/UCxxx/videos/videoId/analysis/title_description
   ```
2. Re-run insights with verbose mode:
   ```bash
   LOG_LEVEL=DEBUG python src/main.py
   ```
3. Run specific insight type:
   ```bash
   python src/main.py --type profiles  # Per-content-type profiles only
   python src/main.py --type gaps      # Content gap analysis only
   ```

---

## Phase 4: Recommender Issues

### No Insights Available

**Symptoms:**
```
Warning: No insights found, using template-based generation
```

**Cause:** Phase 3 insights not generated.

**Solution:**
1. Run Phase 3 first:
   ```bash
   cd insights && python src/main.py
   ```
2. Verify insights in Firestore:
   ```bash
   firebase firestore:get insights/summary
   ```

### AI Generation Failing

**Symptoms:**
- Only template-based recommendations
- Error logs show Gemini failures

**Cause:** Gemini API issues.

**Solution:**
1. Verify API key:
   ```bash
   curl "https://generativelanguage.googleapis.com/v1beta/models?key=$GOOGLE_API_KEY"
   ```
2. Check quota in Google Cloud Console
3. Template fallback still provides useful recommendations

### Poor Recommendations

**Symptoms:**
- Generic or irrelevant suggestions
- Not Telugu-specific

**Cause:** Insufficient data or context.

**Solution:**
1. Ensure enough Telugu channels analyzed
2. Verify insights contain relevant patterns
3. Provide more specific input:
   ```bash
   npm run recommend -- \
     --topic "Hyderabadi Biryani" \
     --type recipe \
     --angle "Restaurant secret" \
     --audience "Telugu home cooks"
   ```

---

## Firebase Issues

### Connection Timeout

**Symptoms:**
```
Error: 14 UNAVAILABLE: Connection timeout
```

**Cause:** Network issues or Firebase outage.

**Solution:**
1. Check internet connection
2. Verify Firebase status: https://status.firebase.google.com
3. Retry after a few minutes
4. Check firewall settings

### Private Key Format Error

**Symptoms:**
```
Error: Error parsing private key
```

**Cause:** `FIREBASE_PRIVATE_KEY` not properly formatted.

**Solution:**
1. Ensure newlines are preserved:
   ```bash
   # Correct format (with literal \n)
   FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n"
   ```
2. In shell scripts, use:
   ```bash
   export FIREBASE_PRIVATE_KEY=$(cat service-account.json | jq -r '.private_key')
   ```
3. Some environments need double escaping:
   ```bash
   FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\\nMIIE...\\n-----END PRIVATE KEY-----\\n"
   ```

### Storage Bucket Not Found

**Symptoms:**
```
Error: Bucket not found: xxx.appspot.com
```

**Cause:** Wrong bucket name or storage not enabled.

**Solution:**
1. Verify bucket name in Firebase Console
2. Enable Firebase Storage if not already
3. Check `FIREBASE_STORAGE_BUCKET` format:
   ```bash
   # Correct format
   FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
   ```

### Firestore Index Required

**Symptoms:**
```
Error: The query requires an index. You can create it here: [URL]
```

**Cause:** Complex query needs composite index.

**Solution:**
1. Click the URL in the error message
2. Create the suggested index in Firebase Console
3. Wait a few minutes for index to build

---

## API Issues

### YouTube API Key Invalid

**Symptoms:**
```
Error: API key not valid. Please pass a valid API key.
```

**Solution:**
1. Verify key in Google Cloud Console
2. Check API is enabled (YouTube Data API v3)
3. Check key restrictions (HTTP referrers, IP addresses)
4. Create new key if needed

### Gemini API Key Invalid

**Symptoms:**
```
Error: API key not valid
```

**Solution:**
1. Verify key at https://aistudio.google.com/app/apikey
2. Check if free tier quota exhausted
3. Create new key if needed

### API Disabled

**Symptoms:**
```
Error: YouTube Data API v3 has not been used in project XXX
```

**Solution:**
1. Go to Google Cloud Console
2. Navigate to APIs & Services
3. Enable YouTube Data API v3
4. Wait a few minutes for propagation

---

## Performance Issues

### Slow Scraping

**Symptoms:**
- Less than expected videos per hour
- Frequent pauses

**Cause:** Rate limiting or inefficient batching.

**Solution:**
1. Verify network speed
2. Reduce `API_DELAY_MS` (minimum 50ms recommended)
3. Use direct channel IDs instead of handles:
   ```json
   {"url": "https://youtube.com/channel/UCxxx", "category": "..."}
   ```

### Slow Analysis

**Symptoms:**
- Analysis taking days for small dataset
- Frequent retries

**Cause:** Rate limits or network latency.

**Solution:**
1. Process during off-peak hours
2. Use paid Gemini tier for higher limits
3. Reduce image quality (if applicable)
4. Run on server closer to Google infrastructure

### High Memory Usage

**Symptoms:**
- System becoming unresponsive
- Out of memory errors

**Solution:**
1. Process in smaller batches
2. Add memory monitoring:
   ```python
   import tracemalloc
   tracemalloc.start()
   # ... code ...
   print(tracemalloc.get_traced_memory())
   ```
3. Upgrade system RAM
4. Use swap space

### Large Firebase Costs

**Symptoms:**
- Unexpected Firebase billing

**Cause:** Too many reads/writes or large storage.

**Solution:**
1. Batch Firestore writes (already implemented)
2. Use thumbnails only at `mqdefault` quality
3. Enable Firestore caching
4. Review and optimize queries

---

## Quick Diagnostic Commands

### Check Environment

```bash
# Verify Node.js
node --version  # Should be 18+

# Verify Python
python --version  # Should be 3.11+

# Check environment variables
echo $YOUTUBE_API_KEY
echo $FIREBASE_PROJECT_ID
echo $GOOGLE_API_KEY
```

### Test API Connections

```bash
# YouTube API
curl "https://www.googleapis.com/youtube/v3/videos?part=id&id=dQw4w9WgXcQ&key=$YOUTUBE_API_KEY"

# Gemini API
curl "https://generativelanguage.googleapis.com/v1beta/models?key=$GOOGLE_API_KEY"
```

### Check Progress

```bash
# Scraper progress
cd scraper && npx tsx scripts/validate.ts

# Analyzer progress
cd analyzer && python -c "from src.firebase_client import get_progress; print(get_progress())"
```

### View Logs

```bash
# Recent scraper output
tail -100 /var/log/yt-scraper.log

# PM2 logs (if using PM2)
pm2 logs yt-scraper --lines 100
```

---

## Getting Help

If you can't resolve an issue:

1. **Search existing issues**: Check GitHub Issues for similar problems
2. **Gather information**:
   - Error message (full stack trace)
   - Environment (OS, Node/Python version)
   - Steps to reproduce
   - Relevant log output
3. **Open an issue**: Include all gathered information
4. **Contact maintainers**: For urgent production issues

---

## Emergency Recovery

### Complete Reset

If all else fails, reset everything:

```bash
# 1. Clear all Firestore data
firebase firestore:delete --all-collections --project YOUR_PROJECT

# 2. Clear Firebase Storage
gsutil -m rm -r gs://YOUR_BUCKET/**

# 3. Reinstall dependencies
cd scraper && rm -rf node_modules && npm install
cd ../analyzer && rm -rf venv && python -m venv venv && pip install -r requirements.txt

# 4. Start fresh
cd ../scraper && npm start
```

**Warning:** This deletes all data. Only use as last resort.
