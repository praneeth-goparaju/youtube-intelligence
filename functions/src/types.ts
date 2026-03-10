/**
 * Type definitions for the Recommendation API
 */

// ============================================
// Request Types
// ============================================

export interface RecommendationRequest {
  /** Video topic (required) */
  topic: string;
  /** Content type */
  type?: ContentType;
  /** Unique positioning angle */
  angle?: string;
  /** Target audience */
  audience?: string;
}

export type ContentType = 'recipe' | 'vlog' | 'tutorial' | 'review' | 'challenge';

// ============================================
// Response Types
// ============================================

export interface RecommendationResponse {
  titles: TitleRecommendations;
  thumbnail: ThumbnailRecommendation;
  tags: TagRecommendations;
  posting: PostingRecommendation;
  prediction: PerformancePrediction;
  production: ProductionToolkit;
  metadata: ResponseMetadata;
}

export interface TitleRecommendations {
  primary: TitleSuggestion;
  alternatives: TitleSuggestion[];
}

export interface TitleSuggestion {
  english?: string;
  telugu?: string;
  combined: string;
  predictedCTR: 'below-average' | 'average' | 'above-average' | 'high';
  reasoning: string;
}

export interface ThumbnailRecommendation {
  layout: {
    type: string;
    description: string;
  };
  elements: {
    face: FaceElement;
    mainVisual: VisualElement;
    text: TextElements;
    graphics: GraphicsElements;
  };
  colors: ColorScheme;
  referenceExamples?: ReferenceExample[];
}

export interface FaceElement {
  required: boolean;
  expression: string;
  position: string;
  size: string;
  eyeContact: boolean;
}

export interface VisualElement {
  type: string;
  position: string;
  showSteam?: boolean;
  garnished?: boolean;
}

export interface TextElements {
  primary: TextElement;
  secondary?: TextElement;
}

export interface TextElement {
  content: string;
  position: string;
  color: string;
  style?: string;
  language?: string;
}

export interface GraphicsElements {
  addArrow: boolean;
  arrowPointTo?: string;
  addBorder: boolean;
  borderColor?: string;
}

export interface ColorScheme {
  background: string;
  accent: string;
  text: string;
}

export interface ReferenceExample {
  videoId: string;
  reason: string;
}

export interface TagRecommendations {
  primary: string[];
  secondary: string[];
  telugu: string[];
  longtail: string[];
  brand: string[];
  fullTagString: string;
  characterCount: number;
  utilizationPercent: number;
}

export interface PostingRecommendation {
  bestDay: string;
  bestTime: string;
  alternativeTimes: string[];
  reasoning: string;
}

export interface PerformancePrediction {
  expectedViewRange: {
    low: number;
    medium: number;
    high: number;
  };
  confidence: 'low' | 'medium' | 'high';
  positiveFactors: string[];
  riskFactors: string[];
}

export interface HookScriptLine {
  visual: string;
  dialogue: string;
  duration: string;
}

export interface VideoSegment {
  startTime: string;
  endTime: string;
  title: string;
  description: string;
  tips?: string;
}

export interface Shot {
  type: string;
  description: string;
  timing: string;
}

export interface ProductionToolkit {
  optimalDuration: string;
  hookScript: HookScriptLine[];
  segments: VideoSegment[];
  shotList: Shot[];
  pinnedComment: string;
  seoDescription: string;
  endScreenScript: string;
}

export interface ResponseMetadata {
  generatedAt: string;
  modelUsed: string;
  insightsVersion: string | null;
  fallbackUsed: boolean;
}

// ============================================
// Insights Types (from Firestore)
// ============================================

export interface Insights {
  thumbnails?: ThumbnailInsights;
  titles?: TitleInsights;
  timing?: TimingInsights;
  contentGaps?: ContentGapInsights;
}

export interface ThumbnailInsights {
  generatedAt: string;
  basedOnVideos: number;
  topPerformingElements: {
    composition?: PerformingElement[];
    humanPresence?: PerformingElement[];
    colors?: PerformingElement[];
    text?: PerformingElement[];
    food?: PerformingElement[];
  };
  worstPerformingElements?: PerformingElement[];
}

export interface PerformingElement {
  element: string;
  lift: number;
  sampleSize?: number;
  avoid?: boolean;
}

export interface TitleInsights {
  generatedAt: string;
  basedOnVideos: number;
  winningPatterns?: WinningPattern[];
  powerWords?: {
    highImpact?: PowerWord[];
    mediumImpact?: PowerWord[];
  };
  optimalLength?: {
    characters: { min: number; max: number; sweetSpot: number };
    words: { min: number; max: number; sweetSpot: number };
  };
  optimalLanguageMix?: {
    teluguRatio: { min: number; max: number; sweetSpot: number };
  };
}

export interface WinningPattern {
  pattern: string;
  avgViews: number;
  sampleSize: number;
  examples: string[];
}

export interface PowerWord {
  word: string;
  telugu?: string;
  multiplier: number;
}

export interface TimingInsights {
  generatedAt: string;
  basedOnVideos: number;
  bestTimes: {
    byDayOfWeek: DayPerformance[];
    byHourIST: HourPerformance[];
    optimal: {
      day: string;
      hourIST: number;
      multiplier: number;
      description?: string;
    };
  };
}

export interface DayPerformance {
  day: string;
  avgViews: number;
  multiplier: number;
}

export interface HourPerformance {
  hour: number;
  avgViews: number;
  multiplier: number;
  label?: string;
}

export interface ContentGapInsights {
  generatedAt: string;
  highOpportunity: ContentGap[];
  saturatedTopics: SaturatedTopic[];
  keywordGaps?: { highValueKeywords: KeywordOpportunity[] };
  formatGaps?: { formatPerformance: FormatPerformance[]; recommendedFormats: FormatPerformance[] };
}

export interface ContentGap {
  topic: string;
  avgViews: number;
  videoCount: number;
  opportunityScore: number;
}

export interface SaturatedTopic {
  topic: string;
  competition: string;
}

export interface KeywordOpportunity {
  keyword: string;
  avgViewsPerSubscriber: number;
  viewsMultiplier: number;
  usageCount: number;
  usageRate: number;
}

export interface FormatPerformance {
  format: string;
  avgViewsPerSubscriber: number;
  viewsMultiplier: number;
  count: number;
  usagePercent: number;
}

// ============================================
// Idea Generation Types
// ============================================

export interface VideoIdea {
  topic: string;
  angle: string;
  whyItWorks: string;
  opportunityScore: number;
  suggestedType: ContentType;
  keywords: string[];
}

export interface IdeaGenerationResponse {
  ideas: VideoIdea[];
  metadata: ResponseMetadata;
}
