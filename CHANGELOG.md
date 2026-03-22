# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2024-12-01

### Added
- **Phase 1 - Scraper**: YouTube Data API v3 integration with Firebase Firestore/Storage
  - Incremental update mode (`--update`) for fetching only new videos
  - Stats refresh mode (`--refresh`) for updating existing video metrics
  - Quota-aware operation with progress tracking and resumability
  - Channel URL resolution (handles, user pages, custom URLs)
  - Scripts for validation, progress reset, and short thumbnail cleanup
- **Phase 2 - Analyzer**: Gemini 2.5 Flash AI analysis (2 API calls per video)
  - Thumbnail vision analysis (~132 fields)
  - Hybrid local + LLM title/description analysis (~135 fields)
  - Sync mode (per-video) and Batch mode (50% cost savings via Batch API)
  - Local text feature extraction (59 fields, zero API cost)
- **Phase 3 - Insights**: Per-content-type feature profiling and content gap analysis
  - All vs top 10% performance comparison by viewsPerSubscriber
  - Keyword opportunity and format gap analysis
  - Insights summary generation for downstream consumption
- **Phase 4 - Recommender**: AI-powered recommendation engine
  - CLI and Firebase Functions HTTP/callable API
  - Gemini-powered recommendations with template fallback
  - Video idea generation from content gap data
  - AI thumbnail generation
  - Rate limiting and API key authentication
  - Generation history (save/list)
- CI/CD pipeline with GitHub Actions (typecheck + tests)
- Comprehensive documentation (README, API reference, deployment guide, troubleshooting)
- CONTRIBUTING guide with development workflow and code standards
- Security policy (SECURITY.md)
