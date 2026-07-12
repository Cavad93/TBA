import React from 'react';

const CSS = `
.vk-badge {
  display: inline-flex; align-items: center; gap: 5px; font-family: var(--font-sans);
  font-weight: 600; border-radius: var(--radius-pill); white-space: nowrap; line-height: 1;
  border: 1px solid transparent;
}
.vk-badge--sm { height: 20px; padding: 0 8px; font-size: 11px; }
.vk-badge--md { height: 26px; padding: 0 11px; font-size: 13px; }
.vk-badge__dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex: none; }

/* soft (default) */
.vk-badge--soft.is-neutral { background: var(--neutral-100); color: var(--neutral-700); }
.vk-badge--soft.is-success { background: var(--success-bg); color: var(--success-text); }
.vk-badge--soft.is-warning { background: var(--warning-bg); color: var(--warning-text); }
.vk-badge--soft.is-danger  { background: var(--danger-bg);  color: var(--danger-text); }
.vk-badge--soft.is-info    { background: var(--info-bg);    color: var(--info-text); }

/* solid */
.vk-badge--solid { color: #fff; }
.vk-badge--solid.is-neutral { background: var(--neutral-700); }
.vk-badge--solid.is-success { background: var(--success); }
.vk-badge--solid.is-warning { background: var(--warning); color: var(--ink); }
.vk-badge--solid.is-danger  { background: var(--danger); }
.vk-badge--solid.is-info    { background: var(--info); }

/* outline */
.vk-badge--outline { background: transparent; }
.vk-badge--outline.is-neutral { color: var(--neutral-700); border-color: var(--border-strong); }
.vk-badge--outline.is-success { color: var(--success-text); border-color: var(--success-border); }
.vk-badge--outline.is-warning { color: var(--warning-text); border-color: var(--warning-border); }
.vk-badge--outline.is-danger  { color: var(--danger-text);  border-color: var(--danger-border); }
.vk-badge--outline.is-info    { color: var(--info-text);    border-color: var(--info-border); }
`;

if (typeof document !== 'undefined' && !document.getElementById('vk-badge-css')) {
  const s = document.createElement('style');
  s.id = 'vk-badge-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function Badge({
  children,
  variant = 'neutral',
  appearance = 'soft',
  size = 'md',
  dot = false,
  className = '',
  ...rest
}) {
  const cls = [
    'vk-badge', `vk-badge--${appearance}`, `vk-badge--${size}`, `is-${variant}`, className,
  ].filter(Boolean).join(' ');
  return (
    <span className={cls} {...rest}>
      {dot && <span className="vk-badge__dot" />}
      {children}
    </span>
  );
}
