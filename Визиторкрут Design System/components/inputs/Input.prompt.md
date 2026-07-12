# Input

Labelled text field with hint/error states and optional icon, prefix or suffix. Use affixes for units.

```jsx
<Input label="Телефон" iconLeft={<Icon name="phone" size={16} />} placeholder="+7 900 000-00-00" />
<Input label="Цена бензина" suffix="₽/л" defaultValue="58" />
<Input label="E-mail" error="Проверь адрес" defaultValue="ivan@" />
```

- **label**, **hint**, **error** (red border + message), **required**
- **iconLeft**, **prefix**, **suffix**, **size**: `md` · `lg`
- Passes through native `<input>` props (`value`, `onChange`, `type`, `placeholder`).
