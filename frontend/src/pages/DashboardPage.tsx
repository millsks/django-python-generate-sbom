import { useNavigate } from 'react-router-dom'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Container from '@mui/material/Container'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import { logout } from '../api/auth'
import { useAuth } from '../auth/AuthProvider'
import { NoOrgState } from '../components/NoOrgState'
import { OrgSwitcher } from '../components/OrgSwitcher'

export function DashboardPage() {
  const navigate = useNavigate()
  const { activeOrg } = useAuth()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  if (!activeOrg) {
    return <NoOrgState />
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <OrgSwitcher />
        <Button variant="outlined" onClick={handleLogout}>
          Log out
        </Button>
      </Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Dashboard
      </Typography>
      <Paper variant="outlined" sx={{ p: 4 }}>
        <Typography variant="body1" color="text.secondary">
          Your SBOM jobs will appear here.
        </Typography>
      </Paper>
    </Container>
  )
}
