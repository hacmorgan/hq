---
name: add-recipe
description: Add a new recipe to ~/hq/etc/kopi/recipes. Activate when the user asks to add, write, or create a recipe.
---

# Adding a Recipe

## Location

`~/hq/etc/kopi/recipes/<section>/<recipe-name>`

- Filename: kebab-case, no extension
- Available sections: `alcoholic`, `breakfast`, `carbs`, `cordial`, `desserts`, `espresso`, `matcha`, `meat`, `milk-based`, `pourover`, `rice`, `saline`, `sauces`, `snacks`, `soup`, `spices`, `tea`, `veg`

## Style

Read 2–3 existing recipes from the target section before writing — style varies across sections.

Conventions observed across the collection:

- No title line — the filename is the title
- Terse, imperative steps as `-` bullet points
- Lowercase preferred, but not rigidly enforced
- Temperatures in °C — e.g. `pan to 180°C`, `150°C for a few mins`
- Measurements: grams, tbsp, tsp, ml, cups — e.g. `1.5tbsp`, `0.5g`, `1/4 cup`, `30g`
- Section headers in `[ brackets ]` for variants, phases, or sub-components — e.g. `[ dry dredge ]`, `[ Reverse-sear ]`, `[ optional ]`
- Inline optional steps as `(Optional)` rather than a separate section, unless there are many
- Notes, tips, and recommendations as plain prose — no header, just a line or two at the end or top
- No "enjoy", no emojis, no trailing summary
- If the recipe came from a URL, include it as a plain line at the top: `source: <url>`

## Steps

1. Determine the correct section
2. Read 2–3 existing recipes in or near that section for local style
3. Choose a descriptive kebab-case filename
4. Write the recipe file
