import { useState, type ChangeEvent, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import Container from '@mui/material/Container'
import MenuItem from '@mui/material/MenuItem'
import Paper from '@mui/material/Paper'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { DEFAULT_OUTPUT_FORMAT, generateSbom, OUTPUT_FORMATS } from '../api/jobs'
import { useAuth } from '../auth/AuthProvider'
import { NoOrgState } from '../components/NoOrgState'
import { ChooseFileIcon, UploadActionIcon } from '../icons'

export function UploadPage() {
  const navigate = useNavigate()
  const { activeOrg } = useAuth()
  const [file, setFile] = useState<File | null>(null)
  const [applicationId, setApplicationId] = useState('')
  const [componentName, setComponentName] = useState('')
  const [repositoryUrl, setRepositoryUrl] = useState('')
  const [sourceBranch, setSourceBranch] = useState('main')
  const [outputFormat, setOutputFormat] = useState<string>(DEFAULT_OUTPUT_FORMAT)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  function handleFile(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null)
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    if (!file) {
      setError('Choose a manifest file to generate an SBOM.')
      return
    }
    setSubmitting(true)
    try {
      const response = await generateSbom(file, {
        applicationId,
        componentName,
        repositoryUrl,
        sourceBranch,
        outputFormat,
      })
      navigate(`/results/${response.task_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed. Check the file and try again.')
      setSubmitting(false)
    }
  }

  if (!activeOrg) {
    return <NoOrgState />
  }

  return (
    <Container maxWidth="sm" sx={{ py: 6 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Generate an SBOM
      </Typography>
      <Paper
        component="form"
        variant="outlined"
        onSubmit={handleSubmit}
        sx={{ display: 'flex', flexDirection: 'column', gap: 2, p: 3 }}
      >
        {error && <Alert severity="error">{error}</Alert>}
        <Button variant="outlined" component="label" startIcon={<ChooseFileIcon />}>
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
        <TextField
          select
          label="Output format"
          value={outputFormat}
          onChange={(e) => setOutputFormat(e.target.value)}
        >
          {OUTPUT_FORMATS.map((f) => (
            <MenuItem key={f.value} value={f.value}>
              {f.label}
            </MenuItem>
          ))}
        </TextField>
        <Button type="submit" variant="contained" disabled={submitting} startIcon={<UploadActionIcon />}>
          {submitting ? 'Generating…' : 'Generate SBOM'}
        </Button>
      </Paper>
    </Container>
  )
}
