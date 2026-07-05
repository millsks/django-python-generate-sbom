import { describe, expect, it } from 'vitest'
import { formatDuration } from './duration'

describe('formatDuration', () => {
  it('returns a dash for null/undefined/negative', () => {
    expect(formatDuration(null)).toBe('—')
    expect(formatDuration(undefined)).toBe('—')
    expect(formatDuration(-5)).toBe('—')
  })

  it('formats sub-second as milliseconds', () => {
    expect(formatDuration(0.45)).toBe('450ms')
    expect(formatDuration(0)).toBe('0ms')
  })

  it('formats seconds under a minute', () => {
    expect(formatDuration(45)).toBe('45s')
    expect(formatDuration(1)).toBe('1s')
  })

  it('formats minutes and seconds', () => {
    expect(formatDuration(83)).toBe('1m 23s')
    expect(formatDuration(600)).toBe('10m 0s')
  })

  it('formats hours with zero-padded minutes', () => {
    expect(formatDuration(7500)).toBe('2h 05m')
    expect(formatDuration(3600)).toBe('1h 00m')
  })
})
