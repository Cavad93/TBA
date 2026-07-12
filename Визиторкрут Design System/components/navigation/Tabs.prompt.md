# Tabs

Controlled tab switcher. `line` for section nav; `segmented` for compact in-card toggles.

```jsx
const [tab, setTab] = React.useState('feed');
<Tabs value={tab} onChange={setTab} items={[
  { value: 'feed', label: 'Лента', count: 12 },
  { value: 'active', label: 'Активные' },
  { value: 'history', label: 'История' },
]} />

<Tabs variant="segmented" fullWidth value={period} onChange={setPeriod} items={[
  { value: 'day', label: 'День' }, { value: 'week', label: 'Неделя' },
]} />
```

- **items**: `{ value, label, icon?, count? }[]`
- **value** + **onChange** (controlled), **variant**: `line` · `segmented`, **fullWidth**
