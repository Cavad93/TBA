import React from 'react';

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'prefix' | 'size'> {
  label?: React.ReactNode;
  /** Helper text below the field. */
  hint?: React.ReactNode;
  /** Error text below the field; also turns the border red. */
  error?: React.ReactNode;
  required?: boolean;
  /** Icon inside, left of the text. */
  iconLeft?: React.ReactNode;
  /** Text/element before the input (e.g. "₽"). */
  prefix?: React.ReactNode;
  /** Text/element after the input (e.g. "км", "₽/ч"). */
  suffix?: React.ReactNode;
  size?: 'md' | 'lg';
}

/**
 * Labelled text field with hint/error states and optional icon/prefix/suffix.
 * Use prefix/suffix for units — "₽", "км", "₽/ч" — set in tabular mono.
 */
export function Input(props: InputProps): React.ReactElement;
