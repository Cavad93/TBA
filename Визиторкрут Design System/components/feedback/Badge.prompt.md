# Badge

Small status label — order state, counts, "онлайн". For the worth-it verdict use **Verdict**, not Badge.

```jsx
<Badge variant="success" dot>Онлайн</Badge>
<Badge variant="info" appearance="solid">Новый</Badge>
<Badge variant="neutral" appearance="outline" size="sm">×3 в очереди</Badge>
```

- **variant**: `neutral` · `success` · `warning` · `danger` · `info`
- **appearance**: `soft` (default) · `solid` · `outline`
- **size**: `sm` · `md` · **dot** for a leading status dot
