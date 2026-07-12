# Toast

Transient message with a variant icon. Keep copy short and human. Requires the Lucide script.

```jsx
<Toast variant="success" title="Заказ взят. Погнали!" onClose={dismiss} />
<Toast variant="warning" title="Пробка на маршруте" >
  +12 минут. Пересчитал — всё ещё стоит ехать.
</Toast>
<Toast variant="info" title="Смена началась" action={<Button size="sm" variant="ghost">Открыть</Button>} />
```

- **variant**: `info` · `success` · `warning` · `danger`
- **title**, description (children), **action**, **onClose** (× button)
