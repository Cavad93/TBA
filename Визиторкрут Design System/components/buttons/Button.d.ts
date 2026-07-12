import React from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg' | 'xl';

/**
 * Props for the Button component.
 * @startingPoint section="Buttons" subtitle="Кнопки: primary / secondary / ghost / danger" viewport="700x250"
 */
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual style. `primary` is the brand green — the "взять заказ" action. */
  variant?: ButtonVariant;
  /** Control height. `xl` (60px) is reserved for the single primary action on a screen. */
  size?: ButtonSize;
  /** Icon element before the label (use the Icon component). */
  iconLeft?: React.ReactNode;
  /** Icon element after the label. */
  iconRight?: React.ReactNode;
  /** Stretch to the width of the container. */
  fullWidth?: boolean;
  /** Show a spinner and block interaction. */
  loading?: boolean;
  children?: React.ReactNode;
}

/**
 * Primary interactive control. Green primary = commit / take a job; secondary =
 * neutral choice; ghost = low-emphasis; danger = destructive or "не стоит".
 */
export function Button(props: ButtonProps): React.ReactElement;
