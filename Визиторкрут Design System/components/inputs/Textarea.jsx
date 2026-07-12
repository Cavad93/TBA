import React from 'react';

const CSS = `
.vk-field { display: flex; flex-direction: column; gap: 6px; font-family: var(--font-sans); }
.vk-field__label { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.vk-field__msg { font-size: 12px; line-height: 1.35; color: var(--text-tertiary); }
.vk-field__msg--error { color: var(--danger-text); font-weight: 500; }

.vk-textarea {
  font-family: var(--font-sans); font-size: 15px; line-height: 1.5; color: var(--text-primary);
  background: var(--color-surface); border: 1px solid var(--border-strong);
  border-radius: var(--radius-md); padding: 11px 14px; resize: vertical; min-height: 88px;
  transition: border-color var(--duration-fast) var(--ease-standard),
              box-shadow var(--duration-fast) var(--ease-standard); outline: none;
}
.vk-textarea::placeholder { color: var(--text-tertiary); }
.vk-textarea:hover { border-color: var(--neutral-400); }
.vk-textarea:focus { border-color: var(--brand); box-shadow: var(--ring-focus); }
.vk-textarea.is-error { border-color: var(--danger); }
.vk-textarea:disabled { background: var(--color-surface-sunken); opacity: 0.7; }
`;

if (typeof document !== 'undefined' && !document.getElementById('vk-textarea-css')) {
  const s = document.createElement('style');
  s.id = 'vk-textarea-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

let _uid = 0;

export function Textarea({
  label,
  hint,
  error,
  required = false,
  id,
  className = '',
  ...rest
}) {
  const ref = React.useRef(id || `vk-textarea-${++_uid}`);
  const areaId = id || ref.current;
  return (
    <div className={['vk-field', className].filter(Boolean).join(' ')}>
      {label && (
        <label className="vk-field__label" htmlFor={areaId}>{label}{required && <span style={{ color: 'var(--danger)' }}> *</span>}</label>
      )}
      <textarea
        id={areaId}
        className={['vk-textarea', error ? 'is-error' : ''].filter(Boolean).join(' ')}
        aria-invalid={!!error}
        {...rest}
      />
      {(error || hint) && (
        <span className={`vk-field__msg ${error ? 'vk-field__msg--error' : ''}`}>{error || hint}</span>
      )}
    </div>
  );
}
