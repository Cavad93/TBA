import React from 'react';

export interface IconProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Lucide icon name, e.g. "navigation", "wallet", "circle-check". */
  name: string;
  /** Pixel box (width & height). Default 20. */
  size?: number;
  /** Stroke weight. Brand default 1.75. */
  strokeWidth?: number;
  /** Overrides `currentColor` for the glyph. */
  color?: string;
}

/**
 * Thin wrapper over Lucide icons. The page must load the Lucide UMD script.
 * Decorative by default (`aria-hidden`); pair with a visible label or an
 * `aria-label` on the surrounding control for meaning.
 */
export function Icon(props: IconProps): React.ReactElement;
