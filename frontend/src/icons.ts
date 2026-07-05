// Central icon vocabulary (Story 12.2): one icon per concept, imported everywhere so
// the same meaning always renders the same icon. Colors reference the 12.1 theme
// palette (SvgIcon `color` prop), never hard-coded values.
import type { SvgIconComponent } from '@mui/icons-material'
import AccountCircleIcon from '@mui/icons-material/AccountCircle'
import AddIcon from '@mui/icons-material/Add'
import AttachFileIcon from '@mui/icons-material/AttachFile'
import BugReportIcon from '@mui/icons-material/BugReport'
import BusinessIcon from '@mui/icons-material/Business'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import DashboardIcon from '@mui/icons-material/Dashboard'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutlined'
import DownloadIcon from '@mui/icons-material/Download'
import ErrorIcon from '@mui/icons-material/Error'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import GavelIcon from '@mui/icons-material/Gavel'
import GroupIcon from '@mui/icons-material/Group'
import HelpOutlineIcon from '@mui/icons-material/HelpOutlineOutlined'
import HistoryIcon from '@mui/icons-material/History'
import HomeIcon from '@mui/icons-material/Home'
import HourglassTopIcon from '@mui/icons-material/HourglassTop'
import InfoIcon from '@mui/icons-material/Info'
import Inventory2Icon from '@mui/icons-material/Inventory2'
import LogoutIcon from '@mui/icons-material/Logout'
import ReportProblemIcon from '@mui/icons-material/ReportProblem'
import AccountTreeIcon from '@mui/icons-material/AccountTree'
import TableViewIcon from '@mui/icons-material/TableView'
import UnfoldLessIcon from '@mui/icons-material/UnfoldLess'
import UnfoldMoreIcon from '@mui/icons-material/UnfoldMore'
import UpdateIcon from '@mui/icons-material/Update'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import VpnKeyIcon from '@mui/icons-material/VpnKey'
import WarningIcon from '@mui/icons-material/Warning'

// A palette color usable on an MUI SvgIcon (Chip color also accepts these).
export type IconColor = 'success' | 'warning' | 'error' | 'info' | 'disabled' | 'action'

// --- Navigation destinations ---
export const NavIcon = {
  home: HomeIcon,
  upload: CloudUploadIcon,
  history: HistoryIcon,
  keys: VpnKeyIcon,
  members: GroupIcon,
  organization: BusinessIcon,
} as const

// --- Primary actions ---
export const UploadActionIcon = CloudUploadIcon
export const ChooseFileIcon = AttachFileIcon
export const ExportIcon = TableViewIcon // export to Excel
export const DownloadActionIcon = DownloadIcon // download SBOM
export const DeleteActionIcon = DeleteOutlineIcon
export const AddActionIcon = AddIcon
export const ExpandAllIcon = UnfoldMoreIcon
export const CollapseAllIcon = UnfoldLessIcon
export const AccordionExpandIcon = ExpandMoreIcon
export const AccountIcon = AccountCircleIcon
export const LogoutActionIcon = LogoutIcon

// --- Report tabs (in the Results shell order) ---
export const TabIcon = {
  overview: DashboardIcon,
  sbom: Inventory2Icon,
  vulnerabilities: BugReportIcon,
  licenses: GavelIcon,
  graph: AccountTreeIcon,
  versions: UpdateIcon,
} as const

// --- Status / severity vocabularies: one icon+color per concept, everywhere ---

// Vulnerability severity.
export function severityIcon(severity: string): { Icon: SvgIconComponent; color: IconColor } {
  switch (severity) {
    case 'Critical':
      return { Icon: ErrorIcon, color: 'error' }
    case 'High':
      return { Icon: ReportProblemIcon, color: 'error' }
    case 'Medium':
      return { Icon: WarningIcon, color: 'warning' }
    case 'Low':
      return { Icon: InfoIcon, color: 'info' }
    default:
      return { Icon: HelpOutlineIcon, color: 'disabled' }
  }
}

// Version-currency class (current / behind-1 / behind-2+ / unknown).
export function currencyIcon(currency: string): { Icon: SvgIconComponent; color: IconColor } {
  if (currency === 'current') return { Icon: CheckCircleIcon, color: 'success' }
  if (currency === 'unknown') return { Icon: HelpOutlineIcon, color: 'disabled' }
  return { Icon: UpdateIcon, color: 'warning' } // behind-1 / behind-2+
}

// Job status (the SBOMJob status codes surfaced by JobStatusBadge).
export function jobStatusIcon(status: string): { Icon: SvgIconComponent; color: IconColor } {
  switch (status) {
    case 'SUCCESS':
      return { Icon: CheckCircleIcon, color: 'success' }
    case 'FAILED':
      return { Icon: ErrorIcon, color: 'error' }
    default:
      return { Icon: HourglassTopIcon, color: 'info' } // PENDING / PROGRESS
  }
}
