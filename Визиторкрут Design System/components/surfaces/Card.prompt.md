# Card

Base surface. `outlined` is the house style (crisp 1px border, no shadow); `raised` floats it; `flat` is a sunken tint. `interactive` adds hover-lift + keyboard focus for tappable rows.

```jsx
<Card>Обычная карточка</Card>
<Card variant="raised" padding="lg">Приподнятая</Card>
<Card interactive onClick={openJob}>
  {/* job row — Verdict + Metrics inside */}
</Card>
```

- **variant**: `outlined` · `raised` · `flat`
- **padding**: `none` · `sm` · `md` · `lg`
- **interactive**: hover lift, pointer, `role="button"` + `tabIndex`
