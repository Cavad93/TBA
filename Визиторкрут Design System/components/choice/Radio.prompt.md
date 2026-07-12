# Radio

Single-choice control. Give options the same `name` to group them.

```jsx
<Radio name="shift" value="full" label="Полный день" defaultChecked />
<Radio name="shift" value="short" label="Пара часов" description="Заканчиваю к обеду" />
```

- **label**, **description**
- Passes through native input props (`name`, `value`, `checked`, `onChange`).
