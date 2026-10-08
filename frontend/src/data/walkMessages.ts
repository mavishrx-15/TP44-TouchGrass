/**
 * Sprout's words for the walk, the arrival and the check-in. Written in
 * advance like every other Sprout message (Epic 5 rule: no AI model), and
 * chosen from the walk's own state, not generated.
 */
import type { Mood } from '@/data/sproutMessages'

export const BEYOND_BLUE = { label: 'Beyond Blue', number: '1300 22 4636' } as const

/** Shown only behind the walk page's Help button, not thrust in front of a stressed user. */
export const HELP_TEXT = 'Sprout is a tree guide, not a counsellor.'

export const LOCATION_REASON =
  'I need your location to show where you are on the route. It stays on your phone and is never stored.'

export const TIP_TEXT = {
  breathe: 'GPS locked. Try breathing in for 4 steps, then out for 4 steps.',
  breatheNoGps: 'Try breathing in for 4 steps, then out for 4 steps.',
  checkin: 'Halfway there. Drop your shoulders and unclench your jaw.',
} as const

export function directionTip(street: string | null, heading: string): string {
  const where = street ? `along ${street}` : 'along the path'
  return `Head ${heading} ${where}. Keep to the shady side where you can.`
}

export function treesTip(density: 'High' | 'Medium' | 'Low', treeCount: number | null): string {
  const count = treeCount === null ? '' : ` with about ${treeCount} trees`
  return `You’re in a ${density.toLowerCase()} tree-density zone${count}. Take a slow look up.`
}

export function almostTip(treeCount: number, topSpecies: string[]): string {
  const species = topSpecies.length ? `, mostly ${topSpecies.join(' and ')}` : ''
  return `Almost there. This area has ${treeCount} trees${species}.`
}

export const PAUSE_TEXT =
  'Let’s pause. Find some shade if you can and take 3 slow breaths. I’ll wait right here.'
export const RESUME_TEXT = 'Nice and steady. Let’s carry on when you’re ready.'
export const WORSE_TEXT =
  'I’m sorry it feels hard. We can stop any time. You’ve already done something kind for yourself.'
export const END_TEXT = 'Thanks for trying. Every walk counts, even the short ones.'
export const REROUTE_QUESTION = 'Want me to find a new way from here?'
export const ARRIVED_TEXT = 'You made it! First, find a tree near you. Walk to the closest one you can see.'
export const PINNED_TEXT = 'Pinned right where you are! Now snap a photo of your tree.'
export const FIND_TREE_TEXT =
  'Find a tree near you, and walk to the closest one you can reach safely.'
export const TOUCH_BARK_TEXT = 'Gently touch the bark of the tree you found.'
export const LISTEN_TEXT = 'Listen for 3 different sounds around you. Birds, leaves, traffic, anything.'
export const BREATHE_TEXT = 'Breathe in slowly for 4, hold for 2, and out for 6. Three times.'
export const PIN_QUESTION =
  'Is there a tree right next to you? Stand beside it and I’ll pin it with your location.'
export const PIN_WARNING =
  'Your signal is a bit loose, so the pin may be off. Wait a moment and try again for a closer spot.'
export const PHOTO_GUIDE = 'Fit your tree inside the frame'
export const PHOTO_DONE = 'What a beauty! Want to leave it a message?'
export const CAMERA_BLOCKED =
  'I can’t reach your camera. You can still pick a photo from your Photos, or carry on without one.'
export const POSTED_TEXT = 'Posted! Other visitors to this area will see your message.'
export const REPORT_SENT_TEXT =
  'Thank you for looking out for it. Your pin and photo make it easy for the council to find.'
export const SAVED_NOTE =
  'Saved in TouchGrass with your pin and photo. Photos are checked before other visitors can see them.'
export const THANKS_CHIP = 'Thanks for the shade'
export const DAMAGE_CHIP = 'A branch is hanging off'
export const MESSAGE_PROMPT = 'Write anything you like. If you spot damage, mention it and I’ll help you report it.'

/** Words that turn a message into a possible damage report (US7.4). */
export const DAMAGE_WORDS = [
  'hanging',
  'broken',
  'branch',
  'fallen',
  'damage',
  'dying',
  'dead',
  'crack',
  'split',
  'leaning',
  'vandal',
  'snapped',
] as const

/** Returns the first damage word typed, matched as whole words, or null. */
export function findDamageWord(text: string): string | null {
  const lower = text.toLowerCase()
  for (const word of DAMAGE_WORDS) {
    if (new RegExp(`\\b${word}\\b`).test(lower)) return word
  }
  return null
}

export function damageNotice(word: string): string {
  return `SPROUT NOTICED POSSIBLE DAMAGE: “${word}”. Want me to turn this into a report for the council?`
}

export const MOOD_LEVEL: Record<Mood, number> = {
  calm: 0,
  okay: 1,
  tense: 2,
  stressed: 3,
  overwhelmed: 4,
}

/** US6.6: the before/after line, comparing the Epic 5 mood with the check-in. */
export function moodChangeSummary(before: Mood, now: Mood): { text: string; direction: 'down' | 'same' | 'up' } {
  const delta = MOOD_LEVEL[now] - MOOD_LEVEL[before]
  if (delta < 0) {
    const levels = -delta
    return { text: `Down ${levels} level${levels > 1 ? 's' : ''} since your walk started`, direction: 'down' }
  }
  if (delta > 0) {
    return { text: `Up ${delta} level${delta > 1 ? 's' : ''}`, direction: 'up' }
  }
  return { text: 'About the same as before', direction: 'same' }
}

/** Sprout's reaction to the check-in: excited, calm or gentle. */
export function checkInReply(direction: 'down' | 'same' | 'up'): string {
  if (direction === 'down') return 'Yes! Your walk helped. Let’s keep that feeling going.'
  if (direction === 'same') return 'That’s steady, and steady is good. I’m glad you took the time.'
  return 'Thanks for telling me honestly. Be gentle with yourself today.'
}

/**
 * Turns whatever a walk or pin step threw into plain words. Browser and fetch
 * text ("Failed to fetch", "User denied Geolocation") never reaches the user.
 * Our own plain messages (for example "That photo is too large") pass through.
 */
export function friendlyError(error: unknown, fallback: string): string {
  const geo = error as Partial<GeolocationPositionError> | null
  if (geo && typeof geo === 'object' && typeof geo.code === 'number' && !(error instanceof Error)) {
    if (geo.code === 1) return 'Location is blocked. Allow location for TouchGrass in your browser settings, then try again.'
    if (geo.code === 3) return 'I couldn’t get your position in time. Try again somewhere more open.'
    return 'I couldn’t find your position just now. Try again in a moment.'
  }
  if (error instanceof TypeError || (error instanceof Error && /fetch|network|abort|load failed/i.test(error.message))) {
    return 'I couldn’t reach TouchGrass just now. Check your connection, then try again.'
  }
  if (error instanceof Error && error.message) return error.message
  return fallback
}
