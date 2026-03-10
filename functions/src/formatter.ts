/**
 * Formatted CLI output for recommendations.
 * Prints colored, structured sections instead of raw JSON.
 */

import chalk from 'chalk';
import type { RecommendationResponse, IdeaGenerationResponse, ContentType } from './types';

function formatViews(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return n.toString();
}

function header(title: string): string {
  const line = '='.repeat(60);
  return `\n${chalk.bold.cyan(line)}\n${chalk.bold.cyan('  ' + title)}\n${chalk.bold.cyan(line)}`;
}

function section(emoji: string, title: string): string {
  return `\n${chalk.bold.yellow(`${emoji} ${title}`)}`;
}

export function formatRecommendation(rec: RecommendationResponse, thumbnailPaths?: string[]): string {
  const lines: string[] = [];

  // Header
  lines.push(header(`VIDEO RECOMMENDATION: ${rec.titles.primary.combined.split('|')[0]?.trim() || rec.titles.primary.combined}`));

  // Titles
  lines.push(section('\uD83D\uDCCB', 'TITLES'));
  const p = rec.titles.primary;
  lines.push(`  Primary: ${chalk.white.bold(p.combined)}`);
  lines.push(`  CTR: ${chalk.green(p.predictedCTR)}`);
  lines.push(`  Why: ${chalk.dim(p.reasoning)}`);

  if (rec.titles.alternatives.length > 0) {
    lines.push('');
    lines.push(`  ${chalk.dim('Alternatives:')}`);
    rec.titles.alternatives.forEach((alt, i) => {
      lines.push(`    ${i + 1}. ${alt.combined} ${chalk.dim(`(${alt.predictedCTR})`)}`);
    });
  }

  // Thumbnail
  lines.push(section('\uD83C\uDFA8', 'THUMBNAIL'));
  const t = rec.thumbnail;
  lines.push(`  Layout: ${chalk.white.bold(t.layout.type)} ${chalk.dim('\u2014 ' + t.layout.description)}`);

  const face = t.elements.face;
  if (face.required) {
    lines.push(`  Face: ${face.expression}, ${face.position}, ${face.size}, ${face.eyeContact ? 'eye contact' : 'no eye contact'}`);
  }

  const text = t.elements.text;
  lines.push(`  Text: ${chalk.white.bold(`"${text.primary.content}"`)} (${text.primary.position}, ${text.primary.style || 'bold'} ${text.primary.color})`);
  if (text.secondary) {
    lines.push(`        ${chalk.dim(`"${text.secondary.content}"`)} (${text.secondary.position})`);
  }

  lines.push(`  Colors: bg ${chalk.hex(t.colors.background)(t.colors.background)} | accent ${chalk.hex(t.colors.accent)(t.colors.accent)} | text ${chalk.hex(t.colors.text)(t.colors.text)}`);

  // Tags
  lines.push(section('\uD83C\uDFF7\uFE0F ', 'TAGS') + chalk.dim(` (${rec.tags.characterCount}/500 chars, ${Math.round(rec.tags.utilizationPercent)}%)`));
  if (rec.tags.primary.length > 0) {
    lines.push(`  Primary: ${rec.tags.primary.join(', ')}`);
  }
  if (rec.tags.telugu.length > 0) {
    lines.push(`  Telugu: ${rec.tags.telugu.join(', ')}`);
  }
  if (rec.tags.longtail.length > 0) {
    lines.push(`  Longtail: ${rec.tags.longtail.join(', ')}`);
  }
  if (rec.tags.secondary.length > 0) {
    lines.push(`  Secondary: ${rec.tags.secondary.join(', ')}`);
  }
  if (rec.tags.brand.length > 0) {
    lines.push(`  Brand: ${rec.tags.brand.join(', ')}`);
  }

  // Posting
  lines.push(section('\uD83D\uDCC5', 'POSTING'));
  lines.push(`  Best: ${chalk.white.bold(`${rec.posting.bestDay} ${rec.posting.bestTime}`)}`);
  if (rec.posting.alternativeTimes.length > 0) {
    lines.push(`  Also: ${rec.posting.alternativeTimes.join(', ')}`);
  }
  if (rec.posting.reasoning) {
    lines.push(`  ${chalk.dim(rec.posting.reasoning)}`);
  }

  // Prediction
  lines.push(section('\uD83D\uDCCA', 'PREDICTION'));
  const v = rec.prediction.expectedViewRange;
  const conf = rec.prediction.confidence;
  const confColor = conf === 'high' ? chalk.green : conf === 'medium' ? chalk.yellow : chalk.red;
  lines.push(`  Views: ${formatViews(v.low)} \u2014 ${chalk.bold(formatViews(v.medium))} \u2014 ${formatViews(v.high)} (confidence: ${confColor(conf)})`);
  for (const factor of rec.prediction.positiveFactors) {
    lines.push(`  ${chalk.green('\u2713')} ${factor}`);
  }
  for (const risk of rec.prediction.riskFactors) {
    lines.push(`  ${chalk.red('\u2717')} ${risk}`);
  }

  // Production Toolkit
  lines.push(section('\uD83C\uDFAC', 'PRODUCTION TOOLKIT'));

  // Duration
  lines.push(`  Duration: ${chalk.white.bold(rec.production.optimalDuration)}`);

  // Hook Script
  if (rec.production.hookScript && rec.production.hookScript.length > 0) {
    lines.push('');
    lines.push(`  ${chalk.bold.white('Hook Script (first 10-15s):')}`);
    for (const line of rec.production.hookScript) {
      lines.push(`    ${chalk.dim(line.duration)} ${chalk.cyan(line.visual)}`);
      lines.push(`    ${' '.repeat(line.duration.length)} ${chalk.white(line.dialogue)}`);
    }
  }

  // Video Segments
  if (rec.production.segments && rec.production.segments.length > 0) {
    lines.push('');
    lines.push(`  ${chalk.bold.white('Video Segments:')}`);
    for (const seg of rec.production.segments) {
      const time = chalk.dim(`${seg.startTime}-${seg.endTime}`);
      lines.push(`    ${time} ${chalk.yellow.bold(seg.title)}: ${seg.description}`);
      if (seg.tips) {
        lines.push(`    ${' '.repeat(seg.startTime.length + seg.endTime.length + 1)} ${chalk.dim(`Tip: ${seg.tips}`)}`);
      }
    }
  }

  // Shot List
  if (rec.production.shotList && rec.production.shotList.length > 0) {
    lines.push('');
    lines.push(`  ${chalk.bold.white('Shot List:')}`);
    for (const shot of rec.production.shotList) {
      const typeColor = shot.type.includes('close') ? chalk.magenta
        : shot.type.includes('wide') || shot.type.includes('drone') ? chalk.blue
        : shot.type.includes('slow') ? chalk.yellow
        : shot.type.includes('reaction') ? chalk.red
        : chalk.green;
      lines.push(`    ${typeColor(`[${shot.type}]`)} ${shot.description} ${chalk.dim(`(${shot.timing})`)}`);
    }
  }

  // Pinned Comment
  if (rec.production.pinnedComment) {
    lines.push('');
    lines.push(`  ${chalk.bold.white('Pinned Comment:')}`);
    const border = chalk.dim('\u250C' + '\u2500'.repeat(56) + '\u2510');
    const borderBottom = chalk.dim('\u2514' + '\u2500'.repeat(56) + '\u2518');
    lines.push(`  ${border}`);
    for (const commentLine of rec.production.pinnedComment.split('\n')) {
      const padded = commentLine.padEnd(56);
      lines.push(`  ${chalk.dim('\u2502')} ${padded}${chalk.dim('\u2502')}`);
    }
    lines.push(`  ${borderBottom}`);
  }

  // SEO Description
  if (rec.production.seoDescription) {
    lines.push('');
    lines.push(`  ${chalk.bold.white('YouTube Description:')}`);
    const border = chalk.dim('\u250C' + '\u2500'.repeat(56) + '\u2510');
    const borderBottom = chalk.dim('\u2514' + '\u2500'.repeat(56) + '\u2518');
    lines.push(`  ${border}`);
    for (const descLine of rec.production.seoDescription.split('\n')) {
      const padded = descLine.padEnd(56);
      lines.push(`  ${chalk.dim('\u2502')} ${padded}${chalk.dim('\u2502')}`);
    }
    lines.push(`  ${borderBottom}`);
  }

  // End Screen Script
  if (rec.production.endScreenScript) {
    lines.push('');
    lines.push(`  ${chalk.bold.white('End Screen Script (last 20s):')}`);
    lines.push(`    ${chalk.white(rec.production.endScreenScript)}`);
  }

  // Thumbnail images
  if (thumbnailPaths && thumbnailPaths.length > 0) {
    lines.push(section('\uD83D\uDDBC\uFE0F ', 'THUMBNAILS GENERATED'));
    for (const p of thumbnailPaths) {
      lines.push(`  ${chalk.green('\u2192')} ${p}`);
    }
  }

  // Metadata footer
  lines.push('');
  lines.push(chalk.dim(`Generated: ${rec.metadata.generatedAt} | Model: ${rec.metadata.modelUsed} | Insights: ${rec.metadata.insightsVersion || 'none'}`));

  return lines.join('\n');
}

