# Contributing Guide

Thank you for your interest in contributing to the YouTube Intelligence System! This document provides guidelines and instructions for contributing.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Code Standards](#code-standards)
5. [Testing](#testing)
6. [Pull Request Process](#pull-request-process)

---

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Collaborate openly and transparently
- Maintain professional communication

---

## Getting Started

See the [Quick Start](README.md#quick-start) guide for prerequisites and installation. For detailed environment configuration, see the [Deployment Guide](docs/DEPLOYMENT.md).

For project structure and directory layout, see [CLAUDE.md](CLAUDE.md#project-structure).

---

## Development Workflow

### Branch Strategy

```
main                    # Production-ready code
├── feature/xxx         # New features
├── fix/xxx             # Bug fixes
└── docs/xxx            # Documentation updates
```

### Creating a Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: add your feature description"
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
- `functions`: Phase 4 (recommender) changes
- `shared`: Shared utilities
- `config`: Configuration changes

**Examples:**
```
feat(scraper): add support for YouTube Shorts filtering
fix(analyzer): handle empty thumbnail responses from Gemini
docs(readme): update installation instructions
refactor(insights): improve correlation calculation performance
test(functions): add unit tests for recommendation engine
```

---

## Code Standards

### TypeScript (Scraper, Recommender)

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

### Python (Analyzer, Insights)

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

### File Organization

```
module/
├── src/
│   ├── __init__.py
│   ├── main.py           # Entry point
│   ├── config.py         # Configuration
│   ├── feature/          # Feature modules
│   └── utils/            # Utilities
├── tests/
│   ├── conftest.py       # Test fixtures
│   └── test_*.py         # Test files
└── requirements.txt
```

---

## Testing

Each phase has its own test suite. See the phase READMEs for detailed test commands and examples:
- [Scraper tests](scraper/README.md) — Vitest
- [Analyzer tests](analyzer/README.md) — pytest
- [Insights tests](insights/README.md) — pytest

### Quick test commands

```bash
cd scraper && npm test           # TypeScript tests
cd analyzer && pytest tests/     # Analyzer tests
cd insights && pytest tests/     # Insights tests
```

### Test Coverage Requirements

- New features must include tests
- Critical paths should have thorough coverage

---

## Pull Request Process

### Before Submitting

1. **Update from main**
   ```bash
   git checkout main && git pull origin main
   git checkout your-branch && git rebase main
   ```

2. **Run all tests**
   ```bash
   cd scraper && npm test
   cd ../analyzer && pytest tests/
   cd ../insights && pytest tests/
   ```

3. **Update documentation** if needed

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
- [ ] All existing tests pass

## Related Issues
Closes #123
```

### Review Process

1. PR must be reviewed by at least one maintainer
2. All CI checks must pass
3. No merge conflicts

### After Merge

```bash
git branch -d feature/your-feature          # Delete local branch
git push origin --delete feature/your-feature  # Delete remote branch
```

---

## Need Help?

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue with reproduction steps
- **Feature Requests**: Open a GitHub Issue with use case description

Thank you for contributing!
