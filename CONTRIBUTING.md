# Contributing Guide

Thank you for your interest in contributing to the YouTube Intelligence System! This document provides guidelines and instructions for contributing.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Code Standards](#code-standards)
5. [Testing](#testing)
6. [Pull Request Process](#pull-request-process)
7. [Project Structure](#project-structure)

---

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Collaborate openly and transparently
- Maintain professional communication

---

## Getting Started

### Prerequisites

- Node.js 18+ (for scraper)
- Python 3.11+ (for analyzer, insights, recommender)
- Git
- API keys (YouTube, Firebase, Gemini)

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/your-org/youtube-intelligence.git
cd youtube-intelligence

# Copy environment template
cp .env.example .env
# Edit .env with your API keys

# Install scraper dependencies
cd scraper
npm install

# Install Python dependencies
cd ../analyzer
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dev dependencies

# Repeat for insights and recommender
cd ../insights
pip install -r requirements.txt

cd ../recommender
pip install -r requirements.txt
```

### Verify Setup

```bash
# Run scraper tests
cd scraper
npm test

# Run Python tests
cd ../analyzer
pytest tests/

# Validate API connections
cd ../scraper
npx tsx scripts/validate.ts
```

---

## Development Workflow

### Branch Strategy

```
main                    # Production-ready code
├── develop            # Integration branch
│   ├── feature/xxx    # New features
│   ├── fix/xxx        # Bug fixes
│   └── docs/xxx       # Documentation updates
```

### Creating a Feature Branch

```bash
# Update main branch
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: add your feature description"

# Push to remote
git push -u origin feature/your-feature-name
```

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Scopes:**
- `scraper`: Phase 1 changes
- `analyzer`: Phase 2 changes
- `insights`: Phase 3 changes
- `recommender`: Phase 4 changes
- `shared`: Shared utilities
- `config`: Configuration changes

**Examples:**
```
feat(scraper): add support for YouTube Shorts filtering
fix(analyzer): handle empty thumbnail responses from Gemini
docs(readme): update installation instructions
refactor(insights): improve correlation calculation performance
test(recommender): add unit tests for template generation
```

---

## Code Standards

### TypeScript (Scraper)

#### Style Guide

- Use TypeScript strict mode
- Prefer `const` over `let`
- Use explicit return types
- Document public functions with JSDoc

```typescript
/**
 * Resolves a YouTube URL to a channel ID.
 * @param url - YouTube channel URL in any format
 * @returns Resolved channel information with quota cost
 * @throws {Error} If URL format is not recognized
 */
export async function resolveChannelUrl(url: string): Promise<ResolvedChannel> {
  const parsed = parseChannelUrl(url);
  if (!parsed) {
    throw new Error(`Unrecognized URL format: ${url}`);
  }
  // ... implementation
}
```

#### Linting

```bash
cd scraper
npm run lint        # Check for issues
npm run lint:fix    # Auto-fix issues
```

#### ESLint Configuration

Key rules:
- No unused variables
- Prefer template literals
- Consistent spacing
- No console.log in production (use logger)

### Python (Analyzer, Insights, Recommender)

#### Style Guide

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Document functions with docstrings

```python
def analyze_thumbnail(
    video_data: Dict[str, Any],
    retry_count: int = 3
) -> Optional[Dict[str, Any]]:
    """
    Analyze a video thumbnail using Gemini Vision.

    Args:
        video_data: Video document containing thumbnailStoragePath
        retry_count: Number of retry attempts for transient failures

    Returns:
        Analysis result dictionary or None if analysis fails

    Raises:
        ValueError: If thumbnailStoragePath is missing
    """
    if 'thumbnailStoragePath' not in video_data:
        raise ValueError("Missing thumbnailStoragePath in video_data")
    # ... implementation
```

#### Formatting

```bash
cd analyzer

# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Check types
mypy src/

# Lint
flake8 src/ tests/
```

#### Tools Configuration

`pyproject.toml`:
```toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.11"
strict = true
```

### File Organization

```
module/
├── src/
│   ├── __init__.py
│   ├── main.py           # Entry point
│   ├── config.py         # Configuration
│   ├── feature/          # Feature modules
│   │   ├── __init__.py
│   │   └── module.py
│   └── utils/            # Utilities
│       ├── __init__.py
│       └── helpers.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py       # Test fixtures
│   └── test_*.py         # Test files
└── requirements.txt
```

---

## Testing

### TypeScript Tests (Vitest)

```bash
cd scraper

# Run all tests
npm test

# Run specific file
npm test -- tests/utils/duration.test.ts

# Run with coverage
npm test -- --coverage

# Watch mode
npm test -- --watch
```

#### Writing Tests

```typescript
// tests/utils/duration.test.ts
import { describe, it, expect } from 'vitest';
import { parseDuration } from '../../src/utils/duration';

describe('parseDuration', () => {
  it('parses minutes and seconds', () => {
    expect(parseDuration('PT15M33S')).toBe(933);
  });

  it('parses hours', () => {
    expect(parseDuration('PT1H2M3S')).toBe(3723);
  });

  it('handles edge cases', () => {
    expect(parseDuration('PT0S')).toBe(0);
    expect(parseDuration('PT1H')).toBe(3600);
  });
});
```

### Python Tests (Pytest)

```bash
cd analyzer

# Run all tests
pytest tests/

# Run specific file
pytest tests/test_analyzers.py

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Verbose output
pytest tests/ -v

# Run only marked tests
pytest tests/ -m "not slow"
```

#### Writing Tests

```python
# tests/test_analyzers.py
import pytest
from unittest.mock import Mock, patch
from src.analyzers.thumbnail import ThumbnailAnalyzer

class TestThumbnailAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return ThumbnailAnalyzer()

    @pytest.fixture
    def sample_video(self):
        return {
            'videoId': 'test123',
            'channelId': 'UCtest',
            'thumbnailStoragePath': 'thumbnails/UCtest/test123.jpg'
        }

    def test_analyze_returns_dict(self, analyzer, sample_video):
        with patch('src.analyzers.thumbnail.download_thumbnail') as mock_download:
            mock_download.return_value = b'fake_image_data'
            with patch('src.analyzers.thumbnail.analyze_image') as mock_analyze:
                mock_analyze.return_value = {'composition': {}}

                result = analyzer.analyze(sample_video)

                assert isinstance(result, dict)
                assert 'composition' in result

    def test_analyze_handles_missing_thumbnail(self, analyzer):
        video_without_thumbnail = {'videoId': 'test123'}

        with pytest.raises(ValueError):
            analyzer.analyze(video_without_thumbnail)
```

### Test Coverage Requirements

- Minimum coverage: 70%
- Critical paths: 90%
- New features must include tests

---

## Pull Request Process

### Before Submitting

1. **Update from main**
   ```bash
   git checkout main
   git pull origin main
   git checkout your-branch
   git rebase main
   ```

2. **Run all tests**
   ```bash
   # Scraper
   cd scraper && npm test

   # Python modules
   cd analyzer && pytest tests/
   cd insights && pytest tests/
   cd recommender && pytest tests/
   ```

3. **Format and lint code**
   ```bash
   # TypeScript
   cd scraper && npm run lint:fix

   # Python
   cd analyzer && black src/ tests/ && isort src/ tests/
   ```

4. **Update documentation** if needed

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Performance improvement

## Changes Made
- Change 1
- Change 2

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing completed
- [ ] All existing tests pass

## Documentation
- [ ] README updated (if needed)
- [ ] API docs updated (if needed)
- [ ] Inline comments added

## Related Issues
Closes #123
```

### Review Process

1. PR must be reviewed by at least one maintainer
2. All CI checks must pass
3. No merge conflicts
4. Squash commits before merging (if multiple commits)

### After Merge

```bash
# Delete local branch
git branch -d feature/your-feature

# Delete remote branch
git push origin --delete feature/your-feature
```

---

## Project Structure

### Directory Overview

```
youtube_channel_analysis/
├── .env.example              # Environment template
├── .gitignore
├── README.md                 # Main documentation
├── CONTRIBUTING.md           # This file
├── CLAUDE.md                 # AI assistant guidance
│
├── config/
│   └── channels.json         # Channel configuration
│
├── scraper/                  # Phase 1: TypeScript
│   ├── src/
│   │   ├── youtube/          # YouTube API
│   │   ├── firebase/         # Firebase integration
│   │   ├── scraper/          # Core logic
│   │   └── utils/            # Utilities
│   └── tests/
│
├── analyzer/                 # Phase 2: Python
│   ├── src/
│   │   ├── analyzers/        # Analysis modules
│   │   ├── processors/       # Batch processing
│   │   └── prompts/          # AI prompts
│   └── tests/
│
├── insights/                 # Phase 3: Python
│   ├── src/
│   └── tests/
│
├── recommender/              # Phase 4: Python
│   ├── src/
│   └── tests/
│
├── shared/                   # Shared utilities
│
└── docs/                     # Documentation
    ├── TECHNICAL_DOCUMENTATION.md
    ├── API_REFERENCE.md
    ├── DEPLOYMENT.md
    └── TROUBLESHOOTING.md
```

### Key Files

| File | Purpose |
|------|---------|
| `scraper/src/index.ts` | Scraper entry point |
| `scraper/src/youtube/resolver.ts` | URL resolution |
| `analyzer/src/main.py` | Analyzer entry point |
| `analyzer/src/gemini_client.py` | Gemini API wrapper |
| `insights/src/correlations.py` | Statistical analysis |
| `recommender/src/engine.py` | Recommendation logic |

---

## Need Help?

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue with reproduction steps
- **Feature Requests**: Open a GitHub Issue with use case description

Thank you for contributing!
