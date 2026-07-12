import React from 'react';

const CSS = `
.vk-tabs { font-family: var(--font-sans); display: inline-flex; }
.vk-tabs--full { display: flex; width: 100%; }

/* line */
.vk-tabs--line { gap: 4px; border-bottom: 1px solid var(--border-default); }
.vk-tabs--line .vk-tab {
  appearance: none; border: none; background: none; cursor: pointer;
  padding: 10px 14px; font-size: 15px; font-weight: 600; color: var(--text-tertiary);
  position: relative; display: inline-flex; align-items: center; gap: 7px;
  transition: color var(--duration-fast) var(--ease-standard); margin-bottom: -1px;
}
.vk-tabs--line.vk-tabs--full .vk-tab { flex: 1; justify-content: center; }
.vk-tabs--line .vk-tab:hover { color: var(--text-secondary); }
.vk-tabs--line .vk-tab.is-active { color: var(--text-primary); }
.vk-tabs--line .vk-tab.is-active::after {
  content: ""; position: absolute; left: 8px; right: 8px; bottom: 0; height: 2.5px;
  background: var(--brand); border-radius: 2px;
}
.vk-tabs--line .vk-tab:focus-visible { outline: none; box-shadow: var(--ring-focus); border-radius: var(--radius-sm); }

/* segmented */
.vk-tabs--segmented {
  gap: 2px; background: var(--color-bg-sunken); border-radius: var(--radius-md);
  padding: 3px; border: 1px solid var(--border-subtle);
}
.vk-tabs--segmented .vk-tab {
  appearance: none; border: none; background: transparent; cursor: pointer;
  padding: 7px 14px; font-size: 14px; font-weight: 600; color: var(--text-secondary);
  border-radius: calc(var(--radius-md) - 3px); display: inline-flex; align-items: center;
  gap: 6px; justify-content: center; white-space: nowrap;
  transition: background var(--duration-fast) var(--ease-standard), color var(--duration-fast) var(--ease-standard);
}
.vk-tabs--segmented.vk-tabs--full .vk-tab { flex: 1; }
.vk-tabs--segmented .vk-tab:hover { color: var(--text-primary); }
.vk-tabs--segmented .vk-tab.is-active { background: var(--color-surface); color: var(--text-primary); box-shadow: var(--shadow-xs); }
.vk-tabs--segmented .vk-tab:focus-visible { outline: none; box-shadow: var(--ring-focus); }
.vk-tab__count { font-family: var(--font-mono); font-size: 12px; opacity: 0.7; }
`;

if (typeof document !== 'undefined' && !document.getElementById('vk-tabs-css')) {
  const s = document.createElement('style');
  s.id = 'vk-tabs-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function Tabs({
  items = [],
  value,
  onChange,
  variant = 'line',
  fullWidth = false,
  className = '',
  ...rest
}) {
  const cls = [
    'vk-tabs', `vk-tabs--${variant}`, fullWidth ? 'vk-tabs--full' : '', className,
  ].filter(Boolean).join(' ');

  return (
    <div className={cls} role="tablist" {...rest}>
      {items.map((it) => {
        const active = it.value === value;
        return (
          <button
            key={it.value}
            type="button"
            role="tab"
            aria-selected={active}
            className={['vk-tab', active ? 'is-active' : ''].filter(Boolean).join(' ')}
            onClick={() => onChange && onChange(it.value)}
          >
            {it.icon}
            {it.label}
            {it.count != null && <span className="vk-tab__count">{it.count}</span>}
          </button>
        );
      })}
    </div>
  );
}
