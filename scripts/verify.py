"""Run local checks for all phases: python scripts/verify.py.

Install requirements.txt, Ruff, and both npm projects before running.
Use --contracts-only to check the Python insights output with the real TypeScript consumer.
No check calls a production service.
"""

import argparse
import json
import os
import subprocess
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def node_environment():
    environment = os.environ.copy()
    environment["NODE_OPTIONS"] = f"{environment.get('NODE_OPTIONS', '')} --throw-deprecation".strip()
    return environment


def check_insights_contract():
    from insights.src.gaps import GapAnalyzer
    from insights.src.main import generate_content_type_profile, get_views_per_subscriber
    from insights.src.recommender_bridge import generate_recommender_documents

    videos = [
        {
            "video": {
                "calculated": {"viewsPerSubscriber": i + 1, "publishDayOfWeek": "Monday", "publishHourIST": 12},
            },
            "title_analysis": {
                "contentSignals": {"contentType": "recipe", "isRecipe": True},
                "hooks": {"powerWords": "secret, easy" if i >= 90 else "simple"},
                "keywords": {"niche": "cooking", "primaryKeyword": "rare" if i >= 98 else "recipe"},
            },
        }
        for i in range(100)
    ]
    profile = generate_content_type_profile("recipe", videos)
    analyzer = GapAnalyzer(videos, get_views_per_subscriber)
    gaps = {
        "totalVideos": len(videos),
        "contentGaps": analyzer.find_content_gaps(),
        "keywordGaps": analyzer.analyze_keyword_gaps(),
        "formatGaps": analyzer.analyze_format_gaps(),
    }
    full = generate_recommender_documents({"recipe": profile}, gaps)
    for video in videos:
        video["video"]["calculated"].pop("publishDayOfWeek")
        video["video"]["calculated"].pop("publishHourIST")
    sparse = generate_recommender_documents({"recipe": generate_content_type_profile("recipe", videos)}, gaps)
    consumer_check = """
        const assert = require('node:assert/strict');
        const fs = require('node:fs');
        const core = require('./src/recommendation-core.ts');
        const { formatRecommendation } = require('./src/formatter.ts');
        const { full, sparse } = JSON.parse(fs.readFileSync(0, 'utf8'));
        const context = core.buildContext(full);
        assert(context.includes('secret'));
        assert(context.includes('cooking'));
        assert.equal(core.getPostingRecommendation(full).bestDay, 'Monday');
        const ideasContext = core.buildIdeasContext(full);
        assert(ideasContext.includes('rare'));
        assert(ideasContext.includes('2.0% usage'));
        assert(ideasContext.includes('recipe'));
        for (const insights of [full, sparse]) {
            const result = core.generateFromTemplates('Biryani', 'recipe', undefined, 'Telugu audience', insights, null);
            assert.doesNotThrow(() => formatRecommendation(result));
            assert(!JSON.stringify(result).includes('undefined'));
            assert(result.tags.characterCount <= 500);
        }
        console.log('Python insights and TypeScript recommendations agree.');
    """
    subprocess.run(
        ["node", "--require", "tsx/cjs", "--eval", consumer_check],
        input=json.dumps({"full": full, "sparse": sparse}),
        text=True,
        cwd=ROOT / "functions",
        env=node_environment(),
        check=True,
    )


def main():
    warnings.filterwarnings("error", category=DeprecationWarning)
    warnings.filterwarnings("error", category=FutureWarning)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contracts-only", action="store_true")
    args = parser.parse_args()
    if not args.contracts_only:
        checks = [
            (ROOT, [sys.executable, "-m", "pytest", "-q"]),
            (ROOT, [sys.executable, "-m", "ruff", "check", "analyzer", "insights", "shared", "scripts/verify.py"]),
            (
                ROOT,
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "format",
                    "--check",
                    "analyzer",
                    "insights",
                    "shared",
                    "scripts/verify.py",
                ],
            ),
            (ROOT / "scraper", ["npm", "exec", "--", "tsc", "--noEmit"]),
            (ROOT / "scraper", ["npm", "test"]),
            (ROOT / "functions", ["npm", "exec", "--", "tsc", "--noEmit"]),
            (ROOT / "functions", ["npm", "test", "--", "--runInBand"]),
        ]
        for directory, command in checks:
            print(f"\nRunning {' '.join(command)} in {directory.relative_to(ROOT) or '.'}", flush=True)
            subprocess.run(command, cwd=directory, env=node_environment() if command[0] == "npm" else None, check=True)
    check_insights_contract()


if __name__ == "__main__":
    main()
