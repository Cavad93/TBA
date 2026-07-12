# IconButton

Icon-only button for toolbars, screen headers and map controls. Always pass an `aria-label`.

```jsx
<IconButton aria-label="Назад" variant="outline"><Icon name="arrow-left" /></IconButton>
<IconButton aria-label="Уведомления" variant="ghost"><Icon name="bell" /></IconButton>
<IconButton aria-label="Мой курс" variant="solid" round><Icon name="navigation" /></IconButton>
```

- **variant**: `solid` (brand) · `soft` (green tint) · `outline` · `ghost`
- **size**: `sm` (36) · `md` (44) · `lg` (52)
- **round**: pill shape (used for the map "recenter" control)
