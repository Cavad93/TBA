import React from 'react';

const CSS = `
.vk-btn {
  --_h: 44px; --_px: 18px; --_fs: 15px; --_gap: 8px; --_r: var(--radius-lg);
  display: inline-flex; align-items: center; justify-content: center; gap: var(--_gap);
  height: var(--_h); padding: 0 var(--_px); border-radius: var(--_r);
  font-family: var(--font-sans); font-size: var(--_fs); font-weight: 600; line-height: 1;
  letter-spacing: -0.01em; white-space: nowrap; cursor: pointer; user-select: none;
  border: 1px solid transparent; background: none; color: inherit;
  transition: background var(--duration-fast) var(--ease-standard),
              border-color var(--duration-fast) var(--ease-standard),
              transform var(--duration-instant) var(--ease-standard),
              box-shadow var(--duration-fast) var(--ease-standard);
}
.vk-btn:focus-visible { outline: none; box-shadow: var(--ring-focus); }
.vk-btn:active { transform: scale(var(--press-scale)); }
.vk-btn--full { width: 100%; }

.vk-btn--sm { --_h: var(--control-sm); --_px: 14px; --_fs: 13px; --_gap: 6px; --_r: var(--radius-md); }
.vk-btn--md { --_h: var(--control-md); }
.vk-btn--lg { --_h: var(--control-lg); --_px: 22px; --_fs: 16px; }
.vk-btn--xl { --_h: var(--control-xl); --_px: 28px; --_fs: 17px; --_gap: 10px; --_r: var(--radius-xl); }

.vk-btn--primary { background: var(--brand); color: var(--on-brand); box-shadow: var(--shadow-xs); }
.vk-btn--primary:hover { background: var(--brand-hover); }
.vk-btn--primary:active { background: var(--brand-active); }

.vk-btn--secondary { background: var(--color-surface); color: var(--text-primary); border-color: var(--border-strong); }
.vk-btn--secondary:hover { background: var(--color-surface-sunken); border-color: var(--neutral-400); }

.vk-btn--ghost { background: transparent; color: var(--text-primary); }
.vk-btn--ghost:hover { background: var(--neutral-100); }

.vk-btn--danger { background: var(--danger); color: #fff; box-shadow: var(--shadow-xs); }
.vk-btn--danger:hover { background: var(--danger-hover); }

.vk-btn[disabled], .vk-btn[aria-disabled="true"] { opacity: 0.45; cursor: not-allowed; box-shadow: none; }
.vk-btn[disabled]:hover, .vk-btn[aria-disabled="true"]:hover { background: var(--brand); }
.vk-btn--secondary[disabled]:hover { background: var(--color-surface); border-color: var(--border-strong); }
.vk-btn--ghost[disabled]:hover { background: transparent; }
.vk-btn[disabled]:active, .vk-btn[aria-disabled="true"]:active { transform: none; }

.vk-btn__spinner {
  width: 1em; height: 1em; border-radius: 50%; flex: none;
  border: 2px solid currentColor; border-right-color: transparent;
  animation: vk-btn-spin 0.6s linear infinite;
}
@keyframes vk-btn-spin { to { transform: rotate(360deg); } }
.vk-btn__icon { display: inline-flex; flex: none; }
`;

if (typeof document !== 'undefined' && !document.getElementById('vk-button-css')) {
  const s = document.createElement('style');
  s.id = 'vk-button-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  iconLeft = null,
  iconRight = null,
  fullWidth = false,
  loading = false,
  disabled = false,
  type = 'button',
  className = '',
  ...rest
}) {
  const isDisabled = disabled || loading;
  const cls = [
    'vk-btn',
    `vk-btn--${variant}`,
    `vk-btn--${size}`,
    fullWidth ? 'vk-btn--full' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <button type={type} className={cls} disabled={isDisabled} {...rest}>
      {loading && <span className="vk-btn__spinner" aria-hidden="true" />}
      {!loading && iconLeft && <span className="vk-btn__icon">{iconLeft}</span>}
      {children != null && <span>{children}</span>}
      {!loading && iconRight && <span className="vk-btn__icon">{iconRight}</span>}
    </button>
  );
}
