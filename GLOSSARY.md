# Glossary

Terms as they appear in code. Use these words in issues, tests and skills.

- **structure** — a buildable piece: `Structure` resource (`structures/*.tres`: `model` + `price`). `Builder.structures` is the palette; an item's **structure index** is its position in that array and is what the grid and saved maps store.
- **tile** / **cell** — one `GridMap` cell; holds a structure index or `-1` (empty). Saved as `DataStructure.position` (`Vector2i` of x, z).
- **selector** — the cursor (`Builder/Selector`) that follows the mouse over the grid and carries the orientation.
- **preview** — the instanced model of the selected structure inside `selector_container`; rebuilt by `update_structure()`.
- **index** — `Builder.index`, the structure index currently selected (`structure_next` / `structure_previous`).
- **orientation** — a cell's GridMap orthogonal index, taken from the selector's basis (`rotate` turns it 90°).
- **build** — place the selected structure on a tile; charges its `price` only when the tile held a different structure.
- **demolish** — clear a tile back to `-1`; no refund.
- **cash** — `DataMap.cash` (starts at 10000), shown by `cash_display` via `update_cash()`.
- **map** — `DataMap`: cash + `structures: Array[DataStructure]`, one **DataStructure** (position, orientation, structure index) per used cell; saved to `user://map.res`, sample in `sample map/map.res`.
