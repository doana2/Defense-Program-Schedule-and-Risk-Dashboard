# Validation and acceptance record

## Completed checks

- 26 automated Python tests passed: calendar conversion; FS, SS, FF and SF calculations; parallel float; deadline vs network float; actual progress; constraints; rejected cycles/unknown IDs; resource loading; deterministic risk bounds and reproducibility; and the synthetic program's input integrity.
- Browser execution passed all six tabs, phase/path filtering, empty search, 14 health rows, six resource pools and change-history visibility with no JavaScript page errors. Desktop and mobile screenshots are included. See outputs/browser_checks.json.
- Excel formulas recalculated without detected formula errors. Changing one risk probability to zero set its expected impact to zero; restoring the input restored the original result. All six sheet previews were inspected.
- The two-page executive PDF was rendered and visually inspected. A text/chart overlap was corrected before delivery.
- The seven-slide PowerPoint passed package, layout and artifact-tool import checks. Its two editable charts have embedded workbook data; all slides were rendered and visually inspected during authoring.
- Project XML and Tableau XML were parsed for well-formedness. Their task/data references and archive contents were checked. These checks do not establish native desktop compatibility.

## Desktop acceptance still required

This environment does not have licensed Microsoft Project or Tableau Desktop. Therefore it cannot certify successful import, native recalculation or native dashboard rendering. The included HTML screenshots are explicitly labeled as the offline companion, not Tableau screenshots. There is no generated `.mpp` or `.pbix` file.

In Project, open the XML, confirm the WBS and predecessor types, compare baseline/current/actual dates, inspect resource overallocations, recalculate and record differences, then save a native `.mpp`. In Tableau, open the TWBX, reconnect CSVs if necessary, inspect all five worksheets and the four-sheet dashboard, and save a desktop-validated copy. USER_GUIDE.md supplies exact steps and a worksheet reconstruction recipe if the generated workbook XML needs adjustment.

Excel and PowerPoint were validated with the portable authoring runtime, not their desktop applications. Review them in your intended Office version for font substitutions and rendering differences.

## Scope boundaries

No resource leveling, authenticated approval workflow, official DCMA compliance certification, or real program performance claim is implied. The committed Office files are snapshots; the Python build refreshes analytical exports and the PDF/HTML/Project/Tableau outputs. See METHODOLOGY.md for metric definitions and assumptions.