const TYPE_COLORS: Record<ContentType, (s: string) => string> = {
  recipe: chalk.red,
  vlog: chalk.blue,
  tutorial: chalk.green,
  review: chalk.magenta,
  challenge: chalk.yellow,
};

export function formatIdeas(response: IdeaGenerationResponse): string {
  const lines: string[] = [];

  lines.push(header('VIDEO IDEAS'));
  lines.push(`  ${chalk.dim(`${response.ideas.length} data-backed ideas`)}`);

  for (let i = 0; i < response.ideas.length; i++) {
    const idea = response.ideas[i];
    const typeColor = TYPE_COLORS[idea.suggestedType] || chalk.white;
    const scoreColor = idea.opportunityScore >= 70 ? chalk.green
      : idea.opportunityScore >= 40 ? chalk.yellow
      : chalk.red;

    lines.push('');
    lines.push(`  ${chalk.bold.white(`${i + 1}. ${idea.topic}`)}`);
    lines.push(`     ${chalk.italic(idea.angle)}`);
    lines.push(`     ${typeColor(`[${idea.suggestedType}]`)} ${scoreColor(`Score: ${idea.opportunityScore}`)}`);
    if (idea.keywords.length > 0) {
      lines.push(`     Keywords: ${idea.keywords.map((k) => chalk.cyan(k)).join(', ')}`);
    }
    lines.push(`     ${chalk.dim(idea.whyItWorks)}`);
  }

  // Metadata footer
  lines.push('');
  lines.push(chalk.dim(`Generated: ${response.metadata.generatedAt} | Model: ${response.metadata.modelUsed} | Insights: ${response.metadata.insightsVersion || 'none'}`));

  return lines.join('\n');
}
