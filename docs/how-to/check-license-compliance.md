# Check license compliance

**Goal:** see the license of every dependency and flag legal risk.

## Steps

1. Open a finished job's **Results** page and select the **Licenses** tab.
2. Review packages grouped by **risk tier**:
    - **Strong Copyleft** (e.g. AGPL, GPL) — highest obligation; review before shipping.
    - **Weak Copyleft** (e.g. LGPL, MPL) — moderate obligation.
    - **Permissive** (e.g. MIT, BSD, Apache-2.0) — lowest obligation.
3. Focus on the copyleft tiers first — these are the licenses most likely to carry
   redistribution or source-disclosure obligations.
4. For any package whose license is unacceptable for your project, find an alternative or
   confirm your usage complies, then update your manifest and re-run.

## Result

You have each dependency's license sorted by legal risk. Use
[Export a report to Excel](export-to-excel.md) to hand the list to legal or include it in
an audit. See also the [User Guide](../user-guide/index.md).
