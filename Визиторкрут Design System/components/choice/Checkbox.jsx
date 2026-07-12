import React from 'react';

const CSS = `
.vk-check { display: inline-flex; align-items: flex-start; gap: 10px; cursor: pointer;
  font-family: var(--font-sans); user-select: none; }
.vk-check.is-disabled { cursor: not-allowed; opacity: 0.5; }
.vk-check input { position: absolute; opacity: 0; width: 0; height: 0; }
.vk-check__box {
  flex: none; width: 22px; height: 22px; border-radius: var(--radius-sm); margin-top: 1px;
  border: 1.5px solid var(--border-strong); background: var(--color-surface);
  display: inline-flex; align-items: center; justify-content: center; color: #fff;
  transition: background var(--duration-fast) var(--ease-standard),
              border-color var(--duration-fast) var(--ease-standard);
}
.vk-check__box svg { opacity: 0; transform: scale(0.6); transition: opacity var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out); }
.vk-check:hover .vk-check__box { border-color: var(--neutral-400); }
.vk-check input:checked + .vk-check__box,
.vk-check input:indeterminate + .vk-check__box { background: var(--brand); border-color: var(--brand); }
.vk-check input:checked + .vk-check__box svg,
.vk-check input:indeterminate + .vk-check__box svg { opacity: 1; transform: scale(1); }
.vk-check input:focus-visible + .vk-check__box { box-shadow: var(--ring-focus); }
.vk-check__text { display: flex; flex-direction: column; gap: 2px; }
.vk-check__label { font-size: 15px; font-weight: 500; color: var(--text-primary); line-height: 1.35; }
.vk-check__desc { font-size: 13px; color: var(--text-secondary); line-height: 1.4; }
`;

if (typeof document !== 'undefined' && !document.getElementById('vk-check-css')) {
  const s = document.createElement('style');
  s.id = 'vk-check-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function Checkbox({
  label,
  description,
  checked,
  indeterminate = false,
  disabled = false,
  className = '',
  ...rest
}) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminate;
  }, [indeterminate]);

  return (
    <label className={['vk-check', disabled ? 'is-disabled' : '', className].filter(Boolean).join(' ')}>
      <input ref={ref} type="checkbox" checked={checked} disabled={disabled} {...rest} />
      <span className="vk-check__box">
        {indeterminate
          ? <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M6 12h12"/></svg>
          : <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7"/></svg>}
      </span>
      {(label || description) && (
        <span className="vk-check__text">
          {label && <span className="vk-check__label">{label}</span>}
          {description && <span className="vk-check__desc">{description}</span>}
        </span>
      )}
    </label>
  );
}
