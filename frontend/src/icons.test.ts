import { describe, expect, it } from 'vitest'
import { currencyIcon, jobStatusIcon, severityIcon } from './icons'

// The icon vocabulary is the single source of truth for status→icon/color (Story 12.2):
// a given concept must always resolve to the same icon and palette color.

describe('severityIcon', () => {
  it('maps each severity to a stable icon + palette color', () => {
    expect(severityIcon('Critical').color).toBe('error')
    expect(severityIcon('High').color).toBe('error')
    expect(severityIcon('Medium').color).toBe('warning')
    expect(severityIcon('Low').color).toBe('info')
    expect(severityIcon('Unknown').color).toBe('disabled')
    // Same input → same icon component (consistent vocabulary).
    expect(severityIcon('Critical').Icon).toBe(severityIcon('Critical').Icon)
  })

  it('falls back to the unknown icon for an unrecognized severity', () => {
    expect(severityIcon('nonsense')).toEqual(severityIcon('Unknown'))
  })
})

describe('currencyIcon', () => {
  it('maps currency classes to a stable icon + color', () => {
    expect(currencyIcon('current').color).toBe('success')
    expect(currencyIcon('unknown').color).toBe('disabled')
    // behind-1 and behind-2+ share the "outdated" vocabulary.
    expect(currencyIcon('behind-1')).toEqual(currencyIcon('behind-2+'))
    expect(currencyIcon('behind-1').color).toBe('warning')
  })
})

describe('jobStatusIcon', () => {
  it('maps job status codes to a stable icon + color', () => {
    expect(jobStatusIcon('SUCCESS').color).toBe('success')
    expect(jobStatusIcon('FAILED').color).toBe('error')
    // PENDING and PROGRESS share the "in progress" vocabulary.
    expect(jobStatusIcon('PENDING')).toEqual(jobStatusIcon('PROGRESS'))
    expect(jobStatusIcon('PROGRESS').color).toBe('info')
  })
})
