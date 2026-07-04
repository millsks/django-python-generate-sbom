import { describe, expect, it } from 'vitest'
import { versionCurrencySheet, vulnerabilitiesSheet } from './reportSheets'

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

describe('vulnerabilitiesSheet', () => {
  it('maps one row per finding across the full report, flattening ids and CWEs', () => {
    const sheet = vulnerabilitiesSheet({
      packages: [
        {
          name: 'django',
          version: '4.2.0',
          vulnerabilities: [
            {
              id: 'GHSA-a',
              aliases: ['CVE-2024-1', 'GHSA-a'],
              cve: 'CVE-2024-1',
              cvss_score: 7.5,
              severity: 'High',
              advisory_url: 'http://a',
              cwe: ['CWE-79', 'CWE-89'],
            },
            {
              id: 'GHSA-b',
              aliases: [],
              cve: null,
              cvss_score: null,
              severity: 'Low',
              advisory_url: 'http://b',
              cwe: [],
            },
          ],
        },
      ],
      summary: { vulnerable_package_count: 1, severity_breakdown: { High: 1, Low: 1 } },
    })

    expect(sheet.name).toBe('Vulnerabilities')
    expect(sheet.columns.map((c) => c.header)).toEqual([
      'Package',
      'Installed',
      'CVE / GHSA',
      'CVSS',
      'Severity',
      'CWE',
      'Advisory URL',
    ])
    expect(sheet.rows).toHaveLength(2)
    // Multi-id dedupes id + aliases; multi-CWE comma-joins.
    expect(sheet.rows[0]).toMatchObject({
      name: 'django',
      version: '4.2.0',
      ids: 'GHSA-a, CVE-2024-1',
      cvss: 7.5,
      severity: 'High',
      cwe: 'CWE-79, CWE-89',
      advisory: 'http://a',
    })
    // null CVSS → '' ; empty CWE → ''.
    expect(sheet.rows[1]).toMatchObject({ name: 'django', ids: 'GHSA-b', cvss: '', cwe: '', advisory: 'http://b' })
  })
})
