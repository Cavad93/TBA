import React from 'react';

export interface TabItem {
  value: string;
  label: React.ReactNode;
  /** Optional leading icon element. */
  icon?: React.ReactNode;
  /** Optional trailing count (mono), e.g. number of jobs in that tab. */
  count?: number | string;
}

export interface TabsProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onChange'> {
  items: TabItem[];
  /** Currently selected value (controlled). */
  value: string;
  onChange?: (value: string) => void;
  /** line = underline tabs; segmented = pill switcher. */
  variant?: 'line' | 'segmented';
  fullWidth?: boolean;
}

/**
 * Controlled tab switcher. `line` for section navigation (Лента / Активные /
 * История); `segmented` for compact in-card toggles.
 */
export function Tabs(props: TabsProps): React.ReactElement;
