import React from 'react';

const CSS = `
.vk-iconbtn {
  --_s: 44px; --_r: var(--radius-md);
  display: inline-flex; align-items: center; justify-content: center;
  width: var(--_s); height: var(--_s); border-radius: var(--_r);
  border: 1px solid transparent; background: none; cursor: pointer; padding: 0;
  color: var(--text-primary); flex: none;
  transition: background var(--duration-fast) var(--ease-standard),
              border-color var(--duration-fast) var(--ease-standard),
              transform var(--duration-instant) var(--ease-standard),
              box-shadow var(--duration-fast) var(--ease-standard);
}
.vk-iconbtn:focus-visible { outline: none; box-shadow: var(--ring-focus); }
.vk-iconbtn:active { transform: scale(var(--press-scale)); }
.vk-iconbtn svg { width: 55%; height: 55%; }

.vk-iconbtn--sm { --_s: var(--control-sm); }
.vk-iconbtn--md { --_s: var(--control-md); }
.vk-iconbtn--lg { --_s: var(--control-lg); }
.vk-iconbtn--round { --_r: var(--radius-pill); }

.vk-iconbtn--solid { background: var(--brand); color: var(--on-brand); }
.vk-iconbtn--solid:hover { background: var(--brand-hover); }

.vk-iconbtn--soft { background: var(--brand-subtle); color: var(--brand-active); }
.vk-iconbtn--soft:hover { background: var(--green-100); }

.vk-iconbtn--outline { background: var(--color-surface); border-color: var(--border-strong); }
.vk-iconbtn--outline:hover { background: var(--color-surface-sunken); border-color: var(--neutral-400); }

.vk-iconbtn--ghost { background: transparent; }
.vk-iconbtn--ghost:hover { background: var(--neutral-100); }

.vk-iconbtn[disabled] { opacity: 0.4; cursor: not-allowed; }
.vk-iconbtn[disabled]:hover { background: transparent; }
.vk-iconbtn--solid[disabled]:hover { background: var(--brand); }
.vk-iconbtn[disabled]:active { transform: none; }
`;

if (typeof document !== 'undefined' && !document.getElementById('vk-iconbtn-css')) {
  const s = document.createElement('style');
  s.id = 'vk-iconbtn-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function IconButton({
  children,
  variant = 'ghost',
  size = 'md',
  round = false,
  disabled = false,
  className = '',
  ...rest
}) {
  const cls = [
    'vk-iconbtn',
    `vk-iconbtn--${variant}`,
    `vk-iconbtn--${size}`,
    round ? 'vk-iconbtn--round' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <button type="button" className={cls} disabled={disabled} {...rest}>
      {children}
    </button>
  );
}
