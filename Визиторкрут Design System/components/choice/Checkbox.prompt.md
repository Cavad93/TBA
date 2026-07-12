# Checkbox

Checkbox with optional label + description; green when checked. Supports an indeterminate state.

```jsx
<Checkbox label="Только заказы рядом" description="В радиусе 5 км от меня" checked onChange={...} />
<Checkbox label="Выбрать все" indeterminate />
```

- **label**, **description**, **indeterminate**
- Passes through native input props (`checked`, `onChange`, `disabled`).
