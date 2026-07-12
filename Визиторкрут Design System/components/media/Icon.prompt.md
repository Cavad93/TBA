# Icon

Thin wrapper over [Lucide](https://lucide.dev). Requires the Lucide UMD script on the page:
`<script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>`.

```jsx
<Icon name="navigation" />
<Icon name="wallet" size={24} color="var(--brand)" />
<Icon name="fuel" strokeWidth={2} />
```

- **name**: any Lucide glyph name (kebab-case)
- **size** (px, default 20) · **strokeWidth** (default 1.75) · **color**
- Decorative by default. Product-relevant glyphs: `navigation`, `route`, `map-pin`, `car-front`, `bike`, `package`, `stethoscope`, `wrench`, `wallet`, `banknote`, `fuel`, `clock`, `gauge`, `circle-check`, `circle-x`, `star`.
