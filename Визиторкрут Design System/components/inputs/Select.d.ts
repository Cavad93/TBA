import React from 'react';

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  label?: React.ReactNode;
  hint?: React.ReactNode;
  error?: React.ReactNode;
  /** Options array; alternatively pass <option> children. */
  options?: SelectOption[];
  /** Disabled first option shown when nothing is selected. */
  placeholder?: string;
  size?: 'md' | 'lg';
}

/**
 * Styled native select (keeps the OS picker on mobile — right for a field app).
 * Pass `options` or `<option>` children.
 */
export function Select(props: SelectProps): React.ReactElement;
