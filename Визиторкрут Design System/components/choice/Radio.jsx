import React from 'react';

const CSS = `
.vk-radio { display: inline-flex; align-items: flex-start; gap: 10px; cursor: pointer;
  font-family: var(--font-sans); user-select: none; }
.vk-radio.is-disabled { cursor: not-allowed; opacity: 0.5; }
.vk-radio input { position: absolute; opacity: 0; width: 0; height: 0; }
.vk-radio__dot {
  flex: none; width: 22px; height: 22px; border-radius: 50%; margin-top: 1px;
  border: 1.5px solid var(--border-strong); background: var(--color-surface);
  display: inline-flex; align-items: center; justify-content: center;
  transition: border-color var(--duration-fast) var(--ease-standard); position: relative;
}
.vk-radio__dot::after {
  content: ""; width: 10px; height: 10px; border-radius: 50%; background: var(--brand);
  opacity: 0; transform: scale(0.5); transition: opacity var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out);
}
.vk-radio:hover .vk-radio__dot { border-color: var(--neutral-400); }
.vk-radio input:checked + .vk-radio__dot { border-color: var(--brand); }
.vk-radio input:checked + .vk-radio__dot::after { opacity: 1; transform: scale(1); }
.vk-radio input:focus-visible + .vk-radio__dot { box-shadow: var(--ring-focus); }
.vk-radio__text { display: flex; flex-direction: column; gap: 2px; }
.vk-radio__label { font-size: 15px; font-weight: 500; color: var(--text-primary); line-height: 1.35; }
.vk-radio__desc { font-size: 13px; color: var(--text-secondary); line-height: 1.4; }
`;

if (typeof document !== 'undefined' && !document.getElementById('vk-radio-css')) {
  const s = document.createElement('style');
  s.id = 'vk-radio-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function Radio({
  label,
  description,
  disabled = false,
  className = '',
  ...rest
}) {
  return (
    <label className={['vk-radio', disabled ? 'is-disabled' : '', className].filter(Boolean).join(' ')}>
      <input type="radio" disabled={disabled} {...rest} />
      <span className="vk-radio__dot" />
      {(label || description) && (
        <span className="vk-radio__text">
          {label && <span className="vk-radio__label">{label}</span>}
          {description && <span className="vk-radio__desc">{description}</span>}
        </span>
      )}
    </label>
  );
}
