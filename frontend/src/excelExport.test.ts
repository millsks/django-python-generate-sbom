import { describe, expect, it } from 'vitest'
import { buildWorkbook } from './excelExport'

describe('buildWorkbook', () => {
  it('creates a worksheet per spec with a bold header row and data rows', () => {
    const workbook = buildWorkbook([
      {
        name: 'Test',
        columns: [
          { key: 'a', header: 'Alpha' },
          { key: 'b', header: 'Beta' },
        ],
        rows: [
          { a: 1, b: 2 },
          { a: 3, b: 4 },
        ],
      },
    ])

    const worksheet = workbook.getWorksheet('Test')!
    expect(worksheet.columnCount).toBe(2)
    expect(worksheet.rowCount).toBe(3) // header + 2 data rows
    expect(worksheet.getRow(1).getCell(1).value).toBe('Alpha')
    expect(worksheet.getRow(1).font?.bold).toBe(true)
    expect(worksheet.getRow(2).getCell(1).value).toBe(1)
    expect(worksheet.getRow(3).getCell(2).value).toBe(4)
  })

  it('renders a hyperlink cell for a { text, hyperlink } value', () => {
    const workbook = buildWorkbook([
      {
        name: 'Links',
        columns: [{ key: 'pkg', header: 'Package' }],
        rows: [{ pkg: { text: 'django', hyperlink: 'https://pypi.org/project/django/' } }],
      },
    ])

    const cell = workbook.getWorksheet('Links')!.getRow(2).getCell(1)
    expect(cell.value).toMatchObject({ text: 'django', hyperlink: 'https://pypi.org/project/django/' })
    expect(cell.font?.underline).toBe(true)
  })

  it('renders a red-font cell for a { text, redText } value (Story 8.22)', () => {
    const workbook = buildWorkbook([
      {
        name: 'Reds',
        columns: [{ key: 'v', header: 'Value' }],
        rows: [{ v: { text: '2.9.0', redText: true } }, { v: 'plain' }],
      },
    ])

    const ws = workbook.getWorksheet('Reds')!
    // The marker is unwrapped to its text and given a red font.
    const redCell = ws.getRow(2).getCell(1)
    expect(redCell.value).toBe('2.9.0')
    expect(redCell.font?.color?.argb).toBe('FFD32F2F')
    // A plain value keeps the default font (no red).
    const plainCell = ws.getRow(3).getCell(1)
    expect(plainCell.value).toBe('plain')
    expect(plainCell.font?.color?.argb).toBeUndefined()
  })

  it('supports multiple sheets in one workbook', () => {
    const workbook = buildWorkbook([
      { name: 'One', columns: [{ key: 'x', header: 'X' }], rows: [{ x: 1 }] },
      { name: 'Two', columns: [{ key: 'y', header: 'Y' }], rows: [{ y: 2 }] },
    ])

    expect(workbook.worksheets.map((w) => w.name)).toEqual(['One', 'Two'])
  })
})
