# Tag

Pill chip for filters and categories. Add `onClick` to make it a toggle; add `onRemove` for a dismissable chip.

```jsx
<Tag icon={<Icon name="car-front" size={14} />} selected onClick={toggle}>Такси</Tag>
<Tag onClick={toggle}>Курьер</Tag>
<Tag onRemove={clear}>8–15 км</Tag>
```

- **selected** → ink-filled active state (filter chips)
- **icon**, **onRemove** (× affordance), **size**: `sm` · `md`
- With `onClick` it renders as a `<button aria-pressed>`.
