# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Email the maintainers or use [GitHub's private vulnerability reporting](https://github.com/praneeth-goparaju/youtube_channel_analysis/security/advisories/new)
3. Include a description of the vulnerability, steps to reproduce, and potential impact

We will acknowledge your report within 48 hours and aim to provide a fix within 7 days for critical issues.

## Scope

This policy covers the code in this repository, including:
- Firebase Functions API endpoints
- Scraper, analyzer, and insights modules
- Configuration and deployment files

## Best Practices for Users

- **Never commit `.env` files** — use `.env.example` as a template
- **Rotate API keys** regularly and after any suspected exposure
- **Configure `RECOMMEND_API_KEY`** before deploying Firebase Functions — the API rejects all requests if this is not set
- **Set `ALLOWED_ORIGINS`** to restrict CORS in production deployments
