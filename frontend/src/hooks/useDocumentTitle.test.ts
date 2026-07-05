import { renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { APP_NAME } from '../config'
import { useDocumentTitle } from './useDocumentTitle'

describe('useDocumentTitle', () => {
  afterEach(() => {
    document.title = ''
  })

  it('sets the tab title to "<page> · <APP_NAME>"', () => {
    renderHook(() => useDocumentTitle('Upload'))
    expect(document.title).toBe(`Upload · ${APP_NAME}`)
  })

  it('falls back to the app name when no page is given', () => {
    renderHook(() => useDocumentTitle())
    expect(document.title).toBe(APP_NAME)
  })

  it('uses the product name, not the Vite "frontend" placeholder', () => {
    expect(APP_NAME).toBe('Generate SBOM')
    expect(APP_NAME).not.toBe('frontend')
  })
})
