# Визиторкрут — Design System

> **Навигатор показывает, куда ехать. Наше приложение показывает — стоит ли ехать.**

Design system for **Визиторкрут** (`vizitorkrut.ru`) — a mass, multi-user app for
mobile field workers: **врачи** (doctors on house calls), **таксисты** (taxi drivers),
**курьеры** (couriers) and **мастера на дом** (home-repair pros). Where a navigator
answers *"how do I get there?"*, Визиторкрут answers the question that actually pays the
bills: **"is this trip worth taking at all?"** — turning distance, pay, time, fuel and
traffic into one honest verdict.

The whole system is built around that single job: making a **verdict** glanceable,
trustworthy and fast to act on while the user is in a car, on a bike, or at someone's door.

---

## Sources

This system was built **from a brand brief only** — no codebase, Figma file, design
tokens, logo, fonts, or imagery were provided. Everything here is an original,
first-principles interpretation of the brief:

- **Product:** «Визиторкрут» — massively multi-user app for outbound/field workers.
- **Domain:** `vizitorkrut.ru`
- **Slogan:** «Навигатор показывает, куда ехать. Наше приложение показывает — стоит ли ехать.»
- **Audiences:** врачи · таксисты · курьеры · мастера на дом

Because there is no ground-truth source, **treat every value here as a proposal to
refine, not a recreation to preserve.** See **Caveats** for the specific substitutions
(fonts, icons, logo, imagery) that need real assets from the team.

---

## Design direction — "Wayfinding, with a verdict"

The visual language borrows from **road signage, dispatch boards and odometers** —
things field workers already trust and read at a glance:

- **Green is the brand.** The product's entire reason to exist is finding the trips
  worth taking, so the "go / worth it" green *is* the identity — not a generic accent.
- **The verdict scale is the spine.** Green (стоит) · Amber (на грани) · Red (не стоит).
  These three colors do the heaviest lifting in the whole product.
- **Warm paper + warm ink.** Off-white `--paper` and near-black `--ink` keep long
  reading sessions and outdoor screens comfortable; nothing is pure `#000`/`#fff`.
- **Numbers are loud.** Pay, distance, minutes and ₽/hour are set in a tabular mono
  (JetBrains Mono) so they line up and read like an instrument panel.
- **Blue is the road.** A single blue doubles as links, info, and the map route line —
  a quiet nod to the navigator we compare ourselves to.

---

## Namespace & usage

Consumers link the single root stylesheet and read components off the global namespace
the compiler generates — currently **`DesignSystem_ee81bc`** (auto-derived; re-check with
`check_design_system` if the project is renamed). Components also need React and, for any
icon, the Lucide UMD script.

```html
<link rel="stylesheet" href="styles.css">
<script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>
<script src="_ds_bundle.js"></script>
<script>
  const { Button, Verdict, Metric } = window.DesignSystem_ee81bc;
</script>
```

### Components

17 primitives across 8 groups (each has a `.jsx`, `.d.ts`, `.prompt.md`):

