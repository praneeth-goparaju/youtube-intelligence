"""Pydantic models for Gemini response_schema.

These models define the exact JSON structure expected from Gemini API responses.
Used as response_schema to guarantee valid JSON output and eliminate the need
for JSON template instructions in prompts (~1,000 input tokens saved per request).

The google-genai SDK accepts Pydantic models directly as response_schema.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# =============================================================================
# Thumbnail Analysis Schema (~109 fields)
# =============================================================================

class ThumbnailComposition(BaseModel):
    layoutType: str = Field(description="split-screen|single-focus|collage|text-heavy|minimal")
    gridStructure: str = Field(description="rule-of-thirds|centered|asymmetric|golden-ratio")
    visualBalance: str = Field(description="balanced|left-heavy|right-heavy|top-heavy|bottom-heavy")
    negativeSpace: str = Field(description="minimal|moderate|heavy")
    complexity: str = Field(description="simple|medium|complex|cluttered")
    focalPoint: str = Field(description="Description of main focal point")
    depthOfField: str = Field(description="shallow|deep|flat")


class ThumbnailHumanPresence(BaseModel):
    facePresent: bool
    faceCount: int
    facePosition: Optional[str] = None
    faceSize: Optional[str] = Field(default=None, description="small|medium|large|dominant")
    faceCoverage: Optional[float] = None
    expression: Optional[str] = Field(default=None, description="happy|surprised|shocked|curious|neutral|excited|disgusted|thinking")
    expressionIntensity: Optional[str] = Field(default=None, description="subtle|moderate|high|extreme")
    mouthOpen: Optional[bool] = None
    eyeContact: Optional[bool] = None
    eyebrowsRaised: Optional[bool] = None
    bodyVisible: bool
    bodyPortion: Optional[str] = Field(default=None, description="face-only|upper|half|full")
    handVisible: bool
    handGesture: Optional[str] = Field(default=None, description="none|thumbs-up|pointing|holding-item|peace|ok")
    pointingAt: Optional[str] = None
    lookingDirection: Optional[str] = Field(default=None, description="camera|left|right|down|at-food")


class ThumbnailPrimaryText(BaseModel):
    content: Optional[str] = None
    language: Optional[str] = Field(default=None, description="english|telugu|hindi|other")
    script: Optional[str] = Field(default=None, description="latin|telugu|devanagari")
    position: Optional[str] = None
    size: Optional[str] = Field(default=None, description="small|medium|large")
    color: Optional[str] = None
    backgroundColor: Optional[str] = None
    hasOutline: Optional[bool] = None
    fontStyle: Optional[str] = Field(default=None, description="bold-sans|script|handwritten|decorative")
    allCaps: Optional[bool] = None
    readable: Optional[bool] = None


class ThumbnailTextElements(BaseModel):
    hasText: bool
    textCount: int
    primaryText: ThumbnailPrimaryText
    languages: List[str]
    hasTeluguScript: bool
    hasEnglishText: bool
    hasNumbers: bool
    numberValue: Optional[str] = None
    numberType: Optional[str] = Field(default=None, description="view-count|list-number|price|time|quantity")
    hasEmoji: bool
    emojiList: List[str]
    textPurpose: List[str] = Field(description="e.g. title, social-proof, cta, brand, dish-name, benefit")
    totalTextCoverage: float


class ThumbnailDominantColor(BaseModel):
    hex: str
    name: str
    percentage: float


class ThumbnailColors(BaseModel):
    dominantColors: List[ThumbnailDominantColor]
    palette: str = Field(description="warm|cool|neutral|mixed")
    mood: str = Field(description="energetic|calm|appetizing|professional|playful")
    contrast: str = Field(description="low|medium|high")
    saturation: str = Field(description="desaturated|medium|high|vivid")
    brightness: str = Field(description="dark|medium|bright")
    backgroundType: str = Field(description="solid|gradient|image|blurred|transparent")
    backgroundColor: str
    colorHarmony: str = Field(description="monochromatic|complementary|triadic|analogous")
    contrastWithYouTube: bool


class ThumbnailFood(BaseModel):
    foodPresent: bool
    foodCount: int
    mainDish: Optional[str] = None
    dishCategory: Optional[str] = Field(default=None, description="rice|curry|snack|dessert|bread|indo-chinese|breakfast")
    cuisineType: Optional[str] = None
    presentation: Optional[str] = Field(default=None, description="close-up|plated|cooking-process|ingredients|before-after")
    platingStyle: Optional[str] = Field(default=None, description="rustic|elegant|home-style|restaurant")
    container: Optional[str] = Field(default=None, description="plate|bowl|pot|pan|banana-leaf|hand")
    steam: bool
    sizzle: bool
    garnished: bool
    garnishes: List[str]
    freshness: str = Field(description="low|medium|high")
    appetiteAppeal: int = Field(ge=1, le=10)
    colorVibrancy: str = Field(description="low|medium|high")
    textureVisible: bool
    portionSize: str = Field(description="small|medium|generous|huge")
    cookingStage: str = Field(description="raw|in-progress|finished")


class ThumbnailGraphics(BaseModel):
    hasArrows: bool
    arrowCount: int
    arrowColor: Optional[str] = None
    arrowStyle: Optional[str] = Field(default=None, description="straight|curved|hand-drawn")
    arrowPointingTo: Optional[str] = None
    hasCircles: bool
    hasHighlights: bool
    hasBorder: bool
    borderColor: Optional[str] = None
    borderStyle: Optional[str] = Field(default=None, description="solid|dashed|glow|shadow")
    hasBadge: bool
    badgeType: Optional[str] = Field(default=None, description="new|viral|view-count|trending|episode-number")
    badgeText: Optional[str] = None
    hasLogo: bool
    logoPosition: Optional[str] = None
    hasBeforeAfter: bool
    hasVsComparison: bool
    hasSplitScreen: bool
    hasGlow: bool
    hasShadow: bool


class ThumbnailBranding(BaseModel):
    channelLogoVisible: bool
    logoPlacement: Optional[str] = None
    channelNameVisible: bool
    recognizableStyle: bool
    professionalQuality: str = Field(description="amateur|medium|high|professional")


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
    primaryEmotion: Optional[str] = Field(default=None, description="curiosity|excitement|appetite|nostalgia|amusement")
    emotionalIntensity: str = Field(description="low|moderate|high")
    clickMotivation: List[str]
    targetAudience: str


class ThumbnailTechnicalQuality(BaseModel):
    resolution: str = Field(description="low|medium|high")
    sharpness: str = Field(description="blurry|acceptable|sharp")
    lighting: str = Field(description="poor|natural|professional|studio")
    noiseLevel: str = Field(description="high|medium|low")
    framing: str = Field(description="poor|acceptable|good|excellent")
    exposure: str = Field(description="underexposed|correct|overexposed")


class ThumbnailScores(BaseModel):
    clickability: int = Field(ge=1, le=10)
    clarity: int = Field(ge=1, le=10)
    professionalism: int = Field(ge=1, le=10)
    uniqueness: int = Field(ge=1, le=10)
    appetiteAppeal: int = Field(ge=1, le=10)
    emotionalImpact: int = Field(ge=1, le=10)
    predictedCTR: str = Field(description="below-average|average|above-average|exceptional")
    improvementAreas: List[str]


class ThumbnailAnalysisSchema(BaseModel):
    """Complete thumbnail analysis schema (~109 fields)."""
    composition: ThumbnailComposition
    humanPresence: ThumbnailHumanPresence
    textElements: ThumbnailTextElements
    colors: ThumbnailColors
    food: ThumbnailFood
    graphics: ThumbnailGraphics
    branding: ThumbnailBranding
    psychology: ThumbnailPsychology
    technicalQuality: ThumbnailTechnicalQuality
    scores: ThumbnailScores


# =============================================================================
# Title + Description Analysis Schema (~140 fields)
# =============================================================================

class TitleSegment(BaseModel):
    text: str
    type: str = Field(description="dish-name|translation|modifier|channel-name|hook")
    language: str = Field(description="english|telugu")


class TitleStructure(BaseModel):
    pattern: str = Field(description="Pattern description like 'dish-name | translation | modifier'")
    patternType: str = Field(description="single|segmented|question|list|statement")
    segments: List[TitleSegment]
    segmentCount: int
    separator: Optional[str] = None
    separatorConsistent: bool
    characterCount: int
    characterCountNoSpaces: int
    wordCount: int
    teluguCharacterCount: int
    englishCharacterCount: int


class TitleLanguage(BaseModel):
    languages: List[str]
    primaryLanguage: str = Field(description="english|telugu")
    secondaryLanguage: Optional[str] = Field(default=None, description="english|telugu")
    scripts: List[str]
    hasTeluguScript: bool
    hasLatinScript: bool
    hasTransliteration: bool
    transliteratedWords: List[str]
    codeSwitch: bool
    codeSwitchStyle: Optional[str] = Field(default=None, description="translation|mixed|parallel")
    teluguWords: List[str]
    teluguWordCount: int
    teluguReadability: str = Field(description="easy|medium|difficult")
    englishWords: List[str]
    englishWordCount: int
    teluguRatio: float
    englishRatio: float


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
    isQuestion: bool
    questionType: Optional[str] = Field(default=None, description="how|why|what|which|can|should")
    questionWord: Optional[str] = None
    hasNumber: bool
    numbers: List[str]
    numberContext: Optional[str] = Field(default=None, description="list|time|money|quantity|ranking|year")
    hasPowerWord: bool
    powerWords: List[str]
    powerWordCategories: List[str]
    exclusivityWords: List[str]
    urgencyWords: List[str]
    curiosityWords: List[str]
    qualityWords: List[str]
    emotionWords: List[str]
    teluguPowerWords: List[str]
    triggers: TitleTriggers
    hookStrength: str = Field(description="weak|moderate|strong|viral")
    primaryHook: str


class TitleKeywordEntry(BaseModel):
    word: str
    type: str = Field(description="dish|recipe|modifier|brand")
    searchVolume: str = Field(description="low|medium|high")


class TitleKeywords(BaseModel):
    primaryKeyword: str
    primaryKeywordPosition: str = Field(description="start|middle|end")
    secondaryKeywords: List[str]
    allKeywords: List[TitleKeywordEntry]
    searchIntent: str = Field(description="how-to|review|comparison|information|entertainment")
    niche: str = Field(description="cooking|travel|entertainment|tech|vlog|etc")
    subNiche: str
    microNiche: Optional[str] = None
    evergreen: bool
    seasonal: bool
    trendingPotential: str = Field(description="low|medium|high")
    keywordCompetition: str = Field(description="low|medium|high|extreme")
    seoOptimized: bool
    keywordInFirst3Words: bool
    naturalLanguage: bool


class TitleFormatting(BaseModel):
    capitalization: str = Field(description="lowercase|title-case|all-caps|mixed")
    allCaps: bool
    partialCaps: bool
    capsWords: List[str]
    hasEmoji: bool
    emojiList: List[str]
    emojiPositions: List[str]
    hasBrackets: bool
    bracketType: Optional[str] = Field(default=None, description="round|square|curly")
    bracketContent: Optional[str] = None
    hasSpecialChars: bool
    specialChars: List[str]
    hasYear: bool
    year: Optional[str] = None
    hasHashtag: bool
    hashtags: List[str]
    endsWithPunctuation: bool
    punctuationType: Optional[str] = Field(default=None, description="exclamation|question|period")
    hasExclamation: bool
    hasQuestion: bool


class TitleContentSignals(BaseModel):
    contentType: str = Field(description="recipe|tutorial|review|vlog|challenge|reaction|comparison|list|storytime|unboxing|explainer|news")
    isRecipe: bool
    isTutorial: bool
    isReview: bool
    isVlog: bool
    isChallenge: bool
    isReaction: bool
    isComparison: bool
    isList: bool
    isStorytime: bool
    isPartOfSeries: bool
    seriesName: Optional[str] = None
    episodeNumber: Optional[str] = None
    hasCollaboration: bool
    collaboratorMentioned: Optional[str] = None
    hasBrandMention: bool
    brandMentioned: Optional[str] = None
    brandPosition: Optional[str] = Field(default=None, description="start|middle|end")


class TitleTeluguAnalysis(BaseModel):
    formalRegister: bool
    respectLevel: str = Field(description="casual|neutral|respectful")
    dialectHints: str = Field(description="andhra|telangana|rayalaseema|neutral")
    hasHonorifics: bool
    honorificsUsed: List[str]
    hasColloquialisms: bool
    colloquialWords: List[str]
    foodTermsAccurate: bool
    traditionalTerms: List[str]
    modernTerms: List[str]
    targetAudienceAge: str = Field(description="young|middle|older|all")
    urbanVsRural: str = Field(description="urban|rural|both")


class TitleCompetitive(BaseModel):
    uniquenessScore: int = Field(ge=1, le=10)
    followsNichePattern: bool
    deviatesFrom: List[str]
    uniqueElements: List[str]
    missingCommonElements: List[str]
    standoutFactor: str


class TitleScores(BaseModel):
    seoScore: int = Field(ge=1, le=10)
    clickabilityScore: int = Field(ge=1, le=10)
    clarityScore: int = Field(ge=1, le=10)
    emotionalScore: int = Field(ge=1, le=10)
    uniquenessScore: int = Field(ge=1, le=10)
    lengthScore: int = Field(ge=1, le=10)
    clickbaitLevel: int = Field(ge=1, le=10)
    clickbaitElements: List[str]
    overallScore: int = Field(ge=1, le=10)
    predictedPerformance: str = Field(description="below-average|average|above-average|exceptional")
    suggestions: List[str]


# Description sub-schemas

class DescStructure(BaseModel):
    length: int
    lineCount: int
    wellOrganized: bool
    firstLineHook: bool


class DescTimestamps(BaseModel):
    hasTimestamps: bool
    timestampCount: int


class DescRecipeContent(BaseModel):
    hasIngredients: bool
    ingredientCount: int
    hasInstructions: bool
    instructionSteps: int
    hasCookingTime: bool


class DescHashtags(BaseModel):
    count: int
    position: str = Field(description="start|middle|end|throughout|none")


class DescCtas(BaseModel):
    hasSubscribeCTA: bool
    hasLikeCTA: bool
    hasCommentCTA: bool
    commentQuestion: Optional[str] = None


class DescSeo(BaseModel):
    keywordInFirst100Chars: bool
    keywordDensity: float
    internalLinking: str = Field(description="none|minimal|good|excellent")


class DescriptionAnalysis(BaseModel):
    structure: DescStructure
    timestamps: DescTimestamps
    recipeContent: DescRecipeContent
    hashtags: DescHashtags
    ctas: DescCtas
    seo: DescSeo


class TitleDescriptionAnalysisSchema(BaseModel):
    """Complete title + description analysis schema (~140 fields)."""
    structure: TitleStructure
    language: TitleLanguage
    hooks: TitleHooks
    keywords: TitleKeywords
    formatting: TitleFormatting
    contentSignals: TitleContentSignals
    teluguAnalysis: TitleTeluguAnalysis
    competitive: TitleCompetitive
    scores: TitleScores
    descriptionAnalysis: DescriptionAnalysis
