import React from 'react';

const CSS = `
.vk-field { display: flex; flex-direction: column; gap: 6px; font-family: var(--font-sans); }
.vk-field__label { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.vk-field__msg { font-size: 12px; line-height: 1.35; color: var(--text-tertiary); }
.vk-field__msg--error { color: var(--danger-text); font-weight: 500; }

.vk-select { position: relative; display: flex; }
.vk-select select {
  appearance: none; -webkit-appearance: none; width: 100%;
  font-family: var(--font-sans); font-size: 15px; color: var(--text-primary);
  background: var(--color-surface); border: 1px solid var(--border-strong);
  border-radius: var(--radius-md); padding: 0 40px 0 14px; cursor: pointer; outline: none;
  transition: border-color var(--duration-fast) var(--ease-standard),
              box-shadow var(--duration-fast) var(--ease-standard);
}
.vk-select--md select { height: var(--control-md); }
.vk-select--lg select { height: var(--control-lg); }
.vk-select select:hover { border-color: var(--neutral-400); }
.vk-select select:focus { border-color: var(--brand); box-shadow: var(--ring-focus); }
.vk-select.is-error select { border-color: var(--danger); }
.vk-select select:disabled { background: var(--color-surface-sunken); opacity: 0.7; cursor: not-allowed; }
.vk-select select.is-placeholder { color: var(--text-tertiary); }
.vk-select__chevron {
  position: absolute; right: 14px; top: 50%; transform: translateY(-50%);
  pointer-events: none; color: var(--text-tertiary); display: inline-flex;
}
`;

if (typeof document !== 'undefined' && !document.getElementById('vk-select-css')) {
  const s = document.createElement('style');
  s.id = 'vk-select-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

let _uid = 0;

export function Select({
  label,
  hint,
  error,
  options = null,
  placeholder,
  value,
  size = 'md',
  id,
  className = '',
  children,
  ...rest
}) {
  const ref = React.useRef(id || `vk-select-${++_uid}`);
  const selId = id || ref.current;
  const isPlaceholder = placeholder != null && (value === '' || value == null);

  return (
    <div className={['vk-field', className].filter(Boolean).join(' ')}>
      {label && <label className="vk-field__label" htmlFor={selId}>{label}</label>}
      <div className={['vk-select', `vk-select--${size}`, error ? 'is-error' : ''].filter(Boolean).join(' ')}>
        <select
          id={selId}
          value={value}
          className={isPlaceholder ? 'is-placeholder' : ''}
          aria-invalid={!!error}
          {...rest}
        >
          {placeholder != null && <option value="" disabled>{placeholder}</option>}
          {options
            ? options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)
            : children}
        </select>
        <span className="vk-select__chevron">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>
        </span>
      </div>
      {(error || hint) && <span className={`vk-field__msg ${error ? 'vk-field__msg--error' : ''}`}>{error || hint}</span>}
    </div>
  );
}
