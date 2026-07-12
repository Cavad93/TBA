---
name: vizitorkrut-design
description: Use this skill to generate well-branded interfaces and assets for Визиторкрут (vizitorkrut.ru) — the "стоит ли ехать?" app for mobile field workers (врачи, таксисты, курьеры, мастера на дом) — for production or throwaway prototypes/mocks. Contains design guidelines, colors, type, fonts, iconography, reusable components and full UI kits (mobile app + marketing site) for prototyping.
user-invocable: true
---

# Визиторкрут — design skill

Read `readme.md` in this skill first — it is the full design guide (brand direction,
CONTENT FUNDAMENTALS, VISUAL FOUNDATIONS, ICONOGRAPHY, and the index of everything here).
Then explore the other files as needed.

## What's here
- `styles.css` + `tokens/` — the single stylesheet to link and all CSS custom properties
  (colors, the verdict spine, type scale, spacing, radii, shadows, motion).
- `guidelines/` — foundation specimen cards (`*.card.html`) you can open to see tokens in use.
- `components/` — React primitives (`<Name>.jsx` + `.d.ts` + `.prompt.md`). Read the
  `.prompt.md` for each component's API and usage. They mount from the compiled bundle at
  `window.DesignSystem_ee81bc` (e.g. `const { Button, Verdict, Metric } = window.DesignSystem_ee81bc`).
- `ui_kits/app/` and `ui_kits/web/` — full, interactive product recreations to copy from.

## How to build with it
- **Visual artifacts** (slides, mocks, throwaway prototypes): copy the assets/tokens you
  need and produce static HTML files the user can open. Link `styles.css`, load React +
  the Lucide UMD script + `_ds_bundle.js`, then compose components (see any `ui_kits/*/index.html`
  for the exact load order and mount pattern).
- **Production code**: read the tokens and component/prompt files to become an expert in the
  brand, then apply the same values in the target codebase.

## Rules of thumb
- Green = the brand and "стоит ехать". Keep the verdict spine (green / amber / red) sacred —
  don't repurpose those colors for decoration.
- Numbers are tabular mono and lead the layout; address the worker informally («ты»); no emoji.
- Warm paper + warm ink, crisp 1px borders, chunky radii, snappy no-bounce motion.
- No logo exists — set the name «Визиторкрут» in Unbounded; never invent a mark.

If invoked with no other guidance, ask what the user wants to build, ask a few focused
questions (surface, audience, fidelity, variations), then act as an expert designer who
outputs HTML artifacts **or** production code depending on the need.
