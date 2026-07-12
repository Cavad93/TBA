import React from 'react';

export type VerdictLevel = 'go' | 'edge' | 'skip';
export type VerdictSize = 'sm' | 'md' | 'lg';

/**
 * Props for the Verdict component.
 * @startingPoint section="Verdict" subtitle="Вердикт «стоит / не стоит» — ядро продукта" viewport="700x340"
 */
export interface VerdictProps extends React.HTMLAttributes<HTMLElement> {
  /** go = стоит ехать · edge = на грани · skip = не стоит. */
  level?: VerdictLevel;
  /** sm = inline pill; md/lg = block card with badge + reason. */
  size?: VerdictSize;
  /** Override the default level label. */
  label?: React.ReactNode;
  /** One-line justification (block sizes only), e.g. "₽640/ч чистыми". */
  reason?: React.ReactNode;
}

/**
 * The product's signature element: the one glance that tells a field worker
 * whether a trip pays off. Uses the verdict color spine (green / amber / red).
 * Requires the Lucide script for its state icon.
 */
export function Verdict(props: VerdictProps): React.ReactElement;
