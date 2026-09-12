import type {
  AreaMetrics,
  MatchSummary,
  Preferences,
  PreferenceMatch,
} from '@/types/personalisation'

// Prototype rules pending backend agreement; used by mock areas AND mock routes.
export const WALKING_TOLERANCE_MINUTES = 2
export const COVERAGE_THRESHOLD_KM = 5
export const canopyLabel = (score: number | null) =>
  score === null ? 'Not available' : score >= 0.75 ? 'High' : score >= 0.4 ? 'Medium' : 'Low'
export const shadeLabel = (share: number | null) =>
  share === null
    ? 'Not available'
    : share >= 0.65
      ? 'Cooler & shaded'
      : share >= 0.35
        ? 'Partial shade'
        : 'Sunny & open'
export const noiseLabel = (share: number | null) =>
  share === null
    ? 'Not available'
    : share >= 0.65
      ? 'Mostly park-side'
      : share >= 0.35
        ? 'Mixed street/park'
        : 'Mostly street-side'

function levelMatches(value: number | null, preference: number, low: number, high: number) {
  if (value === null) return false
  if (preference >= 60) return value >= high
  if (preference <= 35) return value < low
  return value >= low && value < high
}

export function preferenceChips(p: Preferences): string[] {
  return [
    p.canopy === null
      ? null
      : p.canopy >= 60
        ? 'More tree canopy'
        : p.canopy <= 35
          ? 'More open space'
          : 'Balanced tree canopy',
    p.shade === null
      ? null
      : p.shade >= 60
        ? 'Cooler and shaded'
        : p.shade <= 35
          ? 'Sunny and open'
          : 'Balanced shade',
    p.noise === 'quiet'
      ? 'Quieter surroundings'
      : p.noise === 'lively'
        ? 'Lively atmosphere'
        : null,
    p.allergy === 'avoid'
      ? 'Avoid high-pollen areas'
      : p.allergy === 'lower'
        ? 'Prefer lower-allergy areas'
        : null,
    p.walkingTime === null
      ? null
      : p.walkingTime === 20
        ? '20+ min walk'
        : `${p.walkingTime} min walk`,
  ].filter((value): value is string => value !== null)
}

export function withinBudget(minutes: number, budget: Preferences['walkingTime']) {
  // 20+ means an open-ended walk, not a hard 20-minute cap.
  return budget === null || budget === 20 || minutes <= budget + WALKING_TOLERANCE_MINUTES
}

export function scorePreferences(
  metrics: AreaMetrics,
  preferences: Preferences,
  minutes: number,
): MatchSummary {
  const matches: PreferenceMatch[] = []
  const add = (
    key: PreferenceMatch['key'],
    label: string,
    detail: string,
    value: number,
    matched = value >= 0.7,
  ) => {
    matches.push({ key, label, detail, value, matched })
  }
  if (preferences.canopy !== null) {
    const value =
      metrics.canopy === null ? 0 : 1 - Math.abs(metrics.canopy - preferences.canopy / 100)
    add(
      'canopy',
      preferenceChips({
        ...preferences,
        shade: null,
        noise: null,
        allergy: null,
        walkingTime: null,
      })[0]!,
      metrics.canopy === null
        ? 'Canopy scoring is not available yet'
        : `${canopyLabel(metrics.canopy)} tree canopy`,
      value,
      levelMatches(metrics.canopy, preferences.canopy, 0.4, 0.75),
    )
  }
  if (preferences.shade !== null) {
    add(
      'shade',
      preferences.shade >= 60
        ? 'Cooler & shaded'
        : preferences.shade <= 35
          ? 'Sunny & open'
          : 'Balanced shade',
      shadeLabel(metrics.parkShare),
      metrics.parkShare === null ? 0 : 1 - Math.abs(metrics.parkShare - preferences.shade / 100),
      levelMatches(metrics.parkShare, preferences.shade, 0.35, 0.65),
    )
  }
  if (preferences.noise !== null) {
    add(
      'noise',
      preferences.noise === 'quiet' ? 'Quieter surroundings' : 'Lively atmosphere',
      noiseLabel(metrics.parkShare),
      metrics.parkShare === null
        ? 0
        : preferences.noise === 'quiet'
          ? metrics.parkShare
          : 1 - metrics.parkShare,
      metrics.parkShare !== null &&
        (preferences.noise === 'quiet' ? metrics.parkShare >= 0.65 : metrics.parkShare < 0.35),
    )
  }
  if (preferences.allergy !== null) {
    add(
      'allergy',
      preferences.allergy === 'avoid' ? 'Avoid high-pollen areas' : 'Lower-allergy preference',
      metrics.highPollenTrees === null
        ? 'Allergy data not yet confirmed'
        : `${metrics.highPollenTrees} high-pollen trees flagged within 100 m`,
      metrics.lowAllergyShare ?? 0,
      metrics.lowAllergyShare !== null &&
        metrics.lowAllergyShare >= (preferences.allergy === 'avoid' ? 0.95 : 0.8),
    )
  }
  // Walking time constrains route selection; it is not an environmental sub-score.
  const environmental = matches.map((item) => item.value)
  const score = environmental.length
    ? environmental.reduce((a, b) => a + b, 0) / environmental.length
    : 0
  if (preferences.walkingTime !== null) {
    const inBudget = withinBudget(minutes, preferences.walkingTime)
    add(
      'time',
      'Walking time',
      preferences.walkingTime === 20
        ? `${minutes} min · open-ended walk`
        : `${minutes} min · ${preferences.walkingTime} min budget${minutes > preferences.walkingTime && inBudget ? ' (within tolerance)' : ''}`,
      inBudget ? 1 : 0,
      inBudget,
    )
  }
  const good = matches.filter((item) => item.matched).map((item) => item.label.toLowerCase())
  const partial = matches.some((item) => !item.matched)
  const sentence = good.length
    ? `Matches your ${good.join(', ')}${partial ? ', with some trade-offs shown below.' : '.'}`
    : matches.length
      ? 'The best available option has some trade-offs with your preferences.'
      : 'A nearby tree-dense area to explore at your own pace.'
  return { score, matches, sentence }
}
