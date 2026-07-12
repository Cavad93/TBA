import React from 'react';

export type BadgeVariant = 'neutral' | 'success' | 'warning' | 'danger' | 'info';
export type BadgeAppearance = 'soft' | 'solid' | 'outline';
export type BadgeSize = 'sm' | 'md';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  /** soft (tinted, default) · solid (filled) · outline. */
  appearance?: BadgeAppearance;
  size?: BadgeSize;
  /** Leading status dot. */
  dot?: boolean;
  children?: React.ReactNode;
}

/**
 * Small status label — order state, ratings count, "новый", "онлайн". For the
 * worth-it verdict itself use the Verdict component, not a Badge.
 */
export function Badge(props: BadgeProps): React.ReactElement;
