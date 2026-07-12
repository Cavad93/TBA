import React from 'react';

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: React.ReactNode;
  /** Secondary line under the label. */
  description?: React.ReactNode;
  indeterminate?: boolean;
}

/**
 * Checkbox with optional label + description. Green when checked. Use for
 * multi-select preferences ("Не показывать заказы дешевле…", "Только рядом").
 */
export function Checkbox(props: CheckboxProps): React.ReactElement;
