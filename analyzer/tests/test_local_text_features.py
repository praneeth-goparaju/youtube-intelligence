"""Tests for local text feature extraction."""

import pytest
from src.analyzers.local_text_features import extract_local_features, deep_merge


class TestExtractLocalFeatures:
    """Test the main extract_local_features function."""

    def test_telugu_only_title(self):
        title = "హైదరాబాదీ చికెన్ బిర్యానీ రెసిపీ"
        result = extract_local_features(title, "")

        assert result['structure']['characterCount'] == len(title)
        assert result['structure']['teluguCharacterCount'] > 0
        assert result['structure']['englishCharacterCount'] == 0
        assert result['language']['hasTeluguScript'] is True
        assert result['language']['hasLatinScript'] is False
        assert result['language']['teluguRatio'] == 1.0
        assert result['language']['primaryLanguage'] == 'telugu'

    def test_english_only_title(self):
        title = "Best Chicken Biryani Recipe Ever"
        result = extract_local_features(title, "")

        assert result['structure']['englishCharacterCount'] > 0
        assert result['structure']['teluguCharacterCount'] == 0
        assert result['language']['hasTeluguScript'] is False
        assert result['language']['hasLatinScript'] is True
        assert result['language']['englishRatio'] == 1.0
        assert result['language']['primaryLanguage'] == 'english'

    def test_mixed_title(self):
        title = "చికెన్ బిర్యానీ Recipe | Best Hyderabadi Style"
        result = extract_local_features(title, "")

        assert result['structure']['teluguCharacterCount'] > 0
        assert result['structure']['englishCharacterCount'] > 0
        assert result['language']['hasTeluguScript'] is True
        assert result['language']['hasLatinScript'] is True
        assert 0 < result['language']['teluguRatio'] < 1
        assert 0 < result['language']['englishRatio'] < 1
        assert result['structure']['separator'] == '|'
        assert result['structure']['segmentCount'] == 2

    def test_title_with_emoji(self):
        title = "🔥 Best Biryani Recipe 😋"
        result = extract_local_features(title, "")

        assert result['formatting']['hasEmoji'] is True
        assert '🔥' in result['formatting']['emojiList']
        assert 'start' in result['formatting']['emojiPositions']

    def test_title_with_brackets(self):
        title = "Biryani Recipe [OFFICIAL] (Full Version)"
        result = extract_local_features(title, "")

        assert result['formatting']['hasBrackets'] is True
        # First bracket type found wins
        assert result['formatting']['bracketType'] in ('round', 'square')

    def test_title_with_number(self):
        title = "Top 10 Biryani Recipes of 2024"
        result = extract_local_features(title, "")

        assert result['hooks']['hasNumber'] is True
        assert '10' in result['hooks']['numbers']
        assert '2024' in result['hooks']['numbers']
        assert result['formatting']['hasYear'] is True
        assert result['formatting']['year'] == '2024'

    def test_title_question(self):
        title = "Which Biryani is the Best?"
        result = extract_local_features(title, "")

        assert result['hooks']['isQuestion'] is True
        assert result['formatting']['hasQuestion'] is True
        assert result['formatting']['punctuationType'] == 'question'

    def test_title_exclamation(self):
        title = "AMAZING Biryani Recipe!"
        result = extract_local_features(title, "")

        assert result['formatting']['hasExclamation'] is True
        assert result['formatting']['endsWithPunctuation'] is True
        assert result['formatting']['punctuationType'] == 'exclamation'

    def test_title_all_caps(self):
        title = "BEST BIRYANI EVER"
        result = extract_local_features(title, "")

        assert result['formatting']['allCaps'] is True
        assert result['formatting']['capitalization'] == 'all-caps'

    def test_title_with_hashtag(self):
        title = "Biryani Recipe #cooking #food"
        result = extract_local_features(title, "")

        assert result['formatting']['hasHashtag'] is True
        assert '#cooking' in result['formatting']['hashtags']

    def test_word_count(self):
        title = "Simple Easy Quick Biryani"
        result = extract_local_features(title, "")

        assert result['structure']['wordCount'] == 4

    def test_empty_title(self):
        result = extract_local_features("", "")

        assert result['structure']['characterCount'] == 0
        assert result['structure']['wordCount'] == 0

    def test_separator_dash(self):
        title = "Biryani - The Complete Recipe"
        result = extract_local_features(title, "")

        assert result['structure']['separator'] == '-'
        assert result['structure']['segmentCount'] == 2


