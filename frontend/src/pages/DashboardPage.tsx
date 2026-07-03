import { useNavigate } from 'react-router-dom'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Container from '@mui/material/Container'
import Typography from '@mui/material/Typography'
import { logout } from '../api/auth'
import { OrgSwitcher } from '../components/OrgSwitcher'

export function DashboardPage() {
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
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
      <Typography variant="body1">Your SBOM jobs will appear here.</Typography>
    </Container>
  )
}
