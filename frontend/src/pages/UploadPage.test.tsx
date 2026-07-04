import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom'
import { UploadPage } from './UploadPage'
import { ApiError } from '../api/client'
import { generateSbom } from '../api/jobs'

vi.mock('../api/jobs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/jobs')>()
  return { ...actual, generateSbom: vi.fn() }
})
const mockGenerate = generateSbom as Mock

function ResultsStub() {
  const { taskId } = useParams()
  return <div>results-page:{taskId}</div>
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/upload']}>
      <Routes>
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/results/:taskId" element={<ResultsStub />} />
      </Routes>
    </MemoryRouter>,
  )
}

async function fillRequiredFields(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/application id/i), 'A-1')
  await user.type(screen.getByLabelText(/component name/i), 'svc')
  await user.type(screen.getByLabelText(/repository url/i), 'https://github.com/a/b')
}

// No beforeEach reset/clear of mockGenerate on purpose: clearing a mock that a
// later test gives mockRejectedValue triggers a false vitest unhandled-rejection.
// Tests assert with toHaveBeenCalledWith or a per-test call-count delta instead.
describe('UploadPage', () => {
  it('submits to generate and navigates to the new job results page', async () => {
    mockGenerate.mockResolvedValue({
      task_id: 'abc-123',
      status: 'PENDING',
      status_url: '/api/v1/sbom/status/abc-123/',
      estimated_seconds: 30,
    })
    const { container } = renderPage()
    const user = userEvent.setup()

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(fileInput, new File(['requests==2.0'], 'requirements.txt'))
    await fillRequiredFields(user)
    await user.click(screen.getByRole('button', { name: 'Generate SBOM' }))

    expect(await screen.findByText('results-page:abc-123')).toBeInTheDocument()
    expect(mockGenerate).toHaveBeenCalledWith(
      expect.any(File),
      expect.objectContaining({ outputFormat: 'cdx-json' }),
    )
  })

  it('sends the chosen output format', async () => {
    mockGenerate.mockResolvedValue({ task_id: 't', status: 'PENDING', status_url: '', estimated_seconds: 1 })
    const { container } = renderPage()
    const user = userEvent.setup()

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(fileInput, new File(['x'], 'requirements.txt'))
    await fillRequiredFields(user)
    await user.click(screen.getByRole('combobox', { name: /output format/i }))
    await user.click(screen.getByRole('option', { name: 'SPDX (JSON)' }))
    await user.click(screen.getByRole('button', { name: 'Generate SBOM' }))

    expect(mockGenerate).toHaveBeenCalledWith(
      expect.any(File),
      expect.objectContaining({ outputFormat: 'spdx-2.3' }),
    )
  })

  it('surfaces the server error and stays on the form', async () => {
    mockGenerate.mockRejectedValue(new ApiError('Concurrent job limit reached', 429, 'rate_limited'))
    const { container } = renderPage()
    const user = userEvent.setup()

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(fileInput, new File(['x'], 'requirements.txt'))
    await fillRequiredFields(user)
    await user.click(screen.getByRole('button', { name: 'Generate SBOM' }))

    expect(await screen.findByText('Concurrent job limit reached')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate SBOM' })).toBeInTheDocument()
  })

  it('asks for a file when none is chosen', async () => {
    renderPage()
    const user = userEvent.setup()

    // Satisfy the required text fields so the submit handler runs; omit the file.
    await fillRequiredFields(user)
    const before = mockGenerate.mock.calls.length
    await user.click(screen.getByRole('button', { name: 'Generate SBOM' }))

    expect(await screen.findByText(/choose a manifest file/i)).toBeInTheDocument()
    expect(mockGenerate.mock.calls.length).toBe(before) // no submit for this click
  })
})
