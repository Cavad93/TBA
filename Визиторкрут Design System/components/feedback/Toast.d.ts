import React from 'react';

export type ToastVariant = 'info' | 'success' | 'warning' | 'danger';

export interface ToastProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: ToastVariant;
  title?: React.ReactNode;
  /** Description text (as children). */
  children?: React.ReactNode;
  /** Optional action element (e.g. a ghost Button). */
  action?: React.ReactNode;
  /** When provided, shows a close (×) button. */
  onClose?: () => void;
}

/**
 * Transient message with a variant icon. Keep copy short and human
 * ("Заказ взят. Погнали!"). Requires the Lucide script for the leading icon.
 */
export function Toast(props: ToastProps): React.ReactElement;
