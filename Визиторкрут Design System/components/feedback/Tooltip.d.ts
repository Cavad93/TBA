import React from 'react';

export type TooltipPlacement = 'top' | 'bottom' | 'left' | 'right';

export interface TooltipProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Tooltip text/content. Keep it to one short line where possible. */
  content: React.ReactNode;
  placement?: TooltipPlacement;
  /** The trigger element (make it focusable for keyboard users). */
  children: React.ReactNode;
}

/**
 * Lightweight CSS hover/focus tooltip. Wrap a focusable trigger (an
 * IconButton, a "?" chip) so it appears on keyboard focus too.
 */
export function Tooltip(props: TooltipProps): React.ReactElement;
