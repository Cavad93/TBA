# Button

Primary interactive control. Green `primary` is the brand's commit action ("Взять заказ"); `secondary` for neutral choices, `ghost` for low-emphasis, `danger` for destructive or "не стоит".

```jsx
<Button variant="primary" size="lg" iconLeft={<Icon name="check" />}>
  Взять заказ
</Button>
<Button variant="secondary">Пропустить</Button>
<Button variant="ghost" size="sm">Показать расчёт</Button>
<Button variant="danger" loading>Отменить</Button>
```

- **variant**: `primary` · `secondary` · `ghost` · `danger`
- **size**: `sm` (36) · `md` (44) · `lg` (52) · `xl` (60, one per screen)
- **iconLeft / iconRight**, **fullWidth**, **loading**, **disabled**
- Passes through native `<button>` props (`onClick`, `type`, `aria-*`).
