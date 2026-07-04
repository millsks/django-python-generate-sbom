import { describe, expect, it } from 'vitest'
import { versionCurrencySheet } from './reportSheets'

describe('versionCurrencySheet', () => {
  it('maps version-currency entries to a sheet with normalized cells', () => {
    const sheet = versionCurrencySheet([
      { name: 'django', installed: '5.2.1', latest: '5.2.1', currency: 'current', lts: '5.2', on_lts: true, ecosystem: 'pypi' },
      { name: 'numpy', installed: '1.26.0', latest: null, currency: 'unknown', lts: null, on_lts: null, ecosystem: 'conda' },
    ])

    expect(sheet.name).toBe('Version Currency')
    expect(sheet.columns.map((c) => c.header)).toContain('Package')
    expect(sheet.rows).toHaveLength(2)
    expect(sheet.rows[0]).toMatchObject({ name: 'django', on_lts: 'yes', ecosystem: 'pypi', latest: '5.2.1' })
    // null latest/lts → '' and null on_lts → '' (not 'no').
    expect(sheet.rows[1]).toMatchObject({ name: 'numpy', latest: '', lts: '', on_lts: '', ecosystem: 'conda' })
  })
})
