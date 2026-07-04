// Shared client-side Excel export (Stories 8.12–8.15). Builds an .xlsx in the
// browser from report data already fetched — no backend endpoint. Reused by the
// per-tab exports and the Overview combined workbook.
import ExcelJS from 'exceljs'

export interface ExcelColumn {
  key: string
  header: string
}

// A clickable cell: exceljs renders `{ text, hyperlink }` as a hyperlink.
export interface HyperlinkCell {
  text: string
  hyperlink: string
}

export interface SheetSpec {
  name: string // Excel sheet name (keep ≤ 31 chars, no []:*?/\)
  columns: ExcelColumn[]
  rows: Record<string, unknown>[] // a value may be a HyperlinkCell for a linked cell
}

function isHyperlink(value: unknown): value is HyperlinkCell {
  return typeof value === 'object' && value !== null && 'hyperlink' in value
}

// Build a workbook from one or more sheet specs (one sheet per report).
export function buildWorkbook(sheets: SheetSpec[]): ExcelJS.Workbook {
  const workbook = new ExcelJS.Workbook()
  for (const sheet of sheets) {
    const worksheet = workbook.addWorksheet(sheet.name)
    worksheet.columns = sheet.columns.map((column) => ({ key: column.key, header: column.header }))
    worksheet.getRow(1).font = { bold: true }
    for (const row of sheet.rows) {
      const added = worksheet.addRow(row)
      // Style hyperlink cells like links (exceljs doesn't do this automatically).
      added.eachCell((cell) => {
        if (isHyperlink(cell.value)) cell.font = { color: { argb: 'FF0563C1' }, underline: true }
      })
    }
  }
  return workbook
}

// Generate the workbook bytes and trigger a browser download.
export async function downloadWorkbook(workbook: ExcelJS.Workbook, filename: string): Promise<void> {
  const buffer = await workbook.xlsx.writeBuffer()
  const blob = new Blob([buffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}
