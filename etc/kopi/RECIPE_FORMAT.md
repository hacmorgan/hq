# Recipe format (kopi / dashboard)

Recipes under `etc/kopi/recipes/` are **YAML**. Files have **no extension** — the `kopi`
CLI and the dashboard list them by path, so adding `.yaml` would change their displayed
names. YAML doesn't need a file extension to be valid.

- The `kopi` CLI just opens the file in `$EDITOR` — it never parses the contents.
- The dashboard backend (`hq/gui/dashboard/lib/server.py`) parses the YAML and returns it
  as structured JSON; the Flutter UI renders a structured, **scalable** view and lets you
  edit the raw YAML.

## Top-level keys (all optional)

| key           | type            | purpose |
|---------------|-----------------|---------|
| `name`        | string          | Display name. If omitted the UI uses the file path. Only set it when it reads better than the filename. |
| `source`      | string          | URL the recipe was adapted from (the add-recipe skill sets this). |
| `uses`        | list            | Sub-recipes this one builds on, by filename or path (e.g. `crackling`, `veg/beetroot-puree`). Drives the dashboard graph's edges. |
| `yield`       | string          | Freeform serving/yield note, e.g. `serves 2`, `per omelette`, `for a 650g rack`. |
| `notes`       | string (block)  | Freeform prose: background, tips, variants, the long `---` explanation blocks. Use a YAML block scalar (`\|`). |
| `ingredients` | list            | The recipe's main / ungrouped ingredients (see **Ingredient entry**). |
| `steps`       | list            | The recipe's main / ungrouped steps (see **Step entry**). |
| `components`  | list            | Named sub-preparations, each with `name` and its own `ingredients`/`steps`/`notes`. Use when a recipe has distinct parts (rub + sauce + glaze, tangzhong + dough + bake, …). |

A recipe may use `ingredients`/`steps`, **or** `components`, **or both** — e.g. the main
meat as a top-level `basis` ingredient plus a `rub` and a `sauce` component.

## Ingredient entry

Each ingredient is a block-style mapping (one field per line, **not** flow `{ }` style):

```yaml
- item: salt          # required: name (keep the original's lowercase wording)
  mass: 3             # optional: grams — the usual scalable amount
  qty: 2              # optional: numeric count/volume (also scales)
  unit: tsp           # optional: unit for qty — tsp, tbsp, ea, clove, cup, ml, sprig, can, part, …
  basis: true         # optional: marks THE ONE determining ingredient for scaling
  optional: true      # optional: this ingredient is optional
  note: Suntory Toki is best   # optional: parenthetical / prep / substitution info
```

- A bare string is allowed when there's no amount: `- lettuce`.
- An ingredient may carry **both** `mass` and `qty`+`unit` — e.g. `20g (1 tbsp)` becomes
  `item: brown sugar` / `mass: 20` / `qty: 1` / `unit: tbsp`. Both scale together.
- `unit: ea` means a plain count ("each"), e.g. `3 lemons` → `qty: 3`, `unit: ea`.

### Scaling and `basis`

- **At most one** ingredient in the whole recipe (top-level *or* in any component) may have
  `basis: true`. It is the **determining ingredient** — usually the main thing you have
  ("for 500g chicken breast").
- Its `mass` (or, failing that, `qty`) is the **reference amount**. In the dashboard you
  enter your actual amount and every `mass`/`qty` in the recipe (top-level **and** all
  components) is multiplied by `your amount / reference`.
- Put the basis on whatever drives the recipe. For "for 500g chicken: 3g salt, …", add the
  chicken itself as an ingredient (`item: chicken`, `mass: 500`, `basis: true`), then the
  spices.
- **Omit `basis` entirely** for recipes with no determining ingredient (pure procedures,
  pure ratios, fixed batches). The UI then shows no scaling input.

## Step entry

- Usually a plain string: `- pat dry`.
- For a step with sub-points, use a mapping with `substeps`:

