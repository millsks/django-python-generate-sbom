import { describe, expect, it } from 'vitest'
import { licensesSheet, sbomComponentsSheet, versionCurrencySheet, vulnerabilitiesSheet } from './reportSheets'
import type { SbomDocument } from './api/sbom'

function makeDoc(components: SbomDocument['components']): SbomDocument {
  return { format: 'cyclonedx-json', components, raw: '' }
}

describe('versionCurrencySheet', () => {
  it('maps version-currency entries to all UI columns with a linked package name', () => {
    const sheet = versionCurrencySheet([
      { name: 'django', installed: '5.2.1', latest: '5.2.1', currency: 'current', lts: '5.2', on_lts: true, ecosystem: 'pypi', conda_latest: '5.1.0' },
      { name: 'numpy', installed: '1.26.0', latest: null, currency: 'unknown', lts: null, on_lts: null, ecosystem: 'conda' },
    ])

    expect(sheet.name).toBe('Version Currency')
    // All UI columns are present, including the conda-forge latest.
    // "PyPI Latest" sits immediately before "conda-forge Latest" (Story 8.23).
    expect(sheet.columns.map((c) => c.header)).toEqual([
      'Package',
      'Installed',
      'PyPI Latest',
      'conda-forge Latest',
      'Status',
      'LTS',
      'On LTS',
      'Source',
    ])
    // Package name is a hyperlink to its registry (PyPI project page).
    expect(sheet.rows[0]).toMatchObject({
      name: { text: 'django', hyperlink: 'https://pypi.org/project/django/5.2.1/' },
      latest: '5.2.1',
      conda_latest: '5.1.0',
      on_lts: 'yes',
      ecosystem: 'pypi',
    })
    // Conda package links to prefix.dev; null latest/conda_latest/lts → '', null on_lts → ''.
    expect(sheet.rows[1]).toMatchObject({
      name: { text: 'numpy', hyperlink: 'https://prefix.dev/channels/conda-forge/packages/numpy' },
      latest: '',
      conda_latest: '',
      lts: '',
      on_lts: '',
      ecosystem: 'conda',
    })
    // A non-divergent conda_latest (no latest_mismatch) stays plain text (Story 8.22).
    expect(sheet.rows[0].conda_latest).toBe('5.1.0')
  })

  it('marks a diverging conda-forge latest as red text (Story 8.22)', () => {
    const sheet = versionCurrencySheet([
      { name: 'flask', installed: '2.0.0', latest: '3.0.0', currency: 'behind-2+', lts: null, on_lts: null, ecosystem: 'pypi', conda_latest: '2.9.0', latest_mismatch: true },
      { name: 'click', installed: '8.0.0', latest: '8.1.0', currency: 'behind-1', lts: null, on_lts: null, ecosystem: 'pypi', conda_latest: '8.1.0', latest_mismatch: false },
    ])

    // Divergent → red-text marker the workbook builder styles; empty stays plain.
    expect(sheet.rows[0].conda_latest).toEqual({ text: '2.9.0', redText: true })
    expect(sheet.rows[1].conda_latest).toBe('8.1.0')
  })
})

describe('sbomComponentsSheet', () => {
  it('mirrors the Components view, including the Ecosystem column when present (Stories 8.26/8.27)', () => {
    const sheet = sbomComponentsSheet(
      makeDoc([
        {
          name: 'django',
          version: '5.2.1',
          type: 'library',
          purl: 'pkg:pypi/django@5.2.1',
          license: 'BSD-3-Clause',
          relationship: 'direct',
          ecosystem: 'pypi',
        },
        {
          name: 'numpy',
          version: '1.26.0',
          type: 'library',
          purl: 'pkg:conda/numpy@1.26.0',
          license: null,
          relationship: null,
          ecosystem: 'conda',
        },
      ]),
    )

    expect(sheet.name).toBe('SBOM Components')
    expect(sheet.columns.map((c) => c.header)).toEqual([
      'Name',
      'Version',
      'Type',
      'License',
      'Relationship',
      'Ecosystem',
      'PURL',
    ])
    expect(sheet.rows[0]).toEqual({
      name: 'django',
      version: '5.2.1',
      type: 'library',
      license: 'BSD-3-Clause',
      relationship: 'direct',
      ecosystem: 'pypi',
      purl: 'pkg:pypi/django@5.2.1',
    })
    // null license/relationship → '' (mirrors the other builders' ?? '').
    expect(sheet.rows[1]).toMatchObject({ name: 'numpy', license: '', relationship: '', ecosystem: 'conda' })
  })

  it('omits the Ecosystem and PURL columns when no component carries them', () => {
    const sheet = sbomComponentsSheet(
      makeDoc([
        { name: 'bare', version: '1.0', type: 'library', purl: null, license: 'MIT', relationship: null, ecosystem: null },
      ]),
    )

    expect(sheet.columns.map((c) => c.header)).toEqual(['Name', 'Version', 'Type', 'License', 'Relationship'])
    expect(sheet.rows[0]).toEqual({ name: 'bare', version: '1.0', type: 'library', license: 'MIT', relationship: '' })
    expect(sheet.rows[0]).not.toHaveProperty('ecosystem')
    expect(sheet.rows[0]).not.toHaveProperty('purl')
  })

  it('coerces null type/ecosystem/purl to empty strings when other rows carry those fields', () => {
    // The Ecosystem/PURL columns are present because the first component carries them, so
    // the second component's null values must fall through the `?? ''` guards (Story 8.27).
    const sheet = sbomComponentsSheet(
      makeDoc([
        {
          name: 'django',
          version: '5.2.1',
          type: 'library',
          purl: 'pkg:pypi/django@5.2.1',
          license: 'BSD-3-Clause',
          relationship: 'direct',
          ecosystem: 'pypi',
        },
        {
          name: 'ghost',
          version: '0.0',
          type: null,
          purl: null,
          license: null,
          relationship: null,
          ecosystem: null,
        },
      ]),
    )

    expect(sheet.columns.map((c) => c.header)).toContain('Ecosystem')
    expect(sheet.columns.map((c) => c.header)).toContain('PURL')
    expect(sheet.rows[1]).toEqual({
      name: 'ghost',
      version: '0.0',
      type: '',
      license: '',
      relationship: '',
      ecosystem: '',
      purl: '',
    })
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

describe('licensesSheet', () => {
  it('flattens one row per package across all tiers with the risk tier', () => {
    const sheet = licensesSheet({
      tiers: [
        { tier: 'Strong Copyleft', packages: [{ name: 'agpl-pkg', version: '1.0', license: 'AGPL-3.0-only' }] },
        { tier: 'Weak Copyleft', packages: [] },
        { tier: 'Permissive', packages: [{ name: 'mit-pkg', version: '3.0', license: 'MIT' }] },
      ],
      summary: { 'Strong Copyleft': 1, 'Weak Copyleft': 0, Permissive: 1 },
    })

    expect(sheet.name).toBe('Licenses')
    expect(sheet.columns.map((c) => c.header)).toEqual(['Package', 'Installed', 'License', 'Risk Tier'])
    // Empty tiers contribute no rows; one row per package, carrying its tier.
    expect(sheet.rows).toEqual([
      { name: 'agpl-pkg', version: '1.0', license: 'AGPL-3.0-only', tier: 'Strong Copyleft' },
      { name: 'mit-pkg', version: '3.0', license: 'MIT', tier: 'Permissive' },
    ])
  })
})
