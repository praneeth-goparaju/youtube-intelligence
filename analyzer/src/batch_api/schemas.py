"""Pydantic models for Gemini response_schema.

These models define the exact JSON structure expected from Gemini API responses.
Used as response_schema to guarantee valid JSON output and eliminate the need
for JSON template instructions in prompts (~1,000 input tokens saved per request).

The google-genai SDK accepts Pydantic models directly as response_schema.

NOTE: No Optional fields or Field descriptions to stay within Gemini's constraint
state limits. The prompts specify all valid enum values. For absent/N/A data,
Gemini outputs "none", empty string, 0, or false as appropriate.

NOTE: List[str] is extremely expensive for constraint states. Only used where
values form a small closed set (languages, scripts). All freeform word lists
use plain str (comma-separated) to minimize states. Nested List[Object] types
(segments, allKeywords) are removed entirely for the same reason.
"""

from typing import List
from pydantic import BaseModel


# =============================================================================
# Thumbnail Analysis Schema
# =============================================================================


class ThumbnailScene(BaseModel):
    settingType: str
    location: str
    backgroundElements: List[str]
    timeOfDay: str
    props: List[str]
    thumbnailStyle: str
    contentCategory: str


class ThumbnailComposition(BaseModel):
    layoutType: str
    gridStructure: str
    visualBalance: str
    negativeSpace: str
    complexity: str
    focalPoint: List[str]
    depthOfField: str


class ThumbnailHumanPresence(BaseModel):
    facePresent: bool
    faceCount: int
    facePosition: str
    faceSize: str
    faceCoverage: float
    expression: str
    expressionIntensity: str
    mouthOpen: bool
    eyeContact: bool
    eyebrowsRaised: bool
    bodyVisible: bool
    bodyPortion: str
    handVisible: bool
    handGesture: str
    pointingAt: str
    lookingDirection: str


class ThumbnailPrimaryText(BaseModel):
    content: str
    language: str
    script: str
    position: str
    size: str
    color: str
    backgroundColor: str
    hasOutline: bool
    fontStyle: str
    allCaps: bool
    readable: bool


class ThumbnailTextElements(BaseModel):
    hasText: bool
    textCount: int
    primaryText: ThumbnailPrimaryText
    languages: List[str]
    hasTeluguScript: bool
    hasEnglishText: bool
    hasNumbers: bool
    numberValue: str
    numberType: str
    hasEmoji: bool
    emojiList: List[str]
    textPurpose: List[str]
    totalTextCoverage: float


class ThumbnailDominantColor(BaseModel):
    hex: str
    name: str
    percentage: float


class ThumbnailColors(BaseModel):
    dominantColors: List[ThumbnailDominantColor]
    palette: str
    mood: str
    contrast: str
    saturation: str
    brightness: str
    backgroundType: str
    backgroundColor: str
    colorHarmony: str
    contrastWithYouTube: bool


class ThumbnailFood(BaseModel):
    foodPresent: bool
    foodCount: int
    mainDish: str
    dishCategory: str
    cuisineType: str
    presentation: str
    platingStyle: str
    container: str
    steam: bool
    sizzle: bool
    garnished: bool
    garnishes: List[str]
    freshness: str
    appetiteAppeal: int
    colorVibrancy: str
    textureVisible: bool
    portionSize: str
    cookingStage: str


class ThumbnailGraphics(BaseModel):
    hasArrows: bool
    arrowCount: int
    arrowColor: str
    arrowStyle: str
    arrowPointingTo: str
    hasCircles: bool
    hasHighlights: bool
    hasBorder: bool
    borderColor: str
    borderStyle: str
    hasBadge: bool
    badgeType: str
    badgeText: str
    hasLogo: bool
    logoPosition: str
    hasBeforeAfter: bool
    hasVsComparison: bool
    hasSplitScreen: bool
    hasGlow: bool
    hasShadow: bool


class ThumbnailBranding(BaseModel):
    channelLogoVisible: bool
    logoPlacement: str
    channelNameVisible: bool
    recognizableStyle: bool
    professionalQuality: str


class ThumbnailPsychology(BaseModel):
    curiosityGap: bool
    socialProof: bool
    urgency: bool
    scarcity: bool
    authority: bool
    controversy: bool
    transformation: bool
    luxury: bool
    nostalgia: bool
    shock: bool
    humor: bool
    fear: bool
    aspiration: bool
    relatability: bool
    primaryEmotion: str
    emotionalIntensity: str
    clickMotivation: List[str]
    targetAudience: List[str]


