import { useState, type ChangeEvent, type FormEvent } from 'react'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Container from '@mui/material/Container'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { uploadManifest } from '../api/manifests'

export function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [applicationId, setApplicationId] = useState('')
  const [componentName, setComponentName] = useState('')
  const [repositoryUrl, setRepositoryUrl] = useState('')
  const [sourceBranch, setSourceBranch] = useState('main')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<string | null>(null)

  function handleFile(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null)
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setResult(null)
    if (!file) {
      setError('Choose a manifest file to upload.')
      return
    }
    try {
      const response = await uploadManifest(file, {
        applicationId,
        componentName,
        repositoryUrl,
        sourceBranch,
      })
      setResult(`Uploaded — detected format: ${response.detected_format}`)
    } catch {
      setError('Upload failed. Check the file format and that all fields are filled in.')
    }
  }

  return (
    <Container maxWidth="sm" sx={{ py: 6 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Upload a manifest
      </Typography>
      <Box
        component="form"
        onSubmit={handleSubmit}
        sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}
      >
        {error && <Alert severity="error">{error}</Alert>}
        {result && <Alert severity="success">{result}</Alert>}
        <Button variant="outlined" component="label">
          {file ? file.name : 'Choose file'}
          <input type="file" hidden onChange={handleFile} />
        </Button>
        <TextField
          label="Application ID"
          value={applicationId}
          onChange={(e) => setApplicationId(e.target.value)}
          required
        />
        <TextField
          label="Component name"
          value={componentName}
          onChange={(e) => setComponentName(e.target.value)}
          required
        />
        <TextField
          label="Repository URL"
          type="url"
          value={repositoryUrl}
          onChange={(e) => setRepositoryUrl(e.target.value)}
          required
        />
        <TextField
          label="Source branch"
          value={sourceBranch}
          onChange={(e) => setSourceBranch(e.target.value)}
          required
        />
        <Button type="submit" variant="contained">
          Upload
        </Button>
      </Box>
    </Container>
  )
}
