# Verdict

The product's signature element — the one glance that says whether a trip is worth taking. Green (`go`) / amber (`edge`) / red (`skip`). Requires the Lucide script.

```jsx
<Verdict level="go" reason="₽640/ч чистыми — выше твоей нормы" />
<Verdict level="edge" size="lg" reason="Окупится, только если без пробок" />
<Verdict level="skip" size="sm" />           {/* inline pill on a job card */}
<Verdict level="go" label="Бери!" />          {/* custom label */}
```

- **level**: `go` · `edge` · `skip`
- **size**: `sm` (inline pill for list rows) · `md` · `lg` (block with badge + reason)
- **label** overrides the default text; **reason** adds a one-line justification.
