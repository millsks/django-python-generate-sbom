import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

// Vitest runs with the frontend/ project dir as cwd.
const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), 'utf-8')

describe('site favicon', () => {
  it('is a deliberate brand-colored SVG, not the Vite placeholder', () => {
    const svg = read('public/favicon.svg')
    expect(svg).toContain('#D71E28') // brand red (Story 12.1 palette)
    expect(svg).not.toContain('#863bff') // the old Vite default lightning mark
    expect(svg).toContain('viewBox="0 0 24 24"') // Material icon canvas
  })

  it('is referenced as the icon in index.html', () => {
    const html = read('index.html')
    expect(html).toMatch(/<link[^>]+rel="icon"[^>]+href="\/favicon\.svg"/)
  })
})
