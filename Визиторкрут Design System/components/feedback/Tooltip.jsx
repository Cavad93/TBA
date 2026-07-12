import React from 'react';

const CSS = `
.vk-tooltip { position: relative; display: inline-flex; }
.vk-tooltip__bubble {
  position: absolute; z-index: 50; pointer-events: none;
  background: var(--ink); color: #fff; font-family: var(--font-sans);
  font-size: 12px; font-weight: 500; line-height: 1.35; letter-spacing: 0;
  padding: 6px 9px; border-radius: var(--radius-sm); max-width: 220px; width: max-content;
  box-shadow: var(--shadow-md); opacity: 0; transform: translateY(2px) scale(0.98);
  transition: opacity var(--duration-fast) var(--ease-standard),
              transform var(--duration-fast) var(--ease-standard);
}
.vk-tooltip:hover .vk-tooltip__bubble,
.vk-tooltip:focus-within .vk-tooltip__bubble { opacity: 1; transform: translateY(0) scale(1); }

.vk-tooltip__bubble--top    { bottom: 100%; left: 50%; margin-bottom: 8px; translate: -50% 0; }
.vk-tooltip__bubble--bottom { top: 100%; left: 50%; margin-top: 8px; translate: -50% 0; }
.vk-tooltip__bubble--left   { right: 100%; top: 50%; margin-right: 8px; translate: 0 -50%; }
.vk-tooltip__bubble--right  { left: 100%; top: 50%; margin-left: 8px; translate: 0 -50%; }

.vk-tooltip__arrow { position: absolute; width: 8px; height: 8px; background: var(--ink); transform: rotate(45deg); }
.vk-tooltip__bubble--top .vk-tooltip__arrow    { bottom: -3px; left: 50%; margin-left: -4px; }
.vk-tooltip__bubble--bottom .vk-tooltip__arrow { top: -3px; left: 50%; margin-left: -4px; }
.vk-tooltip__bubble--left .vk-tooltip__arrow   { right: -3px; top: 50%; margin-top: -4px; }
.vk-tooltip__bubble--right .vk-tooltip__arrow  { left: -3px; top: 50%; margin-top: -4px; }
`;

if (typeof document !== 'undefined' && !document.getElementById('vk-tooltip-css')) {
  const s = document.createElement('style');
  s.id = 'vk-tooltip-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function Tooltip({
  content,
  placement = 'top',
  children,
  className = '',
  ...rest
}) {
  const cls = ['vk-tooltip', className].filter(Boolean).join(' ');
  return (
    <span className={cls} {...rest}>
      {children}
      <span className={`vk-tooltip__bubble vk-tooltip__bubble--${placement}`} role="tooltip">
        {content}
        <span className="vk-tooltip__arrow" />
      </span>
    </span>
  );
}
