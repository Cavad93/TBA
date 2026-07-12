# Textarea

Multi-line field for notes to clients, cancellation reasons, feedback. Same label/hint/error contract as Input.

```jsx
<Textarea label="Комментарий клиенту" placeholder="Например: перезвоните за 10 минут" rows={3} />
<Textarea label="Причина отмены" error="Опиши, что случилось" required />
```

- **label**, **hint**, **error**, **required**
- Passes through native `<textarea>` props (`rows`, `value`, `onChange`).
