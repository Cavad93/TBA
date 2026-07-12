import React from 'react';

export type MetricTone = 'default' | 'brand' | 'go' | 'skip';
export type MetricSize = 'sm' | 'md' | 'lg';

export interface MetricProps extends React.HTMLAttributes<HTMLDivElement> {
  /** The number/amount, e.g. "2 480", "8,2", "₽640". */
  value: React.ReactNode;
  /** Trailing unit rendered smaller, e.g. "км", "мин", "/ч". */
  unit?: React.ReactNode;
  /** Uppercase caption, optionally with a leading Icon. */
  label?: React.ReactNode;
  /** Small icon shown before the label. */
  icon?: React.ReactNode;
  /** Colors the value: brand/go = green, skip = red. */
  tone?: MetricTone;
  size?: MetricSize;
}

/**
 * A single dispatch-panel metric — pay, distance, minutes, ₽/hour. Value is set
 * in tabular mono so columns of Metrics line up cleanly.
 */
export function Metric(props: MetricProps): React.ReactElement;
