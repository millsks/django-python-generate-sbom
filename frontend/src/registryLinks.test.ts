import { describe, expect, it } from 'vitest'
import { ecosystemLabel, registryUrl } from './registryLinks'

describe('registryUrl', () => {
  it('links PyPI packages to their pypi.org project page (version-specific)', () => {
    expect(registryUrl({ name: 'django', version: '5.2.1', ecosystem: 'pypi' })).toBe(
      'https://pypi.org/project/django/5.2.1/',
    )
  })

  it('falls back to the project page when no version is given', () => {
    expect(registryUrl({ name: 'django', ecosystem: 'pypi' })).toBe('https://pypi.org/project/django/')
  })

  it('links Conda packages to the prefix.dev conda-forge channel explorer', () => {
    expect(registryUrl({ name: 'numpy', version: '1.26.0', ecosystem: 'conda' })).toBe(
      'https://prefix.dev/channels/conda-forge/packages/numpy',
    )
  })

  it('returns null for a missing/unexpected ecosystem', () => {
    expect(registryUrl({ name: 'mystery', version: '1.0' })).toBeNull()
    expect(registryUrl({ name: 'mystery', version: '1.0', ecosystem: 'npm' })).toBeNull()
  })

  it('encodes names with special characters', () => {
    expect(registryUrl({ name: 'a b', version: '1.0', ecosystem: 'pypi' })).toBe(
      'https://pypi.org/project/a%20b/1.0/',
    )
  })
})

describe('ecosystemLabel', () => {
  it('labels known ecosystems and null otherwise', () => {
    expect(ecosystemLabel('pypi')).toBe('PyPI')
    expect(ecosystemLabel('conda')).toBe('Conda')
    expect(ecosystemLabel(undefined)).toBeNull()
    expect(ecosystemLabel('npm')).toBeNull()
  })
})
