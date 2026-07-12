import React from 'react';
import { Icon } from '../media/Icon';

const CSS = `
.vk-verdict { font-family: var(--font-sans); display: inline-flex; }

/* --- pill (size sm) --- */
.vk-verdict--pill {
  align-items: center; gap: 6px; border-radius: var(--radius-pill);
  height: 28px; padding: 0 12px; font-size: 13px; font-weight: 700;
  letter-spacing: -0.01em; color: #fff;
}
.vk-verdict--pill.is-go   { background: var(--verdict-go); }
.vk-verdict--pill.is-edge { background: var(--verdict-edge); color: var(--ink); }
.vk-verdict--pill.is-skip { background: var(--verdict-skip); }

/* --- block (size md / lg) --- */
.vk-verdict--block {
  align-items: center; gap: 12px; border-radius: var(--radius-xl);
  border: 1.5px solid; padding: 12px 16px; width: 100%;
}
.vk-verdict--block.is-go   { background: var(--verdict-go-bg);   border-color: var(--verdict-go-border); }
.vk-verdict--block.is-edge { background: var(--verdict-edge-bg); border-color: var(--verdict-edge-border); }
.vk-verdict--block.is-skip { background: var(--verdict-skip-bg); border-color: var(--verdict-skip-border); }
.vk-verdict--lg { padding: 16px 18px; gap: 14px; }

.vk-verdict__badge {
  flex: none; display: inline-flex; align-items: center; justify-content: center;
  width: 40px; height: 40px; border-radius: var(--radius-pill); color: #fff;
}
.vk-verdict--lg .vk-verdict__badge { width: 48px; height: 48px; }
.is-go   .vk-verdict__badge { background: var(--verdict-go); box-shadow: var(--glow-go); }
.is-edge .vk-verdict__badge { background: var(--verdict-edge); color: var(--ink); }
.is-skip .vk-verdict__badge { background: var(--verdict-skip); box-shadow: var(--glow-skip); }

.vk-verdict__body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.vk-verdict__label { font-weight: 700; font-size: 16px; letter-spacing: -0.01em; }
.vk-verdict--lg .vk-verdict__label { font-size: 18px; }
.is-go   .vk-verdict__label { color: var(--verdict-go-text); }
.is-edge .vk-verdict__label { color: var(--verdict-edge-text); }
.is-skip .vk-verdict__label { color: var(--verdict-skip-text); }
.vk-verdict__reason { font-size: 13px; line-height: 1.4; color: var(--text-secondary); }
`;

if (typeof document !== 'undefined' && !document.getElementById('vk-verdict-css')) {
  const s = document.createElement('style');
  s.id = 'vk-verdict-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

const LEVELS = {
  go:   { label: 'Стоит ехать', icon: 'circle-check' },
  edge: { label: 'На грани',    icon: 'triangle-alert' },
  skip: { label: 'Не стоит',    icon: 'circle-x' },
};

export function Verdict({
  level = 'go',
  size = 'md',
  label,
  reason,
  className = '',
  ...rest
}) {
  const cfg = LEVELS[level] || LEVELS.go;
  const text = label != null ? label : cfg.label;

  if (size === 'sm') {
    const cls = ['vk-verdict', 'vk-verdict--pill', `is-${level}`, className].filter(Boolean).join(' ');
    return (
      <span className={cls} {...rest}>
        <Icon name={cfg.icon} size={15} strokeWidth={2.25} />
        {text}
      </span>
    );
  }

  const cls = [
    'vk-verdict', 'vk-verdict--block', `is-${level}`,
    size === 'lg' ? 'vk-verdict--lg' : '', className,
  ].filter(Boolean).join(' ');

  return (
    <div className={cls} {...rest}>
      <span className="vk-verdict__badge">
        <Icon name={cfg.icon} size={size === 'lg' ? 26 : 22} strokeWidth={2.25} />
      </span>
      <span className="vk-verdict__body">
        <span className="vk-verdict__label">{text}</span>
        {reason && <span className="vk-verdict__reason">{reason}</span>}
      </span>
    </div>
  );
}
