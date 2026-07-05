import { useEffect } from 'react'
import { APP_NAME } from '../config'

// Story 12.6: set the browser tab title to "<page> · <APP_NAME>", or just APP_NAME when
// no page is given. The base title (frontend/index.html) is already APP_NAME, so a page
// that omits its own title still reads correctly.
export function useDocumentTitle(page?: string): void {
  useEffect(() => {
    document.title = page ? `${page} · ${APP_NAME}` : APP_NAME
  }, [page])
}
