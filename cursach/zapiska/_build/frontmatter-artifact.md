# Contract for the two reference front pages

Reference: `cursach/dop_file/Правила оформления КР по проектированию АСОИУ_2026 + Темы КР.docx`.
SHA256: `F67149603FC9571FC1AEA82778B9EB965E6E48774F0EF2EA62BF231221A72AA5`.
The retained reference is read-only. Seven rendered reference pages already exist in `%TEMP%/codex-docx-render/reference-qa`; only its first two page patterns are reused.

## Geometry and source elements

A4 portrait. First-page source geometry: 11906 × 16838 twips; top 851, bottom 1134, left 1701, right 567, header/footer 0. Page two takes its geometry directly from the reference second section. The title has a first-page footer without a number. Assignment carries page number 2. Existing main-text sections and their page geometry remain under the original body contract.

Source locators are zero-based children of `word/document.xml/w:document/w:body`:

- 0–26: title. Ministry 0–1; bold uppercase university 3; institute table 5; approval table 7; topic table 12 and its caption 13; document type 15–16; course/code table 17; code caption 18; student and norm-control table 19; grade 21; city/year 26.
- 27–42: assignment. Ministry 27–28, university 30; heading 33–34; main form table 35 with embedded literature table; graphic-sheet count 36; date 38; receipt signature table 39; submission date 40; supervisor table 41.

Typography, paragraph spacing, tabs, row heights, borders, table grids, labels and rules are copied as XML from those source components. Main text is TNR 14 pt. Field labels such as signature/name/group use their smaller source typography. University and document heading retain source bold/caps. The title topic retains the source regular centered typography and underlined rows.

## Editable slots and permitted deviations

Fill student/group with D. S. Privalikhin / ISIb-23-1 in Russian; supervisor and norm control remain R. D. Gutgarts; keep 2026 and the template dates. Fill the supplied exact topic, split over source ruled topic rows. Unknown variant, signatures, grade and graphic-sheet count remain blank. Replace the unrelated petroleum-system example in the input-data slot with information about the sports-nutrition preproject subject.

Remove source teaching annotations: floating variant callout and background, red instructional placeholder text, yellow/green highlights. Filled values are black. Keep normal printed labels below the ruled fields. Remove only surplus blank spacers needed to accommodate the longer supplied topic; do not shrink fonts or replace tables by space-separated text.

## Package/field preservation

Copy all referenced source styles with a unique `FrontRef_` style-ID prefix, including basedOn/next/link dependencies, so body styles do not change. Copy numbering definitions with remapped numeric IDs. The imported pages use no drawings, comments, content controls or links to external media. Existing body media, relationships, bookmarks, equations, fields and recurring page furniture remain intact unless removal of superseded source references requires a text change. TOC uses native TC/PAGEREF entries with recached pages; no Word GUI is available, so set updateFields=true after render verification.

## Fidelity gates

Compare title and assignment visually with reference pages 1–2, excluding the documented annotations and filled slots. Both forms must fit exactly one page each, preserve the table-based alignment/underlining/captions, and contain no clipping. Render all final pages; check page count and TOC, and verify that own TZ/TP/manual references and their excerpt images are absent from visible content and bibliography. Confirm reference SHA256 unchanged.
