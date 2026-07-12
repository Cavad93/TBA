# Switch

On/off toggle for instant settings (online status, "Считать бензин", push). Green when on.

```jsx
<Switch label="Я на смене" defaultChecked />
<Switch label="Считать бензин в расчёте" labelPosition="left" spread defaultChecked />
<Switch size="sm" aria-label="Уведомления" />
```

- **label**, **size**: `sm` · `md`
- **labelPosition**: `right` (default) · `left`; **spread** for full-width settings rows
- Passes through native input props (`checked`, `onChange`, `disabled`).
