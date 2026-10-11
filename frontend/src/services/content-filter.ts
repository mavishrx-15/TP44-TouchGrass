/** Matches the basic community text rules enforced by the backend. */
export const MESSAGE_CONTENT_WARNING =
  'Your message contains inappropriate language. Please remove swear words or adult content before posting.'

export function isUnsafeText(body: string): boolean {
  const substitutions: Record<string, string> = { '@': 'a', '0': 'o', '1': 'i', '3': 'e', $: 's' }
  const normalized = body
    .normalize('NFKC')
    .toLowerCase()
    .replace(/\p{Cf}/gu, '')
    .replace(/[@013$]/g, (character) => substitutions[character]!)
  return (
    /\b(?:fuck\w*|motherfuck\w*|shit|bullshit|bitch\w*|cunt\w*|nigg(?:er|a)\w*|faggot\w*|porn\w*|hentai)\b/i.test(
      normalized,
    ) ||
    ['kill yourself', 'kys', '去死', '操你', '傻逼', '色情', '约炮'].some((phrase) =>
      normalized.includes(phrase),
    )
  )
}
