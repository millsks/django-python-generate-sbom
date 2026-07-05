// App footer (Story 12.3): product name + version and links to the docs, repo, and
// license. Sits at the bottom of the shell across all pages/auth states.
import Box from '@mui/material/Box'
import Link from '@mui/material/Link'
import Typography from '@mui/material/Typography'
import { APP_NAME, APP_VERSION, DOCS_URL, REPO_URL } from '../config'

const LICENSE_URL = `${REPO_URL}/blob/main/LICENSE`

function FooterLink({ href, children }: { href: string; children: string }) {
  return (
    <Link href={href} target="_blank" rel="noopener noreferrer" variant="body2" color="text.secondary" underline="hover">
      {children}
    </Link>
  )
}

export function Footer() {
  return (
    <Box
      component="footer"
      sx={{
        px: 3,
        py: 2,
        mt: 'auto',
        borderTop: 1,
        borderColor: 'divider',
        bgcolor: 'background.paper',
        display: 'flex',
        flexWrap: 'wrap',
        gap: 2,
        alignItems: 'center',
        justifyContent: 'space-between',
      }}
    >
      <Typography variant="body2" color="text.secondary">
        {APP_NAME} v{APP_VERSION}
      </Typography>
      <Box sx={{ display: 'flex', gap: 2 }}>
        <FooterLink href={DOCS_URL}>Docs</FooterLink>
        <FooterLink href={REPO_URL}>GitHub</FooterLink>
        <FooterLink href={LICENSE_URL}>License</FooterLink>
      </Box>
    </Box>
  )
}
