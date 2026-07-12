import React from 'react';

export type IconButtonVariant = 'solid' | 'soft' | 'outline' | 'ghost';
export type IconButtonSize = 'sm' | 'md' | 'lg';

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** The icon element (use the Icon component). */
  children: React.ReactNode;
  variant?: IconButtonVariant;
  size?: IconButtonSize;
  /** Fully rounded (pill) instead of the default squared radius. */
  round?: boolean;
  /** Always provide for accessibility — the button has no visible label. */
  'aria-label': string;
}

/**
 * Square (or round) icon-only button for toolbars, headers and map controls.
 * Always pass an `aria-label`.
 */
export function IconButton(props: IconButtonProps): React.ReactElement;