class TestDescriptionFeatures:
    """Test description feature extraction."""

    def test_description_with_timestamps(self):
        desc = "0:00 Intro\n2:30 Ingredients\n5:00 Cooking\n10:00 Plating"
        result = extract_local_features("Title", desc)

        da = result['descriptionAnalysis']
        assert da['timestamps']['hasTimestamps'] is True
        assert da['timestamps']['timestampCount'] == 4

    def test_description_with_hashtags(self):
        desc = "Great recipe!\n\nFollow me!\n\n#biryani #cooking #recipe"
        result = extract_local_features("Title", desc)

        da = result['descriptionAnalysis']
        assert da['hashtags']['count'] == 3
        assert da['hashtags']['position'] == 'end'

    def test_description_with_links(self):
        desc = (
            "Follow me on Instagram: https://instagram.com/chef\n"
            "Check out this product: https://amzn.to/abc123\n"
            "Watch my other video: https://youtube.com/watch?v=xyz\n"
            "Playlist: https://youtube.com/playlist?list=PL123\n"
            "My website: https://mysite.com\n"
        )
        result = extract_local_features("Title", desc)

        links = result['descriptionAnalysis']['links']
        assert links['hasSocialMediaLinks'] is True
        assert links['hasAffiliateLinks'] is True
        assert links['hasOtherVideoLinks'] is True
        assert links['hasPlaylistLinks'] is True
        assert links['hasWebsiteLink'] is True
        assert links['totalLinkCount'] == 5

    def test_description_with_ctas(self):
        desc = "Please subscribe to my channel! Like this video and comment below!"
        result = extract_local_features("Title", desc)

        ctas = result['descriptionAnalysis']['ctas']
        assert ctas['hasSubscribeCTA'] is True
        assert ctas['hasLikeCTA'] is True
        assert ctas['hasCommentCTA'] is True

    def test_description_monetization(self):
        desc = (
            "This video is sponsored by BrandX.\n"
            "Use code CHEF20 for 20% off.\n"
            "#ad #sponsored\n"
            "Support me on Patreon: https://patreon.com/chef\n"
            "Check out my merch store!\n"
        )
        result = extract_local_features("Title", desc)

        mon = result['descriptionAnalysis']['monetization']
        assert mon['hasSponsorMention'] is True
        assert mon['hasDisclosure'] is True
        assert mon['hasDiscountCode'] is True
        assert mon['hasMerchLink'] is True
        assert mon['hasDonationLink'] is True

    def test_empty_description(self):
        result = extract_local_features("Title", "")

        da = result['descriptionAnalysis']
        assert da['structure']['length'] == 0
        assert da['structure']['lineCount'] == 0
        assert da['timestamps']['hasTimestamps'] is False
        assert da['links']['totalLinkCount'] == 0
        assert da['monetization']['hasSponsorMention'] is False

    def test_description_length_and_lines(self):
        desc = "Line 1\nLine 2\nLine 3"
        result = extract_local_features("Title", desc)

        assert result['descriptionAnalysis']['structure']['length'] == len(desc)
        assert result['descriptionAnalysis']['structure']['lineCount'] == 3


class TestDeepMerge:
    """Test the deep_merge utility."""

    def test_simple_merge(self):
        base = {'a': 1, 'b': 2}
        overlay = {'b': 3, 'c': 4}
        result = deep_merge(base, overlay)

        assert result == {'a': 1, 'b': 3, 'c': 4}

    def test_nested_merge(self):
        base = {'a': {'x': 1, 'y': 2}, 'b': 3}
        overlay = {'a': {'y': 99, 'z': 100}}
        result = deep_merge(base, overlay)

        assert result == {'a': {'x': 1, 'y': 99, 'z': 100}, 'b': 3}

    def test_does_not_mutate_inputs(self):
        base = {'a': {'x': 1}}
        overlay = {'a': {'y': 2}}
        result = deep_merge(base, overlay)

        assert base == {'a': {'x': 1}}
        assert overlay == {'a': {'y': 2}}
        assert result == {'a': {'x': 1, 'y': 2}}

    def test_overlay_wins_for_non_dict(self):
        base = {'a': [1, 2, 3]}
        overlay = {'a': [4, 5]}
        result = deep_merge(base, overlay)

        assert result == {'a': [4, 5]}

    def test_deeply_nested(self):
        base = {
            'descriptionAnalysis': {
                'structure': {'wellOrganized': True, 'firstLineHook': False},
                'ctas': {'commentQuestion': 'What do you think?'},
            }
        }
        overlay = {
            'descriptionAnalysis': {
                'structure': {'length': 500, 'lineCount': 20},
                'timestamps': {'hasTimestamps': True, 'timestampCount': 5},
            }
        }
        result = deep_merge(base, overlay)

        da = result['descriptionAnalysis']
        assert da['structure']['wellOrganized'] is True
        assert da['structure']['length'] == 500
        assert da['ctas']['commentQuestion'] == 'What do you think?'
        assert da['timestamps']['hasTimestamps'] is True
