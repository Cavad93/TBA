# Metric

A single dispatch-panel metric — pay, distance, minutes, ₽/hour. The value is tabular mono so rows of metrics align.

```jsx
<Metric label="Оплата" value="2 480" unit="₽" tone="brand" size="lg" />
<Metric label="До клиента" value="8,2" unit="км" />
<Metric label="В пути" value="19" unit="мин" />
<Metric label={<>Чистыми</>} icon={<Icon name="wallet" size={13} />} value="₽640" unit="/ч" tone="go" />
```

- **value** + **unit** (unit renders smaller) · **label** (uppercase caption) · **icon**
- **tone**: `default` · `brand` · `go` · `skip`
- **size**: `sm` · `md` · `lg`
