---
name: add-recipe
description: Add a new recipe to ~/hq/etc/kopi/recipes. Activate when the user asks to add, write, or create a recipe.
---

# Adding a Recipe

Recipes are **YAML**. The authoritative spec is `~/hq/etc/kopi/RECIPE_FORMAT.md` — read it
before writing. This skill covers where the file goes and how to approach the conversion.

## Location

`~/hq/etc/kopi/recipes/<section>/<recipe-name>`

- Filename: kebab-case, **no extension** — the `kopi` CLI and dashboard list recipes by
  path, so adding `.yaml` would change the displayed name. YAML is still valid without one.
- Available sections: `alcoholic`, `breakfast`, `carbs`, `cordial`, `desserts`, `espresso`,
  `matcha`, `meat`, `milk-based`, `pourover`, `rice`, `salad`, `sauces`, `snacks`, `soup`,
  `spices`, `tea`, `veg`

## Shape

Top-level keys, all optional: `name`, `source`, `uses`, `yield`, `notes`, `ingredients`,
`steps`, `components`. See `RECIPE_FORMAT.md` for the full table, the ingredient/step entry
fields, and worked examples.

The short version:

```yaml
ingredients:
  - item: mirin          # required; bare string is fine when there's no amount
    mass: 50             # grams
  - item: chicken
    mass: 500
    basis: true          # at most one in the recipe; drives dashboard scaling
  - item: brown onion
    note: shaved, to taste
steps:
  - boil mirin and sake for 20 secs to evaporate alcohol
  - marinate fish in marinade
```

Use `components` (each with a `name` and its own `ingredients`/`steps`/`notes`) when the
recipe has distinct parts — rub + sauce + glaze, or alternative versions of the same thing.

## Style

Read 2–3 existing recipes from the target section before writing — style varies across
sections.

- No title line — the filename is the title. Only set `name` when it reads better than the
  filename.
- Terse, imperative steps; lowercase preferred but not rigidly enforced
- Temperatures in °C, kept inline in the step text — e.g. `bake at 180°C for 40 mins`
- Block style, one field per line — **not** flow `{ }` style
- **Lose nothing.** Every quantity, temperature, time, note, substitution, and variant must
  survive — as structured fields where possible, otherwise in `note`, step text, or `notes`.
- **Don't invent.** No amounts, steps, or a `basis` the original doesn't imply.
- **Keep the author's voice** — original wording, slang, idiosyncratic phrasing.
- Prose that doesn't fit ingredients or steps goes in `notes` as a block scalar (`|`)
- No "enjoy", no emojis, no trailing summary
- If the recipe came from a URL, set `source: <url>`
- List genuine sub-recipe dependencies under `uses` (by filename or path) — this draws the
  dashboard graph's edges, so keep them intentional

## Steps

1. Determine the correct section
2. Read `~/hq/etc/kopi/RECIPE_FORMAT.md`
3. Read 2–3 existing recipes in or near that section for local style
4. Choose a descriptive kebab-case filename
5. Write the recipe file
6. Check it parses: `python3 -c "import yaml; yaml.safe_load(open('<path>'))"`
