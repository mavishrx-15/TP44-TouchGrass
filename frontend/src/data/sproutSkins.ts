export const SKIN_COST = 15

export const SPROUT_SKINS = [
  {
    id: 'classic',
    name: 'Classic Sprout',
    description: 'The original. Always yours.',
    colors: ['#3f7d39', '#4f8f45', '#63a655', '#6db35d', '#8a5a3b'],
    background: '#eaf3e0',
  },
  {
    id: 'autumn',
    name: 'Autumn Sprout',
    description: 'Fiery leaves, a cosy scarf and a little autumn magic.',
    colors: ['#9a4524', '#b5562b', '#d0712e', '#e8923a', '#7a4a2e'],
    background: '#fbeedd',
  },
  {
    id: 'blossom',
    name: 'Blossom Sprout',
    description: 'Pink spring flowers and softly drifting petals.',
    colors: ['#3f7d39', '#4f8f45', '#63a655', '#74b863', '#8a5a3b'],
    background: '#fcebf1',
  },
  {
    id: 'wattle',
    name: 'Golden Wattle',
    description: 'Fluffy golden flowers that sparkle in the sun.',
    colors: ['#4f7a2f', '#5f8a39', '#789f3f', '#8db34a', '#8a5a3b'],
    background: '#fdf6d8',
  },
  {
    id: 'snowgum',
    name: 'Snow Gum',
    description: 'Silvery leaves, a snowy cap and alpine bark.',
    colors: ['#5d8578', '#6f978b', '#87ae9f', '#a2c7b8', '#e8dfcf'],
    background: '#e8f1f4',
  },
  {
    id: 'night',
    name: 'Night Sprout',
    description: 'A crescent moon, twinkling stars and fireflies.',
    colors: ['#172d45', '#1f3a57', '#2a4d71', '#4a78a8', '#4a3a30'],
    background: '#dfe6f2',
  },
] as const

export type SkinId = (typeof SPROUT_SKINS)[number]['id']

export function isSkinId(value: unknown): value is SkinId {
  return SPROUT_SKINS.some((skin) => skin.id === value)
}

export function getSkin(id: SkinId) {
  return SPROUT_SKINS.find((skin) => skin.id === id) ?? SPROUT_SKINS[0]
}
