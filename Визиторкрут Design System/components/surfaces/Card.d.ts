import React from 'react';

export type CardVariant = 'outlined' | 'raised' | 'flat';
export type CardPadding = 'none' | 'sm' | 'md' | 'lg';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  padding?: CardPadding;
  /** Hover-lift + pointer + keyboard focus — use for tappable job rows. */
  interactive?: boolean;
  children?: React.ReactNode;
}

/**
 * Base surface. `outlined` is the default (crisp 1px border, no shadow — the
 * house style); `raised` adds a soft shadow; `flat` is a sunken tint. Set
 * `interactive` for tappable cards (e.g. a job in the feed).
 */
export function Card(props: CardProps): React.ReactElement;
