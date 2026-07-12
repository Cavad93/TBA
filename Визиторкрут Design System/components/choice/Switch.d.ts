import React from 'react';

export interface SwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type' | 'size'> {
  label?: React.ReactNode;
  size?: 'sm' | 'md';
  /** Put the label before the switch. */
  labelPosition?: 'left' | 'right';
  /** Fill width and push the switch to the far end (settings rows). */
  spread?: boolean;
}

/**
 * On/off toggle for instant settings (online status, "Считать бензин",
 * push-уведомления). Use `spread` + `labelPosition="left"` for settings rows.
 */
export function Switch(props: SwitchProps): React.ReactElement;
