import { useEffect, useState } from 'react'
import FormControl from '@mui/material/FormControl'
import InputLabel from '@mui/material/InputLabel'
import MenuItem from '@mui/material/MenuItem'
import Select, { type SelectChangeEvent } from '@mui/material/Select'
import { getOrgs, switchOrg, type OrgListItem } from '../api/orgs'

export function OrgSwitcher() {
  const [orgs, setOrgs] = useState<OrgListItem[]>([])
  const [active, setActive] = useState('')

  useEffect(() => {
    getOrgs()
      .then((list) => {
        setOrgs(list)
        const current = list.find((org) => org.active)
        if (current) setActive(current.slug)
      })
      .catch(() => {})
  }, [])

  async function handleChange(event: SelectChangeEvent) {
    const slug = event.target.value
    setActive(slug)
    await switchOrg(slug)
    window.location.reload()
  }

  if (orgs.length === 0) {
    return null
  }

  return (
    <FormControl size="small" sx={{ minWidth: 200 }}>
      <InputLabel id="org-switcher-label">Org</InputLabel>
      <Select
        labelId="org-switcher-label"
        label="Org"
        value={active}
        onChange={handleChange}
        // Give the dropdown a solid surface (not transparent) in both themes.
        MenuProps={{ slotProps: { paper: { sx: { bgcolor: 'background.paper' } } } }}
      >
        {orgs.map((org) => (
          <MenuItem key={org.slug} value={org.slug}>
            {org.name}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  )
}
