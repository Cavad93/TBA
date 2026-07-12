# Tooltip

Lightweight CSS hover/focus tooltip. Wrap a focusable trigger so it also shows on keyboard focus.

```jsx
<Tooltip content="Расчёт: оплата − бензин − износ − время" placement="top">
  <IconButton aria-label="Как считаем" variant="ghost"><Icon name="help-circle" /></IconButton>
</Tooltip>
```

- **content** (keep to one short line), **placement**: `top` · `bottom` · `left` · `right`
- Appears on hover and focus-within; no JS state needed.