class ThumbnailTechnicalQuality(BaseModel):
    resolution: str
    sharpness: str
    lighting: str
    noiseLevel: str
    framing: str
    exposure: str


class ThumbnailAnalysisSchema(BaseModel):
    """Complete thumbnail analysis schema."""

    scene: ThumbnailScene
    composition: ThumbnailComposition
    humanPresence: ThumbnailHumanPresence
    textElements: ThumbnailTextElements
    colors: ThumbnailColors
    food: ThumbnailFood
    graphics: ThumbnailGraphics
    branding: ThumbnailBranding
    psychology: ThumbnailPsychology
    technicalQuality: ThumbnailTechnicalQuality


# =============================================================================
# Title + Description Analysis Schema (Gemini-only semantic fields)
#
# Deterministic fields (character counts, emoji detection, link patterns,
# hashtags, timestamps, CTAs, monetization signals, formatting) are computed
# locally by local_text_features.py and merged into the final analysis doc.
# This reduces schema size by ~5-6K chars, freeing room for future fields.
#
# Key state-reduction decisions:
# - List[TitleSegment] removed (nested object array = state explosion)
# - List[TitleKeywordEntry] removed (nested object array = state explosion)
# - Freeform word lists use str (comma-separated) instead of List[str]
# - languages/scripts removed (computed locally), no more List[str]
# - TitleFormatting removed entirely (all deterministic)
# - DescTimestamps, DescHashtags, DescLinks, DescMonetization removed (deterministic)
# =============================================================================


class TitleStructure(BaseModel):
    pattern: str
    patternType: str


class TitleLanguage(BaseModel):
    hasTransliteration: bool
    transliteratedWords: str
    codeSwitch: bool
    codeSwitchStyle: str
    teluguWords: str
    teluguWordCount: int
    teluguReadability: str
    englishWords: str
    englishWordCount: int


class TitleTriggers(BaseModel):
    curiosityGap: bool
    socialProof: bool
    urgency: bool
    exclusivity: bool
    controversy: bool
    transformation: bool
    challenge: bool
    comparison: bool
    personal: bool
    storytelling: bool


class TitleHooks(BaseModel):
    questionType: str
    questionWord: str
    numberContext: str
    hasPowerWord: bool
    powerWords: str
    powerWordCategories: str
    triggers: TitleTriggers
    hookStrength: str
    primaryHook: str


class TitleKeywords(BaseModel):
    primaryKeyword: str
    primaryKeywordPosition: str
    secondaryKeywords: str
    searchIntent: str
    niche: str
    subNiche: str
    microNiche: str
    evergreen: bool
    seasonal: bool
    trendingPotential: str
    keywordCompetition: str
    seoOptimized: bool
    keywordInFirst3Words: bool
    naturalLanguage: bool


class TitleContentSignals(BaseModel):
    contentType: str
    isRecipe: bool
    isTutorial: bool
    isReview: bool
    isVlog: bool
    isChallenge: bool
    isReaction: bool
    isComparison: bool
    isList: bool
    isStorytime: bool
    isTravel: bool
    isInterview: bool
    isEducational: bool
    isMusicRelated: bool
    isPartOfSeries: bool
    seriesName: str
    episodeNumber: str
    hasCollaboration: bool
    collaboratorMentioned: str
    hasBrandMention: bool
    brandMentioned: str
    brandPosition: str


# Description sub-schemas (Gemini-only semantic fields)


class DescStructure(BaseModel):
    wellOrganized: bool
    firstLineHook: bool


class DescRecipeContent(BaseModel):
    hasIngredients: bool
    ingredientCount: int
    hasInstructions: bool
    instructionSteps: int
    hasCookingTime: bool


class DescCtas(BaseModel):
    commentQuestion: str


class DescSeo(BaseModel):
    keywordInFirst100Chars: bool
    keywordDensity: float
    internalLinking: str


class DescriptionAnalysis(BaseModel):
    structure: DescStructure
    recipeContent: DescRecipeContent
    ctas: DescCtas
    seo: DescSeo


class TitleDescriptionAnalysisSchema(BaseModel):
    """Complete title + description analysis schema (Gemini semantic fields only).

    Deterministic fields (formatting, counts, links, timestamps, hashtags,
    monetization) are computed locally and merged post-analysis.
    """

    structure: TitleStructure
    language: TitleLanguage
    hooks: TitleHooks
    keywords: TitleKeywords
    contentSignals: TitleContentSignals
    descriptionAnalysis: DescriptionAnalysis
