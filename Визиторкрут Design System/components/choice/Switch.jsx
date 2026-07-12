import React from 'react';

const CSS = `
.vk-switch { display: inline-flex; align-items: center; gap: 10px; cursor: pointer;
  font-family: var(--font-sans); user-select: none; }
.vk-switch.is-disabled { cursor: not-allowed; opacity: 0.5; }
.vk-switch--left { flex-direction: row-reverse; }
.vk-switch--between { display: flex; justify-content: space-between; width: 100%; }
.vk-switch input { position: absolute; opacity: 0; width: 0; height: 0; }
.vk-switch__track {
  --_w: 46px; --_h: 28px; --_thumb: 22px;
  flex: none; width: var(--_w); height: var(--_h); border-radius: var(--radius-pill);
  background: var(--neutral-300); position: relative;
  transition: background var(--duration-base) var(--ease-standard);
}
.vk-switch--sm .vk-switch__track { --_w: 38px; --_h: 23px; --_thumb: 17px; }
.vk-switch__thumb {
  position: absolute; top: 50%; left: 3px; transform: translateY(-50%);
  width: var(--_thumb); height: var(--_thumb); border-radius: 50%; background: #fff;
  box-shadow: var(--shadow-sm);
  transition: left var(--duration-base) var(--ease-out);
}
.vk-switch input:checked + .vk-switch__track { background: var(--brand); }
.vk-switch input:checked + .vk-switch__track .vk-switch__thumb { left: calc(100% - var(--_thumb) - 3px); }
.vk-switch input:focus-visible + .vk-switch__track { box-shadow: var(--ring-focus); }
.vk-switch__label { font-size: 15px; font-weight: 500; color: var(--text-primary); }
`;

if (typeof document !== 'undefined' && !document.getElementById('vk-switch-css')) {
  const s = document.createElement('style');
  s.id = 'vk-switch-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function Switch({
  label,
  size = 'md',
  labelPosition = 'right',
  spread = false,
  disabled = false,
  className = '',
  ...rest
}) {
  const cls = [
    'vk-switch', `vk-switch--${size}`,
    labelPosition === 'left' ? 'vk-switch--left' : '',
    spread ? 'vk-switch--between' : '',
    disabled ? 'is-disabled' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <label className={cls}>
      <input type="checkbox" role="switch" disabled={disabled} {...rest} />
      <span className="vk-switch__track"><span className="vk-switch__thumb" /></span>
      {label && <span className="vk-switch__label">{label}</span>}
    </label>
  );
}
