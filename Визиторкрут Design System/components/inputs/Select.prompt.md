# Select

Styled native select — keeps the OS picker on mobile, which is right for a field app. Pass `options` or `<option>` children.

```jsx
<Select label="Транспорт" placeholder="Выбери" options={[
  { value: 'car', label: 'Авто' },
  { value: 'bike', label: 'Велосипед' },
  { value: 'foot', label: 'Пешком' },
]} />
```

- **label**, **hint**, **error**, **placeholder**
- **options**: `{value, label}[]` (or `<option>` children), **size**: `md` · `lg`
- Passes through native `<select>` props (`value`, `onChange`).
