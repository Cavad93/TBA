import React from 'react';

const CSS = `
.vk-field { display: flex; flex-direction: column; gap: 6px; font-family: var(--font-sans); }
.vk-field__label { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.vk-field__label .req { color: var(--danger); margin-left: 2px; }
.vk-field__msg { font-size: 12px; line-height: 1.35; color: var(--text-tertiary); }
.vk-field__msg--error { color: var(--danger-text); font-weight: 500; }

.vk-input {
  display: flex; align-items: center; gap: 8px; background: var(--color-surface);
  border: 1px solid var(--border-strong); border-radius: var(--radius-md);
  padding: 0 14px; transition: border-color var(--duration-fast) var(--ease-standard),
              box-shadow var(--duration-fast) var(--ease-standard);
}
.vk-input--md { height: var(--control-md); }
.vk-input--lg { height: var(--control-lg); }
.vk-input:hover { border-color: var(--neutral-400); }
.vk-input:focus-within { border-color: var(--brand); box-shadow: var(--ring-focus); }
.vk-input.is-error { border-color: var(--danger); }
.vk-input.is-error:focus-within { box-shadow: 0 0 0 3px rgba(217,59,59,0.28); }
.vk-input.is-disabled { background: var(--color-surface-sunken); border-color: var(--border-default); opacity: 0.7; }

.vk-input input {
  flex: 1; min-width: 0; border: none; outline: none; background: transparent;
  font-family: var(--font-sans); font-size: 15px; color: var(--text-primary); padding: 0;
}
.vk-input input::placeholder { color: var(--text-tertiary); }
.vk-input__icon { display: inline-flex; color: var(--text-tertiary); flex: none; }
.vk-input__affix { font-family: var(--font-mono); font-size: 14px; color: var(--text-secondary); flex: none; }
`;

if (typeof document !== 'undefined' && !document.getElementById('vk-input-css')) {
  const s = document.createElement('style');
  s.id = 'vk-input-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

let _uid = 0;

export function Input({
  label,
  hint,
  error,
  required = false,
  iconLeft = null,
  prefix = null,
  suffix = null,
  size = 'md',
  disabled = false,
  id,
  className = '',
  ...rest
}) {
  const ref = React.useRef(id || `vk-input-${++_uid}`);
  const inputId = id || ref.current;
  const boxCls = [
    'vk-input', `vk-input--${size}`,
    error ? 'is-error' : '', disabled ? 'is-disabled' : '',
  ].filter(Boolean).join(' ');

  return (
    <div className={['vk-field', className].filter(Boolean).join(' ')}>
      {label && (
        <label className="vk-field__label" htmlFor={inputId}>
          {label}{required && <span className="req">*</span>}
        </label>
      )}
      <div className={boxCls}>
        {iconLeft && <span className="vk-input__icon">{iconLeft}</span>}
        {prefix && <span className="vk-input__affix">{prefix}</span>}
        <input id={inputId} disabled={disabled} aria-invalid={!!error} {...rest} />
        {suffix && <span className="vk-input__affix">{suffix}</span>}
      </div>
      {(error || hint) && (
        <span className={`vk-field__msg ${error ? 'vk-field__msg--error' : ''}`}>
          {error || hint}
        </span>
      )}
    </div>
  );
}
