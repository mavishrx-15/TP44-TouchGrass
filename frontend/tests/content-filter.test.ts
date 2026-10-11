import { expect, it } from 'vitest'
import { isUnsafeText } from '@/services/content-filter'

it.each(['fuck', 'FUCK', 'ＦＵＣＫ', 'f\u200buck', 'sh1t', '傻逼', '色情'])(
  'detects inappropriate text: %s',
  (text) => {
    expect(isUnsafeText(text)).toBe(true)
  },
)
it.each(['Thanks for the shade', 'This class is lovely', 'A branch has split'])(
  'allows normal tree messages: %s',
  (text) => {
    expect(isUnsafeText(text)).toBe(false)
  },
)
