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

  it('supports multiple sheets in one workbook', () => {
    const workbook = buildWorkbook([
      { name: 'One', columns: [{ key: 'x', header: 'X' }], rows: [{ x: 1 }] },
      { name: 'Two', columns: [{ key: 'y', header: 'Y' }], rows: [{ y: 2 }] },
    ])

    expect(workbook.worksheets.map((w) => w.name)).toEqual(['One', 'Two'])
  })
})
