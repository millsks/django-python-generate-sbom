import { describe, expect, it } from 'vitest'
import { accentSpectrum, brand, darkTheme, lightTheme } from './theme'

describe('theme', () => {
  it('maps the brand red/gold to primary/secondary in both modes', () => {
    for (const theme of [lightTheme, darkTheme]) {
      expect(theme.palette.primary.main).toBe(brand.red)
      expect(theme.palette.secondary.main).toBe(brand.gold)
      // Gold pairs with dark text, never white.
      expect(theme.palette.secondary.contrastText).toBe(brand.neutral[900])
    }
  })

  it('keeps error visually distinct from the brand primary', () => {
    expect(lightTheme.palette.error.main).not.toBe(brand.red)
    expect(darkTheme.palette.error.main).not.toBe(brand.red)
  })

  it('derives backgrounds/text/dividers from the neutral ramp per mode', () => {
    expect(lightTheme.palette.mode).toBe('light')
    expect(lightTheme.palette.background.default).toBe(brand.neutral[100])
    expect(lightTheme.palette.background.paper).toBe(brand.neutral[0])
    expect(lightTheme.palette.text.primary).toBe(brand.neutral[900])

    expect(darkTheme.palette.mode).toBe('dark')
    expect(darkTheme.palette.background.default).toBe(brand.neutral[900])
    expect(darkTheme.palette.text.primary).toBe(brand.neutral[100])
  })

  it('exposes the full accent spectrum as a reusable data-viz scale', () => {
    expect(accentSpectrum).toHaveLength(6)
    expect(accentSpectrum[0]).toBe('#EB691E')
    expect(accentSpectrum[5]).toBe('#5A469B')
  })

  it('applies shared design tokens (rounded shape, non-uppercase buttons)', () => {
    expect(lightTheme.shape.borderRadius).toBe(8)
    expect(lightTheme.typography.button.textTransform).toBe('none')
  })
})
