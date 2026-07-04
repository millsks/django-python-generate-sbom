// Build the registry detail-page URL for a package by ecosystem (Story 8.9).
// PyPI → pypi.org project page; Conda → prefix.dev's conda-forge channel explorer.
// Returns null for a missing/unexpected ecosystem so the caller renders plain text.
export function registryUrl(pkg: { name: string; version?: string | null; ecosystem?: string | null }): string | null {
  const name = encodeURIComponent(pkg.name)
  if (pkg.ecosystem === 'conda') {
    return `https://prefix.dev/channels/conda-forge/packages/${name}`
  }
  if (pkg.ecosystem === 'pypi') {
    return pkg.version
      ? `https://pypi.org/project/${name}/${encodeURIComponent(pkg.version)}/`
      : `https://pypi.org/project/${name}/`
  }
  return null
}

// Human label for the source chip; null when the ecosystem is unknown.
export function ecosystemLabel(ecosystem?: string | null): string | null {
  if (ecosystem === 'conda') return 'Conda'
  if (ecosystem === 'pypi') return 'PyPI'
  return null
}
