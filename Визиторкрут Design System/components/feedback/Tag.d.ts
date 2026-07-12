import React from 'react';

export interface TagProps extends React.HTMLAttributes<HTMLElement> {
  children?: React.ReactNode;
  /** Active/pressed look (ink fill) — for filter chips. */
  selected?: boolean;
  /** Leading icon element. */
  icon?: React.ReactNode;
  /** When provided, renders a remove (×) affordance. */
  onRemove?: (e: React.MouseEvent) => void;
  /** When provided, the whole tag becomes a toggle button. */
  onClick?: (e: React.MouseEvent) => void;
  size?: 'sm' | 'md';
}

/**
 * Pill chip for filters and categories. Add `onClick` to make it a toggle
 * (profession filters: Такси / Курьер / Врач / Мастер); add `onRemove` for a
 * dismissable chip.
 */
export function Tag(props: TagProps): React.ReactElement;
