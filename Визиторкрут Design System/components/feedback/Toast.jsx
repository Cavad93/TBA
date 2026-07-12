import React from 'react';
import { Icon } from '../media/Icon';

const CSS = `
.vk-toast {
  display: flex; align-items: flex-start; gap: 12px; font-family: var(--font-sans);
  background: var(--color-surface); border: 1px solid var(--border-default);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-lg);
  padding: 14px 14px 14px 14px; max-width: 420px; min-width: 280px;
}
.vk-toast__icon { flex: none; width: 28px; height: 28px; border-radius: var(--radius-pill);
  display: inline-flex; align-items: center; justify-content: center; margin-top: 1px; }
.vk-toast.is-success .vk-toast__icon { background: var(--success-bg); color: var(--success-text); }
.vk-toast.is-danger  .vk-toast__icon { background: var(--danger-bg);  color: var(--danger-text); }
.vk-toast.is-warning .vk-toast__icon { background: var(--warning-bg); color: var(--warning-text); }
.vk-toast.is-info    .vk-toast__icon { background: var(--info-bg);    color: var(--info-text); }
.vk-toast__body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.vk-toast__title { font-weight: 700; font-size: 14px; color: var(--text-primary); }
.vk-toast__desc { font-size: 13px; line-height: 1.4; color: var(--text-secondary); }
.vk-toast__action { margin-top: 8px; }
.vk-toast__close {
  flex: none; width: 24px; height: 24px; border-radius: var(--radius-sm); border: none;
  background: transparent; color: var(--text-tertiary); cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center; margin: -2px -2px 0 0;
}
.vk-toast__close:hover { background: var(--neutral-100); color: var(--text-primary); }
`;

if (typeof document !== 'undefined' && !document.getElementById('vk-toast-css')) {
  const s = document.createElement('style');
  s.id = 'vk-toast-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

const ICONS = {
  success: 'circle-check',
  danger: 'circle-x',
  warning: 'triangle-alert',
  info: 'info',
};

export function Toast({
  variant = 'info',
  title,
  children,
  action = null,
  onClose,
  className = '',
  ...rest
}) {
  const cls = ['vk-toast', `is-${variant}`, className].filter(Boolean).join(' ');
  return (
    <div className={cls} role="status" {...rest}>
      <span className="vk-toast__icon"><Icon name={ICONS[variant]} size={17} strokeWidth={2.25} /></span>
      <div className="vk-toast__body">
        {title && <span className="vk-toast__title">{title}</span>}
        {children && <span className="vk-toast__desc">{children}</span>}
        {action && <div className="vk-toast__action">{action}</div>}
      </div>
      {onClose && (
        <button type="button" className="vk-toast__close" aria-label="Закрыть" onClick={onClose}>
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
        </button>
      )}
    </div>
  );
}
