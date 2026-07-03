import Container from '@mui/material/Container'
import Typography from '@mui/material/Typography'

export function HomePage() {
  return (
    <Container maxWidth="md" sx={{ py: 6 }}>
      <Typography variant="h3" component="h1" gutterBottom>
        django-python-generate-sbom
      </Typography>
      <Typography variant="body1">
        Generate Software Bills of Materials from Python dependency manifests.
      </Typography>
    </Container>
  )
}