- **buttons/** — `Button`, `IconButton`
- **inputs/** — `Input`, `Textarea`, `Select`
- **choice/** — `Checkbox`, `Radio`, `Switch`
- **feedback/** — `Badge`, `Tag`, `Toast`, `Tooltip`
- **verdict/** — `Verdict`, `Metric` *(product-specific — see "Intentional additions")*
- **surfaces/** — `Card`
- **navigation/** — `Tabs`
- **media/** — `Icon` *(Lucide wrapper — see "Intentional additions")*

#### Intentional additions

Beyond the standard primitive set, two families are core to *this* product:

- **`Verdict` / `Metric`** — the whole app exists to render a worth-it verdict and the
  numbers behind it; these encode the green/amber/red spine and the tabular-mono metric.
- **`Icon`** — a thin wrapper over the chosen Lucide glyph set (no icon system was
  provided), so every icon in the system is loaded and styled one consistent way.

---

## CONTENT FUNDAMENTALS

The voice is a **savvy colleague riding shotgun** — direct, confident, a little cheeky,
never corporate. It exists to cut through and help the worker decide fast.

- **Register — informal «ты».** We talk to the driver like a mate, not a user manual:
  «Не гоняй впустую», «Бери не думая», «Погнали». (Formal «вы» only in legal/support copy.)
- **Numbers lead.** The most important thing on almost every surface is a number — put
  **₽/ч** first, then ₽, км, мин. «₽640/ч чистыми» says more than a paragraph.
- **Plain Russian, zero канцелярит.** Never «осуществите приём заказа» / «данный заказ
  является нерентабельным». Say «Взять заказ» / «Уйдёшь в минус».
- **Short and active.** Imperative verbs, few words, one idea per line.
- **Casing.** Sentence case everywhere. Tiny labels use an UPPERCASE overline
  (`.t-overline`, +0.09em tracking). No Title Case (it's not a thing in Russian anyway).
- **Units & numerals.** `₽ км мин ч ₽/ч`; thousands with a thin space — `2 480`, `₽3 200`;
  decimals with a comma — `8,2 км`. Money is always tabular mono so columns line up.
- **No emoji.** Meaning comes from icons + the verdict color, never 🙈/🚀/✅.
- **Verdict lexicon (fixed).** `Стоит ехать` · `На грани` · `Не стоит`. Reasons are one
  concrete line: «Окупится только без пробок», «Далеко и пробки — уйдёшь в минус».

**Say:** «Стоит ехать. ₽640 в час чистыми.» · «Пока тихо. Хорошие заказы появятся здесь.»
**Don't:** «Уведомляем о поступлении нового заказа.» · «Упс! Что-то пошло не так 🙈»

---

## VISUAL FOUNDATIONS

**Motif — "wayfinding, with a verdict."** Road signage, dispatch boards, odometers. The
product should feel like a trustworthy instrument you read at a glance from the driver's seat.

- **Color.** Warm paper (`--paper #F4F2EB`) and warm ink (`--ink #17160F`) — never pure
  `#000`/`#fff`. **Green is the brand** and also means "go / стоит". The **verdict spine**
  (green `#12A150` / amber `#F2A81E` / red `#D93B3B`) carries most of the meaning; a single
  **blue `#2F6FE0`** is links + info + the map route line. Neutrals are a warm gray ramp.
- **Type.** Display **Unbounded** (800) for big verdict/brand moments only; **Golos Text**
  for all UI and reading; **JetBrains Mono** (tabular) for every number. Big and glanceable —
  display up to 58px on web; body 15–17px; nothing important below 13px.
- **Spacing.** 4px base grid (`--space-*`). Generous section padding on web (72–76px);
  12–16px gaps in the app. Touch targets ≥ 44px (`--control-md`), primary action 60px (`xl`).
- **Backgrounds.** Flat color only — paper, sunken `#EEEBE3`, or ink bands. **No gradients**
  (the one exception: the schematic CSS street-grid inside map placeholders). No textures,
  no hero photography yet (none provided — see Caveats).
- **Corners.** Chunky but not bubbly: inputs 10px, buttons 12px, cards 16px, sheets 20px,
  hero panels 28px, pills 999px. (`--radius-*`.)
- **Borders & cards.** Crisp **1px `--border-default`** first, soft shadow second — cards are
  grounded, not floaty. Default card = outlined (border, no shadow); `raised` adds
  `--shadow-md`. **No colored-left-border cards.** Verdict emphasis comes from a tinted fill +
  full colored border + a solid icon badge, never a stripe.
- **Shadows.** Warm ink-tinted, low and soft (`--shadow-xs…xl`). Verdicts get an optional
  colored glow (`--glow-go`, `--glow-skip`) — used sparingly.
- **Motion.** Snappy and decisive: `--duration-fast 120ms` / `base 200ms`, standard ease
  `cubic-bezier(0.2,0,0,1)`. **No bounce** on functional UI. **Hover** = subtle darken +
  1px lift (cards) or background darken (buttons). **Press** = `scale(0.97)`. All motion
  respects `prefers-reduced-motion`.
- **Transparency / blur.** Reserved: the sticky web nav uses an 8px backdrop blur; the iOS
  frame chrome is glassy. Product surfaces are opaque for sunlight legibility.
- **Imagery vibe (target).** When real photography arrives: candid, warm, daylight, workers
  mid-shift — not glossy stock. Maps are light/minimal with a blue route. All imagery is
  currently a labelled placeholder.

---

## ICONOGRAPHY

- **Set:** [Lucide](https://lucide.dev), loaded from CDN. This is a **from-scratch choice**
  (no icon system was provided) — flag for review; swap to the brand's real set when available.
- **Style:** outline, **stroke 1.75** (`Icon` default), rounded joins. Sizes 16/18/20/24/26.
  Match Lucide's 24-grid; don't mix in filled or other-weight glyphs.
- **Delivery:** the `Icon` component wraps Lucide; pages must load the Lucide UMD script.
  Two tiny inline SVGs exist for control affordances only (checkbox tick, tag/toast ×) so
  those primitives don't hard-depend on Lucide.
- **No emoji, no Unicode dingbats** as icons. The verdict "icon" is semantic:
  `circle-check` (go) · `triangle-alert` (edge) · `circle-x` (skip).
- **Product glyph vocabulary:** `navigation route map-pin corner-up-right` (nav) ·
  `car-front bike package stethoscope wrench` (professions) ·
  `wallet banknote fuel clock gauge timer` (economics) · `circle-check triangle-alert circle-x star bell user-round settings`.

---

## Index / manifest

**Root**
- `styles.css` — root stylesheet, `@import` list only (consumers link this)
- `readme.md` — this guide · `SKILL.md` — Agent-Skill entry point
- `_ds_bundle.js`, `_ds_manifest.json`, `_adherence.oxlintrc.json` — generated, do not edit

**`tokens/`** — `fonts · colors · typography · spacing · elevation · motion · base`
(193 custom properties; `base.css` ships a light reset + branded link/body defaults)

**`guidelines/`** — 17 foundation cards → Design System tab
- Colors (5), Type (4), Spacing (4: scale/radii/elevation/motion), Brand (4: wordmark/slogan/voice/icons)

**`components/`** — 17 primitives, 8 groups, namespace `window.DesignSystem_ee81bc`
- `buttons/` Button · IconButton — `inputs/` Input · Textarea · Select — `choice/` Checkbox · Radio · Switch
- `feedback/` Badge · Tag · Toast · Tooltip — `verdict/` Verdict · Metric — `surfaces/` Card
- `navigation/` Tabs — `media/` Icon

**`ui_kits/`** — interactive product recreations
- `app/` — mobile app: лента заказов → разбор поездки (вердикт) → в пути → смена → профиль
  (`index.html`, `app.jsx`, `app-data.js`, `ios-frame.jsx`)
- `web/` — `vizitorkrut.ru` landing (`index.html`, `web.jsx`)

**Starting points:** `Button`, `Verdict` (components); add screen starting points on request.

---

## Caveats

- **No logo provided.** The brand is rendered as a **typographic wordmark** in Unbounded.
  No symbol/mark has been invented. Please provide the real logo files.
- **Fonts are Google Fonts stand-ins**, chosen for strong Cyrillic and the right voice:
  Unbounded (display), Golos Text (UI/body), JetBrains Mono (data). They load from the
  Google Fonts CDN. If the brand owns licensed faces, send them and we'll self-host.
- **Icons:** Lucide (via CDN) — a from-scratch choice, not a recreation. See ICONOGRAPHY.
- **No imagery provided.** Maps, photos and illustrations are shown as clearly-labelled
  placeholders. Real map tiles/screenshots and field-worker photography are needed.
