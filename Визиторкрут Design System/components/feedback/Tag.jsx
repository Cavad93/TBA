import React from 'react';

const CSS = `
.vk-tag {
  display: inline-flex; align-items: center; gap: 6px; font-family: var(--font-sans);
  font-weight: 600; font-size: 13px; line-height: 1; border-radius: var(--radius-pill);
  height: 34px; padding: 0 14px; cursor: default; user-select: none;
  background: var(--color-surface); color: var(--text-secondary);
  border: 1px solid var(--border-default);
  transition: background var(--duration-fast) var(--ease-standard),
              border-color var(--duration-fast) var(--ease-standard),
              color var(--duration-fast) var(--ease-standard);
}
.vk-tag--sm { height: 28px; padding: 0 11px; font-size: 12px; gap: 5px; }
.vk-tag--clickable { cursor: pointer; }
.vk-tag--clickable:hover { border-color: var(--neutral-400); background: var(--color-surface-sunken); }
.vk-tag--clickable:focus-visible { outline: none; box-shadow: var(--ring-focus); }
.vk-tag.is-selected {
  background: var(--ink); color: #fff; border-color: var(--ink);
}
.vk-tag.is-selected:hover { background: var(--neutral-800); border-color: var(--neutral-800); }
.vk-tag__icon { display: inline-flex; margin-left: -2px; }
.vk-tag__remove {
  display: inline-flex; align-items: center; justify-content: center; margin-right: -4px;
  width: 18px; height: 18px; border-radius: 50%; border: none; background: transparent;
  color: inherit; cursor: pointer; opacity: 0.6;
}
.vk-tag__remove:hover { opacity: 1; background: rgba(127,120,108,0.2); }
`;

if (typeof document !== 'undefined' && !document.getElementById('vk-tag-css')) {
  const s = document.createElement('style');
  s.id = 'vk-tag-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function Tag({
  children,
  selected = false,
  icon = null,
  onRemove,
  onClick,
  size = 'md',
  className = '',
  ...rest
}) {
  const clickable = !!onClick;
  const cls = [
    'vk-tag', `vk-tag--${size}`,
    clickable ? 'vk-tag--clickable' : '',
    selected ? 'is-selected' : '',
    className,
  ].filter(Boolean).join(' ');

  const Comp = clickable ? 'button' : 'span';
  const compProps = clickable
    ? { type: 'button', onClick, 'aria-pressed': selected }
    : {};

  return (
    <Comp className={cls} {...compProps} {...rest}>
      {icon && <span className="vk-tag__icon">{icon}</span>}
      {children}
      {onRemove && (
        <button
          type="button"
          className="vk-tag__remove"
          aria-label="Убрать"
          onClick={(e) => { e.stopPropagation(); onRemove(e); }}
        >
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
        </button>
      )}
    </Comp>
  );
}
