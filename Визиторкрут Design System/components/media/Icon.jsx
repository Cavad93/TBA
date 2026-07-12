import React from 'react';

const CSS = `
.vk-icon { display: inline-flex; flex: none; line-height: 0; }
.vk-icon svg { width: 100%; height: 100%; display: block; }
`;

if (typeof document !== 'undefined' && !document.getElementById('vk-icon-css')) {
  const s = document.createElement('style');
  s.id = 'vk-icon-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/**
 * Renders a Lucide glyph. Requires the Lucide UMD script to be loaded on the page:
 *   <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>
 * We manage the inner DOM imperatively so React never fights Lucide's node swap.
 */
export function Icon({
  name,
  size = 20,
  strokeWidth = 1.75,
  color,
  className = '',
  style = {},
  ...rest
}) {
  const ref = React.useRef(null);

  React.useEffect(() => {
    const host = ref.current;
    if (!host) return;
    host.innerHTML = '';
    const i = document.createElement('i');
    i.setAttribute('data-lucide', name);
    host.appendChild(i);
    const lucide = typeof window !== 'undefined' ? window.lucide : null;
    if (lucide && typeof lucide.createIcons === 'function') {
      lucide.createIcons({ attrs: { 'stroke-width': strokeWidth } });
    }
  }, [name, strokeWidth]);

  return (
    <span
      ref={ref}
      className={['vk-icon', className].filter(Boolean).join(' ')}
      style={{ width: size, height: size, color, ...style }}
      aria-hidden="true"
      {...rest}
    />
  );
}
