import React from 'react';

const CSS = `
.vk-metric { display: inline-flex; flex-direction: column; gap: 4px; font-family: var(--font-sans); min-width: 0; }
.vk-metric__label {
  font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--text-tertiary); display: inline-flex; align-items: center; gap: 5px;
}
.vk-metric__value {
  font-family: var(--font-mono); font-feature-settings: var(--numeric-tabular);
  font-weight: 600; line-height: 1.05; letter-spacing: -0.01em; color: var(--text-primary);
  display: inline-flex; align-items: baseline; gap: 3px;
}
.vk-metric--sm .vk-metric__value { font-size: 16px; }
.vk-metric--md .vk-metric__value { font-size: 22px; }
.vk-metric--lg .vk-metric__value { font-size: 34px; }
.vk-metric__unit { font-size: 0.55em; font-weight: 500; color: var(--text-secondary); }
.vk-metric--go   .vk-metric__value { color: var(--verdict-go-text); }
.vk-metric--skip .vk-metric__value { color: var(--verdict-skip-text); }
.vk-metric--brand .vk-metric__value { color: var(--brand); }
.vk-metric__label .vk-icon { color: var(--text-tertiary); }
`;

if (typeof document !== 'undefined' && !document.getElementById('vk-metric-css')) {
  const s = document.createElement('style');
  s.id = 'vk-metric-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function Metric({
  value,
  unit,
  label,
  icon = null,
  tone = 'default',
  size = 'md',
  className = '',
  ...rest
}) {
  const cls = ['vk-metric', `vk-metric--${size}`, `vk-metric--${tone}`, className]
    .filter(Boolean).join(' ');
  return (
    <div className={cls} {...rest}>
      {label != null && (
        <span className="vk-metric__label">{icon}{label}</span>
      )}
      <span className="vk-metric__value">
        {value}
        {unit && <span className="vk-metric__unit">{unit}</span>}
      </span>
    </div>
  );
}
