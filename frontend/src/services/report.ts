export interface TreeReport {
  body: string
  location: string
  date: string
  photoDataUrl: string | null
}

export function reportText(report: TreeReport): string {
  return [
    'Possible tree damage reported through TouchGrass.',
    `Location: ${report.location}`,
    `Date: ${report.date}`,
    `What was seen: ${report.body}`,
    `Photo: ${report.photoDataUrl ? 'included' : 'not provided'}`,
  ].join('\n')
}

export function reportFiles(report: TreeReport): File[] {
  const files = [
    new File([reportText(report)], 'touchgrass-tree-report.txt', { type: 'text/plain' }),
  ]
  if (report.photoDataUrl) {
    const match = /^data:(image\/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=]+)$/.exec(
      report.photoDataUrl,
    )
    if (match) {
      const bytes = Uint8Array.from(atob(match[2]!), (char) => char.charCodeAt(0))
      files.push(
        new File(
          [bytes],
          `touchgrass-tree-photo.${match[1] === 'image/jpeg' ? 'jpg' : match[1]!.split('/')[1]}`,
          { type: match[1] },
        ),
      )
    }
  }
  return files
}

function escapeHtml(value: string): string {
  return value.replace(
    /[&<>"']/g,
    (character) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]!,
  )
}

/** A self-contained document keeps the exact pin, description and photo together. */
export function reportDocument(report: TreeReport): string {
  const photo =
    report.photoDataUrl &&
    /^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(report.photoDataUrl)
      ? `<img alt="Photo of the pinned tree" src="${report.photoDataUrl}" style="max-width:100%;border-radius:16px">`
      : ''
  return `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TouchGrass tree report</title><body style="margin:32px auto;padding:0 24px;max-width:720px;font:16px system-ui;color:#1d2a1d;background:#fffdf8"><h1>Possible tree damage</h1><p>Prepared by a TouchGrass visitor. Submit this report to the council separately.</p><p><strong>Location:</strong> ${escapeHtml(report.location)}</p><p><strong>Date:</strong> ${escapeHtml(report.date)}</p><p style="white-space:pre-wrap">${escapeHtml(report.body)}</p>${photo}</body></html>`
}

export function downloadReport(report: TreeReport) {
  const url = URL.createObjectURL(new Blob([reportDocument(report)], { type: 'text/html' }))
  const link = document.createElement('a')
  link.href = url
  link.download = 'touchgrass-tree-report.html'
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 30_000)
}

export function downloadReportPhoto(report: TreeReport) {
  if (!report.photoDataUrl) return
  const link = document.createElement('a')
  link.href = report.photoDataUrl
  link.download = 'touchgrass-tree-photo.jpg'
  link.click()
}
