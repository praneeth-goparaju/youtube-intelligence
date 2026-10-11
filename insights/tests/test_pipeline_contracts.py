"""Exercise insights generation with the data shapes produced by the other phases."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
import sys

from google.api_core.datetime_helpers import DatetimeWithNanoseconds
import pytest

from insights.src import firebase_client, main
from insights.src.profiler import compute_feature_profile, compute_recency_weight
from insights.src.recommender_bridge import generate_recommender_documents


@pytest.fixture
def videos():
    return [
        {
            "channel": {"subscriberCount": 1000},
            "video": {
                "viewCount": (i + 1) * 1000,
                "calculated": {"viewsPerSubscriber": i + 1, "publishDayOfWeek": "Monday", "publishHourIST": 12},
            },
            "title_analysis": {
                "contentSignals": {"contentType": "recipe", "isRecipe": True},
                "hooks": {"powerWords": "Secret, easy, SECRET" if i >= 90 else "simple"},
                "keywords": {"niche": "cooking", "primaryKeyword": "recipe"},
            },
        }
        for i in range(100)
    ]


@pytest.fixture
def run_insights(monkeypatch, videos):
    saved = {}
    files = {}
    db = MagicMock()

    def snapshots():
        return [SimpleNamespace(id=name, to_dict=lambda data=data: deepcopy(data)) for name, data in saved.items()]

    db.collection.return_value.stream.side_effect = snapshots
    monkeypatch.setattr(firebase_client, "get_db", lambda: db)
    monkeypatch.setattr(main, "initialize_firebase", lambda: None)
    monkeypatch.setattr(main, "get_all_videos_with_analyses", lambda **kwargs: deepcopy(videos))
    monkeypatch.setattr(main, "save_insights", lambda name, data: saved.update({name: deepcopy(data)}))
    monkeypatch.setattr(main, "save_to_file", lambda name, data: files.update({name: deepcopy(data)}))

    def run(*args):
        monkeypatch.setattr(sys, "argv", ["insights", *args])
        main.main()
        return saved, files

    return run, saved


def test_bridge_loads_saved_profiles_without_loading_videos(run_insights, monkeypatch, videos):
    run, saved = run_insights
    saved["recipe"] = main.generate_content_type_profile("recipe", videos)
    monkeypatch.setattr(
        main, "get_all_videos_with_analyses", lambda **kwargs: pytest.fail("Bridge must use saved profiles")
    )

    run("--type", "bridge")

    assert saved["titles"]["basedOnVideos"] == 100
    assert saved["timing"]["bestTimes"]["optimal"]["hourIST"] == 12
    assert "summary" not in saved


def test_bridge_without_profiles_preserves_previous_documents(run_insights):
    run, saved = run_insights
    original = {"titles": {"basedOnVideos": 99}, "timing": {"basedOnVideos": 99}}
    saved.update(deepcopy(original))

    with pytest.raises(SystemExit) as exc:
        run("--type", "bridge")

    assert exc.value.code == 1
    assert saved == original


def test_bridge_dry_run_reads_profiles_but_does_not_write(run_insights, videos):
    run, saved = run_insights
    saved["recipe"] = main.generate_content_type_profile("recipe", videos)
    original = deepcopy(saved)
    _, files = run("--type", "bridge", "--dry-run")
    assert saved == original
    assert files["bridge_titles"]["basedOnVideos"] == 100


def test_channel_bridge_uses_channel_videos_without_database_writes(run_insights):
    run, saved = run_insights
    _, files = run("--type", "bridge", "--channel", "UCexample")
    assert saved == {}
    assert files["bridge_titles"]["basedOnVideos"] == 100


def test_gap_modes_publish_the_same_complete_contract(run_insights):
    run, saved = run_insights
    run("--type", "all")
    all_gaps = saved["contentGaps"]
    run("--type", "gaps")
    gaps_only = saved["contentGaps"]

    for key in ("highOpportunity", "saturatedTopics", "keywordGaps", "formatGaps", "totalVideos"):
        assert all_gaps[key] == gaps_only[key]
    assert all_gaps["formatGaps"]["formatPerformance"][0]["format"] == "recipe"


def test_rebuilding_bridge_preserves_gap_data(run_insights):
    run, saved = run_insights
    run("--type", "all")
    original = {key: value for key, value in saved["contentGaps"].items() if key != "generatedAt"}
    run("--type", "bridge")
    assert {key: value for key, value in saved["contentGaps"].items() if key != "generatedAt"} == original


def test_empty_filtered_dataset_preserves_existing_insights(run_insights, monkeypatch):
    run, saved = run_insights
    saved["titles"] = {"basedOnVideos": 99}
    monkeypatch.setattr(main, "get_all_videos_with_analyses", lambda **kwargs: [{"channel": {"subscriberCount": 1}}])
    with pytest.raises(SystemExit):
        run("--type", "all")
    assert saved == {"titles": {"basedOnVideos": 99}}


def test_power_words_reach_recommender_as_individual_words(videos):
    original = deepcopy(videos)
    profile = main.generate_content_type_profile("recipe", videos)
    documents = generate_recommender_documents({"recipe": profile}, None)
    words = documents["titles"]["powerWords"]["highImpact"]
    assert {word["word"] for word in words} == {"secret", "easy"}
    assert all(word["multiplier"] == 10 for word in words)
    assert videos == original


def test_power_word_profiles_keep_bounded_frequencies_with_many_distinct_words():
    analyses = [{"hooks": {"powerWords": f"word{i}, common"}} for i in range(60)]
    features = compute_feature_profile(analyses, analyses[-6:])
    items = features["hooks"]["powerWords"]["topItems"]
    assert items["common"] == {"all": 1.0, "top10": 1.0}
    assert len(items) <= 15


def test_firestore_timestamps_receive_the_same_recency_weight_as_strings():
    old = DatetimeWithNanoseconds.fromtimestamp(
        (datetime.now(timezone.utc) - timedelta(days=365)).timestamp(), tz=timezone.utc
    )
    assert compute_recency_weight(old) == pytest.approx(0.5, abs=0.001)
    assert compute_recency_weight(old) == pytest.approx(compute_recency_weight(old.isoformat()))


def test_outliers_with_computed_metrics_are_capped_without_mutating_input():
    videos = [{"channel": {"subscriberCount": 1000}, "video": {"viewCount": views}} for views in [1000] * 19 + [100000]]
    original = deepcopy(videos)
    filtered, stats = main.remove_outliers(videos, main.get_views_per_subscriber)
    assert stats["winsorizedCount"] == 1
    assert max(map(main.get_views_per_subscriber, filtered)) == pytest.approx(stats["vpsCap"])
    assert videos == original


def test_zero_outlier_cap_is_not_recomputed_from_original_views():
    videos = [{"channel": {"subscriberCount": 1000}, "video": {"viewCount": views}} for views in [0] * 99 + [100000]]
    filtered, stats = main.remove_outliers(videos, main.get_views_per_subscriber)
    assert stats["vpsCap"] == 0
    assert stats["winsorizedCount"] == 1
    assert max(map(main.get_views_per_subscriber, filtered)) == 0
