# Presi — lighting plot and DMX patch sheet

One landscape A4 page: plan view, fixture legend, and the full DMX patch by address.
Edit it in a browser, then print or save it as a PDF.

## Files

| File | What it is |
| :--- | :--- |
| `index.html` | The whole sheet. Open it in any browser; no build, no network. |
| `presi-plot.pdf` | The current one-page export, ready to send. |
| `patch.csv` | The same patch as plain data, for a console or a spreadsheet. |
| `assets/blueprint-sheet.png` | The original generated sheet, kept for reference. |

## Edit it

Open `index.html` in a browser and change any field in place:

- **Venue, room, title, brand, console** — click the text and type. "YOUR BRAND" is a placeholder for the shop logo or name.
- **Fixture type, ID, address, channel count** — click a cell in the DMX patch table.
- **Brand** — the blank column next to each fixture type. Fill it once per model.
- **Add fixture** — appends a row at the end of the patch.
- **×** — removes a row.

Edits save in that browser's local storage. They do not change the file, so use
**Export JSON** to keep a copy and **Import JSON** to bring it back or move it to
another machine. **Export CSV** gives a spreadsheet copy. **Reset** returns to the
patch as generated.

## Export the PDF

Click **Print / save as PDF**, choose the A4 landscape page, and save. Chrome and
Safari both produce a single page with the dark background; keep
"background graphics" on in Chrome.

## Put it online

GitHub Pages, so a link can be shared and the file edited from the repo:

1. Create a repository, for example `presi-plot`.
2. Put `index.html`, `patch.csv` and `assets/` at the top level.
3. In the repository, open **Settings → Pages**, set **Source** to *Deploy from a branch*, branch `main`, folder `/ (root)`.
4. The sheet appears at `https://<account>.github.io/presi-plot/`.

Anyone with edit rights can change the JSON or the HTML. Anyone with the link can
only view it. A visitor's edits stay in their own browser.

## Where the data comes from

Recovered from the show file `Presi.dvc`, made on an ADJ myDMX 3.0 desk and
migrated toward Wolfmix WMX1.

Real: fixture names, DMX addresses, channel counts, group names, and the 2D
positions (POSX/POSY taken from the desk's own patch layout).

Not real: fixture heights, and the channel map inside each fixture. The profiles
were never decrypted, so the sheet gives start address and width only.

Universe 1, 41 fixtures, 512 of 512 channels used, no gaps and no overlaps.

## Notes for whoever patches it

- The fixture names keep the desk's own numbering. It skips `.11` and jumps from `.15` to `.38`, so patch by address, not by name order.
- Aura 25 and 26 are 25 channels each; the laser is 28; the DJ beams are 9 each.
- Moving heads 1–15 fill 1–224, the RGBW pars sit inside 225–256, and heads 38 and 39 take 257–288.

## CAD version

`presi-plot.dxf` is the same sheet as real CAD geometry, drawn at 1:100 on an A3
landscape sheet, ready for AutoCAD, BricsCAD, Vectorworks, QCAD or LibreCAD.

| Layer | Holds |
| :--- | :--- |
| `border` | Sheet frame, zone marks, room outline, title block |
| `truss` | Truss back and front, dashed |
| `grid` | 1 m construction grid |
| `FIX-MOVING`, `FIX-RGBW`, `FIX-STAGE`, `FIX-DJ`, `FIX-AURA`, `FIX-LASER` | Fixture symbols, one layer per group |
| `text` | Labels, notes, legend |
| `dim` | Dimensions and scale bar |
| `patch` | The DMX patch table |

Every fixture is a real symbol at its recovered position, with a leader to its ID
and address range. The patch table is drawn as lines and text, not a picture, so
it can be edited in CAD.

DWG is not produced here: it is a closed binary format and no converter is
installed. Open the DXF in AutoCAD and use **Save As → DWG**, which keeps every
layer and entity.

`presi-plot-cad.pdf` is the plotted sheet, and `presi-plot-dxf.png` is a quick preview.

## Export from the page

Two controls in the toolbar:

- **Export DXF** writes the sheet you are looking at as DXF, using the same code
  path that draws the preview. Every fixture, leader, dimension, the legend, the
  patch table and the title block come out as CAD entities on named layers.
- **Preview: colour / black & white** switches the whole sheet, and the DXF with
  it. Black and white writes every layer at colour 7, so the drawing plots as
  line art on paper or in a PDF.

The DXF is generated in the browser, so the export always matches the data and
the mode on screen. Nothing is uploaded.

`render_dxf.py` plots a DXF to PNG and PDF without computing any geometry; it
draws what the file contains.

## Visual style

The screen UI follows SRCL (sacred.computer) terminal conventions: monospace
throughout, bracketed uppercase actions with key hints, `▾` section markers, a
dashed status line, and hairline borders instead of cards and shadows. The printed
sheet keeps the same type system so the PDF and the screen agree.

## Editing the room

The building is not surveyed, so its geometry is a control, not a fact. Above the
plan: room width, room depth, and the back and front truss offsets in metres. They
drive the plan drawing, the dimension strings, the DXF, and the printed sheet.
Defaults come from the fixture extents plus 1.5 m, which is a guess.

The fixture positions themselves come from the show file and are not editable here;
edit the JSON if a fixture moves.

## Legend and addresses

The fixture legend draws the same symbols as the plan and the DXF — circle with
cross for heads, plain square for pars, square with a diagonal for panels, rectangle
for beams, double circle for aura and laser — and gives each group's address range,
so the legend, the plan labels and the patch table all agree.

## Print is the drawing

The printed sheet is always the CAD plot: black linework on white, with a title
block. The screen's colour/black-and-white switch changes the on-screen preview and
the DXF layer colours, not the print.

## Logo

The brand slot takes an image: click it, or drag a PNG, SVG or JPEG onto it. Keep
the file under 1.5 MB. It stays in that browser, like the other edits, and appears
on the printed sheet.

Most shop logos are light on dark. The print sheet is white, so press **INV** next
to the slot to flip the logo to dark ink. Press **×** to remove it.

The DXF has no raster support, so the logo is print-only; the title block carries
the drawing number and scale instead.

## Verification

`verify.py` is the hard pass. It reads `patch.csv`, the sheet's data and
`presi-plot.dxf`, then asserts 65 things: every fixture name, address and channel
count against the source; 1–512 fully allocated with no overlaps; every ID label
and address range on the plan; every symbol at its recovered coordinate and the
right shape for its group; legend ranges and quantities; all 41 patch rows; the
dimensions, room size and scale bar; the title block fields; nothing outside the
frame; no overlapping table cells or fixture labels.

Run it after any edit:

    python3 verify.py

It exits non-zero on a failure and prints the check that failed. `VERIFICATION.txt`
holds the last run.
