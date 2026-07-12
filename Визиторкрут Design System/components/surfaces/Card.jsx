import React from 'react';

const CSS = `
.vk-card {
  background: var(--color-surface); border-radius: var(--radius-xl);
  border: 1px solid transparent; color: var(--text-primary);
  transition: transform var(--duration-fast) var(--ease-standard),
              box-shadow var(--duration-fast) var(--ease-standard),
              border-color var(--duration-fast) var(--ease-standard);
}
.vk-card--outlined { border-color: var(--border-default); }
.vk-card--raised { border-color: var(--border-subtle); box-shadow: var(--shadow-md); }
.vk-card--flat { background: var(--color-surface-sunken); }

.vk-card--pad-sm { padding: var(--space-3); }
.vk-card--pad-md { padding: var(--space-4); }
.vk-card--pad-lg { padding: var(--space-6); }

.vk-card--interactive { cursor: pointer; }
.vk-card--interactive:hover { transform: var(--lift); box-shadow: var(--shadow-lg); border-color: var(--border-strong); }
.vk-card--interactive:active { transform: scale(0.995); box-shadow: var(--shadow-sm); }
.vk-card--interactive:focus-visible { outline: none; box-shadow: var(--ring-focus); }
`;

if (typeof document !== 'undefined' && !document.getElementById('vk-card-css')) {
  const s = document.createElement('style');
  s.id = 'vk-card-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function Card({
  children,
  variant = 'outlined',
  padding = 'md',
  interactive = false,
  className = '',
  ...rest
}) {
  const cls = [
    'vk-card',
    `vk-card--${variant}`,
    padding !== 'none' ? `vk-card--pad-${padding}` : '',
    interactive ? 'vk-card--interactive' : '',
    className,
  ].filter(Boolean).join(' ');

  const interactiveProps = interactive ? { tabIndex: 0, role: 'button' } : {};

  return (
    <div className={cls} {...interactiveProps} {...rest}>
      {children}
    </div>
  );
}