```yaml
- step: apply rub, salt first then the rest
  substeps:
    - 2:1 meat:bone side
```

- Keep temperatures, times, and technique in the step text, e.g. `bake at 180°C for 40 mins`.

## Linking recipes (`uses`)

List the sub-recipes a recipe genuinely builds on, so the dashboard graph can draw
"uses" edges between them:

```yaml
uses:
  - crackling           # resolved by filename (unique across the tree)
  - veg/beetroot-puree  # or by full path
```

Add only real dependencies — these edges are meant to be intentional. "Happens to share
an ingredient" is a separate, optional overlay in the graph UI, not a `uses` link.

## Ratios & proportions

For recipes expressed purely as ratios (no absolute amounts), prefer `unit: part` and no
`basis`:

```yaml
ingredients:
  - item: rose
    qty: 1
    unit: part
  - item: grape soju
    qty: 2
    unit: part
```

For more involved ratio explanations (several alternative ratios — margarita, v60,
steamed-beverages), keep them in `notes`.

---

## Worked examples

### "for Ng X" seasoning — `meat/portugese-chicken`

```yaml
yield: per 500g meat
ingredients:
  - item: chicken
    mass: 500
    basis: true
  - item: salt
    mass: 3
    note: add 4g more if not brined
  - item: white pepper
    mass: 0.5
  - item: paprika
    mass: 3
steps:
  - rub meat, then cover with oil and bbq
```

### Simple drink — `milk-based/hot-cocoa`

```yaml
ingredients:
  - item: water
    mass: 300
    note: 96°C
  - item: cadbury baking cocoa powder
    mass: 6
  - item: sugar
    mass: 15
  - item: milk
    mass: 40
```

### Multi-component — `meat/beef-ribs` (abbreviated)

```yaml
yield: 3 short ribs, 1kg incl. bone
ingredients:
  - item: beef short ribs
    mass: 1000
    basis: true
components:
  - name: rub
    ingredients:
      - item: brown sugar
        mass: 20
        qty: 1
        unit: tbsp
        note: sub white
      - item: paprika
        mass: 5
        qty: 2
        unit: tsp
  - name: sauce
    ingredients:
      - item: ketchup
        mass: 335
        note: or Aussie tomato sauce
      - item: water
        qty: 500
        unit: ml
    steps:
      - place all ingredients in saucepan and simmer 45 mins
  - name: procedure (oven)
    steps:
      - oven to 160°C
      - coat ribs in rub
      - bake meat side down 3.5hr covered until meat pulls apart, basting intermittently
```

### Pure ratio — `alcoholic/roju`

```yaml
ingredients:
  - item: rose
    qty: 1
    unit: part
  - item: grape soju
    qty: 2
    unit: part
```

### Procedure-only — `meat/bacon`

```yaml
steps:
  - set pan to 150°C
  - turn at least every few mins
  - should take 10-15 mins to render
```

### Notes-heavy — using a block scalar

```yaml
notes: |
  Rich fatty pork + fried starchy potato = the plate needs brightness and acidity.
  Apple provides fruity sweetness and tart acidity that caramelised sugars can't replicate.
```

## Conventions

- **Block style, not flow `{ }`.** One field per line. (The whole tree round-trips through
  PyYAML with `default_flow_style=False`, so quoting is handled automatically — a `note`
  with a comma or a `step` with a colon will be quoted for you when needed.)
- **Lose nothing.** Every quantity, temperature, time, note, substitution, variant, and
  alternative must survive — as structured fields where possible, otherwise in `note`, step
  text, or `notes`. When in doubt, keep it.
- **Don't invent.** Don't add amounts, steps, or a `basis` the original doesn't imply.
- **Keep the author's voice** — original lowercase wording, slang ("pok", "zhuzh"), and
  idiosyncratic phrasing.
- Choose `basis` only when the original clearly scales off one determining ingredient
  (usually a "for Ng X" / "per Ng X" line). Otherwise omit it.
