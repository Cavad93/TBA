/* @ds-bundle: {"format":4,"namespace":"DesignSystem_ee81bc","components":[{"name":"Button","sourcePath":"components/buttons/Button.jsx"},{"name":"IconButton","sourcePath":"components/buttons/IconButton.jsx"},{"name":"Checkbox","sourcePath":"components/choice/Checkbox.jsx"},{"name":"Radio","sourcePath":"components/choice/Radio.jsx"},{"name":"Switch","sourcePath":"components/choice/Switch.jsx"},{"name":"Badge","sourcePath":"components/feedback/Badge.jsx"},{"name":"Tag","sourcePath":"components/feedback/Tag.jsx"},{"name":"Toast","sourcePath":"components/feedback/Toast.jsx"},{"name":"Tooltip","sourcePath":"components/feedback/Tooltip.jsx"},{"name":"Input","sourcePath":"components/inputs/Input.jsx"},{"name":"Select","sourcePath":"components/inputs/Select.jsx"},{"name":"Textarea","sourcePath":"components/inputs/Textarea.jsx"},{"name":"Icon","sourcePath":"components/media/Icon.jsx"},{"name":"Tabs","sourcePath":"components/navigation/Tabs.jsx"},{"name":"Card","sourcePath":"components/surfaces/Card.jsx"},{"name":"Metric","sourcePath":"components/verdict/Metric.jsx"},{"name":"Verdict","sourcePath":"components/verdict/Verdict.jsx"}],"sourceHashes":{"components/buttons/Button.jsx":"599936c193b2","components/buttons/IconButton.jsx":"160d8b957cad","components/choice/Checkbox.jsx":"0698eb1c10bb","components/choice/Radio.jsx":"06593a2af625","components/choice/Switch.jsx":"dd7c000c3b17","components/feedback/Badge.jsx":"679b676ad41d","components/feedback/Tag.jsx":"695928102e3e","components/feedback/Toast.jsx":"36ebe5396b8a","components/feedback/Tooltip.jsx":"dc49430e0e20","components/inputs/Input.jsx":"585ebf7026b9","components/inputs/Select.jsx":"d7e5e5807fb6","components/inputs/Textarea.jsx":"587c060d4f74","components/media/Icon.jsx":"78a6c61243f0","components/navigation/Tabs.jsx":"e905ed279127","components/surfaces/Card.jsx":"04aede666b0f","components/verdict/Metric.jsx":"b0f35e7be4c8","components/verdict/Verdict.jsx":"b7e60fd678fd","ui_kits/app/app-data.js":"39846226444b","ui_kits/app/app.jsx":"34b974e62daa","ui_kits/app/ios-frame.jsx":"be3343be4b51","ui_kits/web/web.jsx":"7d0e206470c9"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.DesignSystem_ee81bc = window.DesignSystem_ee81bc || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/buttons/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vk-btn {
  --_h: 44px; --_px: 18px; --_fs: 15px; --_gap: 8px; --_r: var(--radius-lg);
  display: inline-flex; align-items: center; justify-content: center; gap: var(--_gap);
  height: var(--_h); padding: 0 var(--_px); border-radius: var(--_r);
  font-family: var(--font-sans); font-size: var(--_fs); font-weight: 600; line-height: 1;
  letter-spacing: -0.01em; white-space: nowrap; cursor: pointer; user-select: none;
  border: 1px solid transparent; background: none; color: inherit;
  transition: background var(--duration-fast) var(--ease-standard),
              border-color var(--duration-fast) var(--ease-standard),
              transform var(--duration-instant) var(--ease-standard),
              box-shadow var(--duration-fast) var(--ease-standard);
}
.vk-btn:focus-visible { outline: none; box-shadow: var(--ring-focus); }
.vk-btn:active { transform: scale(var(--press-scale)); }
.vk-btn--full { width: 100%; }

.vk-btn--sm { --_h: var(--control-sm); --_px: 14px; --_fs: 13px; --_gap: 6px; --_r: var(--radius-md); }
.vk-btn--md { --_h: var(--control-md); }
.vk-btn--lg { --_h: var(--control-lg); --_px: 22px; --_fs: 16px; }
.vk-btn--xl { --_h: var(--control-xl); --_px: 28px; --_fs: 17px; --_gap: 10px; --_r: var(--radius-xl); }

.vk-btn--primary { background: var(--brand); color: var(--on-brand); box-shadow: var(--shadow-xs); }
.vk-btn--primary:hover { background: var(--brand-hover); }
.vk-btn--primary:active { background: var(--brand-active); }

.vk-btn--secondary { background: var(--color-surface); color: var(--text-primary); border-color: var(--border-strong); }
.vk-btn--secondary:hover { background: var(--color-surface-sunken); border-color: var(--neutral-400); }

.vk-btn--ghost { background: transparent; color: var(--text-primary); }
.vk-btn--ghost:hover { background: var(--neutral-100); }

.vk-btn--danger { background: var(--danger); color: #fff; box-shadow: var(--shadow-xs); }
.vk-btn--danger:hover { background: var(--danger-hover); }

.vk-btn[disabled], .vk-btn[aria-disabled="true"] { opacity: 0.45; cursor: not-allowed; box-shadow: none; }
.vk-btn[disabled]:hover, .vk-btn[aria-disabled="true"]:hover { background: var(--brand); }
.vk-btn--secondary[disabled]:hover { background: var(--color-surface); border-color: var(--border-strong); }
.vk-btn--ghost[disabled]:hover { background: transparent; }
.vk-btn[disabled]:active, .vk-btn[aria-disabled="true"]:active { transform: none; }

.vk-btn__spinner {
  width: 1em; height: 1em; border-radius: 50%; flex: none;
  border: 2px solid currentColor; border-right-color: transparent;
  animation: vk-btn-spin 0.6s linear infinite;
}
@keyframes vk-btn-spin { to { transform: rotate(360deg); } }
.vk-btn__icon { display: inline-flex; flex: none; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vk-button-css')) {
  const s = document.createElement('style');
  s.id = 'vk-button-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
function Button({
  children,
  variant = 'primary',
  size = 'md',
  iconLeft = null,
  iconRight = null,
  fullWidth = false,
  loading = false,
  disabled = false,
  type = 'button',
  className = '',
  ...rest
}) {
  const isDisabled = disabled || loading;
  const cls = ['vk-btn', `vk-btn--${variant}`, `vk-btn--${size}`, fullWidth ? 'vk-btn--full' : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("button", _extends({
    type: type,
    className: cls,
    disabled: isDisabled
  }, rest), loading && /*#__PURE__*/React.createElement("span", {
    className: "vk-btn__spinner",
    "aria-hidden": "true"
  }), !loading && iconLeft && /*#__PURE__*/React.createElement("span", {
    className: "vk-btn__icon"
  }, iconLeft), children != null && /*#__PURE__*/React.createElement("span", null, children), !loading && iconRight && /*#__PURE__*/React.createElement("span", {
    className: "vk-btn__icon"
  }, iconRight));
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/buttons/Button.jsx", error: String((e && e.message) || e) }); }

// components/buttons/IconButton.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vk-iconbtn {
  --_s: 44px; --_r: var(--radius-md);
  display: inline-flex; align-items: center; justify-content: center;
  width: var(--_s); height: var(--_s); border-radius: var(--_r);
  border: 1px solid transparent; background: none; cursor: pointer; padding: 0;
  color: var(--text-primary); flex: none;
  transition: background var(--duration-fast) var(--ease-standard),
              border-color var(--duration-fast) var(--ease-standard),
              transform var(--duration-instant) var(--ease-standard),
              box-shadow var(--duration-fast) var(--ease-standard);
}
.vk-iconbtn:focus-visible { outline: none; box-shadow: var(--ring-focus); }
.vk-iconbtn:active { transform: scale(var(--press-scale)); }
.vk-iconbtn svg { width: 55%; height: 55%; }

.vk-iconbtn--sm { --_s: var(--control-sm); }
.vk-iconbtn--md { --_s: var(--control-md); }
.vk-iconbtn--lg { --_s: var(--control-lg); }
.vk-iconbtn--round { --_r: var(--radius-pill); }

.vk-iconbtn--solid { background: var(--brand); color: var(--on-brand); }
.vk-iconbtn--solid:hover { background: var(--brand-hover); }

.vk-iconbtn--soft { background: var(--brand-subtle); color: var(--brand-active); }
.vk-iconbtn--soft:hover { background: var(--green-100); }

.vk-iconbtn--outline { background: var(--color-surface); border-color: var(--border-strong); }
.vk-iconbtn--outline:hover { background: var(--color-surface-sunken); border-color: var(--neutral-400); }

.vk-iconbtn--ghost { background: transparent; }
.vk-iconbtn--ghost:hover { background: var(--neutral-100); }

.vk-iconbtn[disabled] { opacity: 0.4; cursor: not-allowed; }
.vk-iconbtn[disabled]:hover { background: transparent; }
.vk-iconbtn--solid[disabled]:hover { background: var(--brand); }
.vk-iconbtn[disabled]:active { transform: none; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vk-iconbtn-css')) {
  const s = document.createElement('style');
  s.id = 'vk-iconbtn-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
function IconButton({
  children,
  variant = 'ghost',
  size = 'md',
  round = false,
  disabled = false,
  className = '',
  ...rest
}) {
  const cls = ['vk-iconbtn', `vk-iconbtn--${variant}`, `vk-iconbtn--${size}`, round ? 'vk-iconbtn--round' : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("button", _extends({
    type: "button",
    className: cls,
    disabled: disabled
  }, rest), children);
}
Object.assign(__ds_scope, { IconButton });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/buttons/IconButton.jsx", error: String((e && e.message) || e) }); }

// components/choice/Checkbox.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vk-check { display: inline-flex; align-items: flex-start; gap: 10px; cursor: pointer;
  font-family: var(--font-sans); user-select: none; }
.vk-check.is-disabled { cursor: not-allowed; opacity: 0.5; }
.vk-check input { position: absolute; opacity: 0; width: 0; height: 0; }
.vk-check__box {
  flex: none; width: 22px; height: 22px; border-radius: var(--radius-sm); margin-top: 1px;
  border: 1.5px solid var(--border-strong); background: var(--color-surface);
  display: inline-flex; align-items: center; justify-content: center; color: #fff;
  transition: background var(--duration-fast) var(--ease-standard),
              border-color var(--duration-fast) var(--ease-standard);
}
.vk-check__box svg { opacity: 0; transform: scale(0.6); transition: opacity var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out); }
.vk-check:hover .vk-check__box { border-color: var(--neutral-400); }
.vk-check input:checked + .vk-check__box,
.vk-check input:indeterminate + .vk-check__box { background: var(--brand); border-color: var(--brand); }
.vk-check input:checked + .vk-check__box svg,
.vk-check input:indeterminate + .vk-check__box svg { opacity: 1; transform: scale(1); }
.vk-check input:focus-visible + .vk-check__box { box-shadow: var(--ring-focus); }
.vk-check__text { display: flex; flex-direction: column; gap: 2px; }
.vk-check__label { font-size: 15px; font-weight: 500; color: var(--text-primary); line-height: 1.35; }
.vk-check__desc { font-size: 13px; color: var(--text-secondary); line-height: 1.4; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vk-check-css')) {
  const s = document.createElement('style');
  s.id = 'vk-check-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
function Checkbox({
  label,
  description,
  checked,
  indeterminate = false,
  disabled = false,
  className = '',
  ...rest
}) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminate;
  }, [indeterminate]);
  return /*#__PURE__*/React.createElement("label", {
    className: ['vk-check', disabled ? 'is-disabled' : '', className].filter(Boolean).join(' ')
  }, /*#__PURE__*/React.createElement("input", _extends({
    ref: ref,
    type: "checkbox",
    checked: checked,
    disabled: disabled
  }, rest)), /*#__PURE__*/React.createElement("span", {
    className: "vk-check__box"
  }, indeterminate ? /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: "14",
    height: "14",
    fill: "none",
    stroke: "currentColor",
    "stroke-width": "3",
    "stroke-linecap": "round"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M6 12h12"
  })) : /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: "14",
    height: "14",
    fill: "none",
    stroke: "currentColor",
    "stroke-width": "3",
    "stroke-linecap": "round",
    "stroke-linejoin": "round"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M5 12.5l4.5 4.5L19 7"
  }))), (label || description) && /*#__PURE__*/React.createElement("span", {
    className: "vk-check__text"
  }, label && /*#__PURE__*/React.createElement("span", {
    className: "vk-check__label"
  }, label), description && /*#__PURE__*/React.createElement("span", {
    className: "vk-check__desc"
  }, description)));
}
Object.assign(__ds_scope, { Checkbox });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/choice/Checkbox.jsx", error: String((e && e.message) || e) }); }

// components/choice/Radio.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vk-radio { display: inline-flex; align-items: flex-start; gap: 10px; cursor: pointer;
  font-family: var(--font-sans); user-select: none; }
.vk-radio.is-disabled { cursor: not-allowed; opacity: 0.5; }
.vk-radio input { position: absolute; opacity: 0; width: 0; height: 0; }
.vk-radio__dot {
  flex: none; width: 22px; height: 22px; border-radius: 50%; margin-top: 1px;
  border: 1.5px solid var(--border-strong); background: var(--color-surface);
  display: inline-flex; align-items: center; justify-content: center;
  transition: border-color var(--duration-fast) var(--ease-standard); position: relative;
}
.vk-radio__dot::after {
  content: ""; width: 10px; height: 10px; border-radius: 50%; background: var(--brand);
  opacity: 0; transform: scale(0.5); transition: opacity var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out);
}
.vk-radio:hover .vk-radio__dot { border-color: var(--neutral-400); }
.vk-radio input:checked + .vk-radio__dot { border-color: var(--brand); }
.vk-radio input:checked + .vk-radio__dot::after { opacity: 1; transform: scale(1); }
.vk-radio input:focus-visible + .vk-radio__dot { box-shadow: var(--ring-focus); }
.vk-radio__text { display: flex; flex-direction: column; gap: 2px; }
.vk-radio__label { font-size: 15px; font-weight: 500; color: var(--text-primary); line-height: 1.35; }
.vk-radio__desc { font-size: 13px; color: var(--text-secondary); line-height: 1.4; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vk-radio-css')) {
  const s = document.createElement('style');
  s.id = 'vk-radio-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
function Radio({
  label,
  description,
  disabled = false,
  className = '',
  ...rest
}) {
  return /*#__PURE__*/React.createElement("label", {
    className: ['vk-radio', disabled ? 'is-disabled' : '', className].filter(Boolean).join(' ')
  }, /*#__PURE__*/React.createElement("input", _extends({
    type: "radio",
    disabled: disabled
  }, rest)), /*#__PURE__*/React.createElement("span", {
    className: "vk-radio__dot"
  }), (label || description) && /*#__PURE__*/React.createElement("span", {
    className: "vk-radio__text"
  }, label && /*#__PURE__*/React.createElement("span", {
    className: "vk-radio__label"
  }, label), description && /*#__PURE__*/React.createElement("span", {
    className: "vk-radio__desc"
  }, description)));
}
Object.assign(__ds_scope, { Radio });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/choice/Radio.jsx", error: String((e && e.message) || e) }); }

// components/choice/Switch.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vk-switch { display: inline-flex; align-items: center; gap: 10px; cursor: pointer;
  font-family: var(--font-sans); user-select: none; }
.vk-switch.is-disabled { cursor: not-allowed; opacity: 0.5; }
.vk-switch--left { flex-direction: row-reverse; }
.vk-switch--between { display: flex; justify-content: space-between; width: 100%; }
.vk-switch input { position: absolute; opacity: 0; width: 0; height: 0; }
.vk-switch__track {
  --_w: 46px; --_h: 28px; --_thumb: 22px;
  flex: none; width: var(--_w); height: var(--_h); border-radius: var(--radius-pill);
  background: var(--neutral-300); position: relative;
  transition: background var(--duration-base) var(--ease-standard);
}
.vk-switch--sm .vk-switch__track { --_w: 38px; --_h: 23px; --_thumb: 17px; }
.vk-switch__thumb {
  position: absolute; top: 50%; left: 3px; transform: translateY(-50%);
  width: var(--_thumb); height: var(--_thumb); border-radius: 50%; background: #fff;
  box-shadow: var(--shadow-sm);
  transition: left var(--duration-base) var(--ease-out);
}
.vk-switch input:checked + .vk-switch__track { background: var(--brand); }
.vk-switch input:checked + .vk-switch__track .vk-switch__thumb { left: calc(100% - var(--_thumb) - 3px); }
.vk-switch input:focus-visible + .vk-switch__track { box-shadow: var(--ring-focus); }
.vk-switch__label { font-size: 15px; font-weight: 500; color: var(--text-primary); }
`;
if (typeof document !== 'undefined' && !document.getElementById('vk-switch-css')) {
  const s = document.createElement('style');
  s.id = 'vk-switch-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
function Switch({
  label,
  size = 'md',
  labelPosition = 'right',
  spread = false,
  disabled = false,
  className = '',
  ...rest
}) {
  const cls = ['vk-switch', `vk-switch--${size}`, labelPosition === 'left' ? 'vk-switch--left' : '', spread ? 'vk-switch--between' : '', disabled ? 'is-disabled' : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("label", {
    className: cls
  }, /*#__PURE__*/React.createElement("input", _extends({
    type: "checkbox",
    role: "switch",
    disabled: disabled
  }, rest)), /*#__PURE__*/React.createElement("span", {
    className: "vk-switch__track"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vk-switch__thumb"
  })), label && /*#__PURE__*/React.createElement("span", {
    className: "vk-switch__label"
  }, label));
}
Object.assign(__ds_scope, { Switch });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/choice/Switch.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Badge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vk-badge {
  display: inline-flex; align-items: center; gap: 5px; font-family: var(--font-sans);
  font-weight: 600; border-radius: var(--radius-pill); white-space: nowrap; line-height: 1;
  border: 1px solid transparent;
}
.vk-badge--sm { height: 20px; padding: 0 8px; font-size: 11px; }
.vk-badge--md { height: 26px; padding: 0 11px; font-size: 13px; }
.vk-badge__dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex: none; }

/* soft (default) */
.vk-badge--soft.is-neutral { background: var(--neutral-100); color: var(--neutral-700); }
.vk-badge--soft.is-success { background: var(--success-bg); color: var(--success-text); }
.vk-badge--soft.is-warning { background: var(--warning-bg); color: var(--warning-text); }
.vk-badge--soft.is-danger  { background: var(--danger-bg);  color: var(--danger-text); }
.vk-badge--soft.is-info    { background: var(--info-bg);    color: var(--info-text); }

/* solid */
.vk-badge--solid { color: #fff; }
.vk-badge--solid.is-neutral { background: var(--neutral-700); }
.vk-badge--solid.is-success { background: var(--success); }
.vk-badge--solid.is-warning { background: var(--warning); color: var(--ink); }
.vk-badge--solid.is-danger  { background: var(--danger); }
.vk-badge--solid.is-info    { background: var(--info); }

/* outline */
.vk-badge--outline { background: transparent; }
.vk-badge--outline.is-neutral { color: var(--neutral-700); border-color: var(--border-strong); }
.vk-badge--outline.is-success { color: var(--success-text); border-color: var(--success-border); }
.vk-badge--outline.is-warning { color: var(--warning-text); border-color: var(--warning-border); }
.vk-badge--outline.is-danger  { color: var(--danger-text);  border-color: var(--danger-border); }
.vk-badge--outline.is-info    { color: var(--info-text);    border-color: var(--info-border); }
`;
if (typeof document !== 'undefined' && !document.getElementById('vk-badge-css')) {
  const s = document.createElement('style');
  s.id = 'vk-badge-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
function Badge({
  children,
  variant = 'neutral',
  appearance = 'soft',
  size = 'md',
  dot = false,
  className = '',
  ...rest
}) {
  const cls = ['vk-badge', `vk-badge--${appearance}`, `vk-badge--${size}`, `is-${variant}`, className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("span", _extends({
    className: cls
  }, rest), dot && /*#__PURE__*/React.createElement("span", {
    className: "vk-badge__dot"
  }), children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Badge.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Tag.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vk-tag {
  display: inline-flex; align-items: center; gap: 6px; font-family: var(--font-sans);
  font-weight: 600; font-size: 13px; line-height: 1; border-radius: var(--radius-pill);
  height: 34px; padding: 0 14px; cursor: default; user-select: none;
  background: var(--color-surface); color: var(--text-secondary);
  border: 1px solid var(--border-default);
  transition: background var(--duration-fast) var(--ease-standard),
              border-color var(--duration-fast) var(--ease-standard),
              color var(--duration-fast) var(--ease-standard);
}
.vk-tag--sm { height: 28px; padding: 0 11px; font-size: 12px; gap: 5px; }
.vk-tag--clickable { cursor: pointer; }
.vk-tag--clickable:hover { border-color: var(--neutral-400); background: var(--color-surface-sunken); }
.vk-tag--clickable:focus-visible { outline: none; box-shadow: var(--ring-focus); }
.vk-tag.is-selected {
  background: var(--ink); color: #fff; border-color: var(--ink);
}
.vk-tag.is-selected:hover { background: var(--neutral-800); border-color: var(--neutral-800); }
.vk-tag__icon { display: inline-flex; margin-left: -2px; }
.vk-tag__remove {
  display: inline-flex; align-items: center; justify-content: center; margin-right: -4px;
  width: 18px; height: 18px; border-radius: 50%; border: none; background: transparent;
  color: inherit; cursor: pointer; opacity: 0.6;
}
.vk-tag__remove:hover { opacity: 1; background: rgba(127,120,108,0.2); }
`;
if (typeof document !== 'undefined' && !document.getElementById('vk-tag-css')) {
  const s = document.createElement('style');
  s.id = 'vk-tag-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
function Tag({
  children,
  selected = false,
  icon = null,
  onRemove,
  onClick,
  size = 'md',
  className = '',
  ...rest
}) {
  const clickable = !!onClick;
  const cls = ['vk-tag', `vk-tag--${size}`, clickable ? 'vk-tag--clickable' : '', selected ? 'is-selected' : '', className].filter(Boolean).join(' ');
  const Comp = clickable ? 'button' : 'span';
  const compProps = clickable ? {
    type: 'button',
    onClick,
    'aria-pressed': selected
  } : {};
  return /*#__PURE__*/React.createElement(Comp, _extends({
    className: cls
  }, compProps, rest), icon && /*#__PURE__*/React.createElement("span", {
    className: "vk-tag__icon"
  }, icon), children, onRemove && /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "vk-tag__remove",
    "aria-label": "\u0423\u0431\u0440\u0430\u0442\u044C",
    onClick: e => {
      e.stopPropagation();
      onRemove(e);
    }
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: "12",
    height: "12",
    fill: "none",
    stroke: "currentColor",
    "stroke-width": "2.5",
    "stroke-linecap": "round"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M6 6l12 12M18 6L6 18"
  }))));
}
Object.assign(__ds_scope, { Tag });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Tag.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Tooltip.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vk-tooltip { position: relative; display: inline-flex; }
.vk-tooltip__bubble {
  position: absolute; z-index: 50; pointer-events: none;
  background: var(--ink); color: #fff; font-family: var(--font-sans);
  font-size: 12px; font-weight: 500; line-height: 1.35; letter-spacing: 0;
  padding: 6px 9px; border-radius: var(--radius-sm); max-width: 220px; width: max-content;
  box-shadow: var(--shadow-md); opacity: 0; transform: translateY(2px) scale(0.98);
  transition: opacity var(--duration-fast) var(--ease-standard),
              transform var(--duration-fast) var(--ease-standard);
}
.vk-tooltip:hover .vk-tooltip__bubble,
.vk-tooltip:focus-within .vk-tooltip__bubble { opacity: 1; transform: translateY(0) scale(1); }

.vk-tooltip__bubble--top    { bottom: 100%; left: 50%; margin-bottom: 8px; translate: -50% 0; }
.vk-tooltip__bubble--bottom { top: 100%; left: 50%; margin-top: 8px; translate: -50% 0; }
.vk-tooltip__bubble--left   { right: 100%; top: 50%; margin-right: 8px; translate: 0 -50%; }
.vk-tooltip__bubble--right  { left: 100%; top: 50%; margin-left: 8px; translate: 0 -50%; }

.vk-tooltip__arrow { position: absolute; width: 8px; height: 8px; background: var(--ink); transform: rotate(45deg); }
.vk-tooltip__bubble--top .vk-tooltip__arrow    { bottom: -3px; left: 50%; margin-left: -4px; }
.vk-tooltip__bubble--bottom .vk-tooltip__arrow { top: -3px; left: 50%; margin-left: -4px; }
.vk-tooltip__bubble--left .vk-tooltip__arrow   { right: -3px; top: 50%; margin-top: -4px; }
.vk-tooltip__bubble--right .vk-tooltip__arrow  { left: -3px; top: 50%; margin-top: -4px; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vk-tooltip-css')) {
  const s = document.createElement('style');
  s.id = 'vk-tooltip-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
function Tooltip({
  content,
  placement = 'top',
  children,
  className = '',
  ...rest
}) {
  const cls = ['vk-tooltip', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("span", _extends({
    className: cls
  }, rest), children, /*#__PURE__*/React.createElement("span", {
    className: `vk-tooltip__bubble vk-tooltip__bubble--${placement}`,
    role: "tooltip"
  }, content, /*#__PURE__*/React.createElement("span", {
    className: "vk-tooltip__arrow"
  })));
}
Object.assign(__ds_scope, { Tooltip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Tooltip.jsx", error: String((e && e.message) || e) }); }

// components/inputs/Input.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vk-field { display: flex; flex-direction: column; gap: 6px; font-family: var(--font-sans); }
.vk-field__label { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.vk-field__label .req { color: var(--danger); margin-left: 2px; }
.vk-field__msg { font-size: 12px; line-height: 1.35; color: var(--text-tertiary); }
.vk-field__msg--error { color: var(--danger-text); font-weight: 500; }

.vk-input {
  display: flex; align-items: center; gap: 8px; background: var(--color-surface);
  border: 1px solid var(--border-strong); border-radius: var(--radius-md);
  padding: 0 14px; transition: border-color var(--duration-fast) var(--ease-standard),
              box-shadow var(--duration-fast) var(--ease-standard);
}
.vk-input--md { height: var(--control-md); }
.vk-input--lg { height: var(--control-lg); }
.vk-input:hover { border-color: var(--neutral-400); }
.vk-input:focus-within { border-color: var(--brand); box-shadow: var(--ring-focus); }
.vk-input.is-error { border-color: var(--danger); }
.vk-input.is-error:focus-within { box-shadow: 0 0 0 3px rgba(217,59,59,0.28); }
.vk-input.is-disabled { background: var(--color-surface-sunken); border-color: var(--border-default); opacity: 0.7; }

.vk-input input {
  flex: 1; min-width: 0; border: none; outline: none; background: transparent;
  font-family: var(--font-sans); font-size: 15px; color: var(--text-primary); padding: 0;
}
.vk-input input::placeholder { color: var(--text-tertiary); }
.vk-input__icon { display: inline-flex; color: var(--text-tertiary); flex: none; }
.vk-input__affix { font-family: var(--font-mono); font-size: 14px; color: var(--text-secondary); flex: none; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vk-input-css')) {
  const s = document.createElement('style');
  s.id = 'vk-input-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
let _uid = 0;
function Input({
  label,
  hint,
  error,
  required = false,
  iconLeft = null,
  prefix = null,
  suffix = null,
  size = 'md',
  disabled = false,
  id,
  className = '',
  ...rest
}) {
  const ref = React.useRef(id || `vk-input-${++_uid}`);
  const inputId = id || ref.current;
  const boxCls = ['vk-input', `vk-input--${size}`, error ? 'is-error' : '', disabled ? 'is-disabled' : ''].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("div", {
    className: ['vk-field', className].filter(Boolean).join(' ')
  }, label && /*#__PURE__*/React.createElement("label", {
    className: "vk-field__label",
    htmlFor: inputId
  }, label, required && /*#__PURE__*/React.createElement("span", {
    className: "req"
  }, "*")), /*#__PURE__*/React.createElement("div", {
    className: boxCls
  }, iconLeft && /*#__PURE__*/React.createElement("span", {
    className: "vk-input__icon"
  }, iconLeft), prefix && /*#__PURE__*/React.createElement("span", {
    className: "vk-input__affix"
  }, prefix), /*#__PURE__*/React.createElement("input", _extends({
    id: inputId,
    disabled: disabled,
    "aria-invalid": !!error
  }, rest)), suffix && /*#__PURE__*/React.createElement("span", {
    className: "vk-input__affix"
  }, suffix)), (error || hint) && /*#__PURE__*/React.createElement("span", {
    className: `vk-field__msg ${error ? 'vk-field__msg--error' : ''}`
  }, error || hint));
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/inputs/Input.jsx", error: String((e && e.message) || e) }); }

// components/inputs/Select.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vk-field { display: flex; flex-direction: column; gap: 6px; font-family: var(--font-sans); }
.vk-field__label { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.vk-field__msg { font-size: 12px; line-height: 1.35; color: var(--text-tertiary); }
.vk-field__msg--error { color: var(--danger-text); font-weight: 500; }

.vk-select { position: relative; display: flex; }
.vk-select select {
  appearance: none; -webkit-appearance: none; width: 100%;
  font-family: var(--font-sans); font-size: 15px; color: var(--text-primary);
  background: var(--color-surface); border: 1px solid var(--border-strong);
  border-radius: var(--radius-md); padding: 0 40px 0 14px; cursor: pointer; outline: none;
  transition: border-color var(--duration-fast) var(--ease-standard),
              box-shadow var(--duration-fast) var(--ease-standard);
}
.vk-select--md select { height: var(--control-md); }
.vk-select--lg select { height: var(--control-lg); }
.vk-select select:hover { border-color: var(--neutral-400); }
.vk-select select:focus { border-color: var(--brand); box-shadow: var(--ring-focus); }
.vk-select.is-error select { border-color: var(--danger); }
.vk-select select:disabled { background: var(--color-surface-sunken); opacity: 0.7; cursor: not-allowed; }
.vk-select select.is-placeholder { color: var(--text-tertiary); }
.vk-select__chevron {
  position: absolute; right: 14px; top: 50%; transform: translateY(-50%);
  pointer-events: none; color: var(--text-tertiary); display: inline-flex;
}
`;
if (typeof document !== 'undefined' && !document.getElementById('vk-select-css')) {
  const s = document.createElement('style');
  s.id = 'vk-select-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
let _uid = 0;
function Select({
  label,
  hint,
  error,
  options = null,
  placeholder,
  value,
  size = 'md',
  id,
  className = '',
  children,
  ...rest
}) {
  const ref = React.useRef(id || `vk-select-${++_uid}`);
  const selId = id || ref.current;
  const isPlaceholder = placeholder != null && (value === '' || value == null);
  return /*#__PURE__*/React.createElement("div", {
    className: ['vk-field', className].filter(Boolean).join(' ')
  }, label && /*#__PURE__*/React.createElement("label", {
    className: "vk-field__label",
    htmlFor: selId
  }, label), /*#__PURE__*/React.createElement("div", {
    className: ['vk-select', `vk-select--${size}`, error ? 'is-error' : ''].filter(Boolean).join(' ')
  }, /*#__PURE__*/React.createElement("select", _extends({
    id: selId,
    value: value,
    className: isPlaceholder ? 'is-placeholder' : '',
    "aria-invalid": !!error
  }, rest), placeholder != null && /*#__PURE__*/React.createElement("option", {
    value: "",
    disabled: true
  }, placeholder), options ? options.map(o => /*#__PURE__*/React.createElement("option", {
    key: o.value,
    value: o.value
  }, o.label)) : children), /*#__PURE__*/React.createElement("span", {
    className: "vk-select__chevron"
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: "18",
    height: "18",
    fill: "none",
    stroke: "currentColor",
    "stroke-width": "2",
    "stroke-linecap": "round",
    "stroke-linejoin": "round"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M6 9l6 6 6-6"
  })))), (error || hint) && /*#__PURE__*/React.createElement("span", {
    className: `vk-field__msg ${error ? 'vk-field__msg--error' : ''}`
  }, error || hint));
}
Object.assign(__ds_scope, { Select });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/inputs/Select.jsx", error: String((e && e.message) || e) }); }

// components/inputs/Textarea.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vk-field { display: flex; flex-direction: column; gap: 6px; font-family: var(--font-sans); }
.vk-field__label { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.vk-field__msg { font-size: 12px; line-height: 1.35; color: var(--text-tertiary); }
.vk-field__msg--error { color: var(--danger-text); font-weight: 500; }

.vk-textarea {
  font-family: var(--font-sans); font-size: 15px; line-height: 1.5; color: var(--text-primary);
  background: var(--color-surface); border: 1px solid var(--border-strong);
  border-radius: var(--radius-md); padding: 11px 14px; resize: vertical; min-height: 88px;
  transition: border-color var(--duration-fast) var(--ease-standard),
              box-shadow var(--duration-fast) var(--ease-standard); outline: none;
}
.vk-textarea::placeholder { color: var(--text-tertiary); }
.vk-textarea:hover { border-color: var(--neutral-400); }
.vk-textarea:focus { border-color: var(--brand); box-shadow: var(--ring-focus); }
.vk-textarea.is-error { border-color: var(--danger); }
.vk-textarea:disabled { background: var(--color-surface-sunken); opacity: 0.7; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vk-textarea-css')) {
  const s = document.createElement('style');
  s.id = 'vk-textarea-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
let _uid = 0;
function Textarea({
  label,
  hint,
  error,
  required = false,
  id,
  className = '',
  ...rest
}) {
  const ref = React.useRef(id || `vk-textarea-${++_uid}`);
  const areaId = id || ref.current;
  return /*#__PURE__*/React.createElement("div", {
    className: ['vk-field', className].filter(Boolean).join(' ')
  }, label && /*#__PURE__*/React.createElement("label", {
    className: "vk-field__label",
    htmlFor: areaId
  }, label, required && /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--danger)'
    }
  }, " *")), /*#__PURE__*/React.createElement("textarea", _extends({
    id: areaId,
    className: ['vk-textarea', error ? 'is-error' : ''].filter(Boolean).join(' '),
    "aria-invalid": !!error
  }, rest)), (error || hint) && /*#__PURE__*/React.createElement("span", {
    className: `vk-field__msg ${error ? 'vk-field__msg--error' : ''}`
  }, error || hint));
}
Object.assign(__ds_scope, { Textarea });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/inputs/Textarea.jsx", error: String((e && e.message) || e) }); }

// components/media/Icon.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
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
function Icon({
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
      lucide.createIcons({
        attrs: {
          'stroke-width': strokeWidth
        }
      });
    }
  }, [name, strokeWidth]);
  return /*#__PURE__*/React.createElement("span", _extends({
    ref: ref,
    className: ['vk-icon', className].filter(Boolean).join(' '),
    style: {
      width: size,
      height: size,
      color,
      ...style
    },
    "aria-hidden": "true"
  }, rest));
}
Object.assign(__ds_scope, { Icon });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/media/Icon.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Toast.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vk-toast {
  display: flex; align-items: flex-start; gap: 12px; font-family: var(--font-sans);
  background: var(--color-surface); border: 1px solid var(--border-default);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-lg);
  padding: 14px 14px 14px 14px; max-width: 420px; min-width: 280px;
}
.vk-toast__icon { flex: none; width: 28px; height: 28px; border-radius: var(--radius-pill);
  display: inline-flex; align-items: center; justify-content: center; margin-top: 1px; }
.vk-toast.is-success .vk-toast__icon { background: var(--success-bg); color: var(--success-text); }
.vk-toast.is-danger  .vk-toast__icon { background: var(--danger-bg);  color: var(--danger-text); }
.vk-toast.is-warning .vk-toast__icon { background: var(--warning-bg); color: var(--warning-text); }
.vk-toast.is-info    .vk-toast__icon { background: var(--info-bg);    color: var(--info-text); }
.vk-toast__body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.vk-toast__title { font-weight: 700; font-size: 14px; color: var(--text-primary); }
.vk-toast__desc { font-size: 13px; line-height: 1.4; color: var(--text-secondary); }
.vk-toast__action { margin-top: 8px; }
.vk-toast__close {
  flex: none; width: 24px; height: 24px; border-radius: var(--radius-sm); border: none;
  background: transparent; color: var(--text-tertiary); cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center; margin: -2px -2px 0 0;
}
.vk-toast__close:hover { background: var(--neutral-100); color: var(--text-primary); }
`;
if (typeof document !== 'undefined' && !document.getElementById('vk-toast-css')) {
  const s = document.createElement('style');
  s.id = 'vk-toast-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
const ICONS = {
  success: 'circle-check',
  danger: 'circle-x',
  warning: 'triangle-alert',
  info: 'info'
};
function Toast({
  variant = 'info',
  title,
  children,
  action = null,
  onClose,
  className = '',
  ...rest
}) {
  const cls = ['vk-toast', `is-${variant}`, className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("div", _extends({
    className: cls,
    role: "status"
  }, rest), /*#__PURE__*/React.createElement("span", {
    className: "vk-toast__icon"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: ICONS[variant],
    size: 17,
    strokeWidth: 2.25
  })), /*#__PURE__*/React.createElement("div", {
    className: "vk-toast__body"
  }, title && /*#__PURE__*/React.createElement("span", {
    className: "vk-toast__title"
  }, title), children && /*#__PURE__*/React.createElement("span", {
    className: "vk-toast__desc"
  }, children), action && /*#__PURE__*/React.createElement("div", {
    className: "vk-toast__action"
  }, action)), onClose && /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "vk-toast__close",
    "aria-label": "\u0417\u0430\u043A\u0440\u044B\u0442\u044C",
    onClick: onClose
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: "14",
    height: "14",
    fill: "none",
    stroke: "currentColor",
    "stroke-width": "2.2",
    "stroke-linecap": "round"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M6 6l12 12M18 6L6 18"
  }))));
}
Object.assign(__ds_scope, { Toast });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Toast.jsx", error: String((e && e.message) || e) }); }

// components/navigation/Tabs.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vk-tabs { font-family: var(--font-sans); display: inline-flex; }
.vk-tabs--full { display: flex; width: 100%; }

/* line */
.vk-tabs--line { gap: 4px; border-bottom: 1px solid var(--border-default); }
.vk-tabs--line .vk-tab {
  appearance: none; border: none; background: none; cursor: pointer;
  padding: 10px 14px; font-size: 15px; font-weight: 600; color: var(--text-tertiary);
  position: relative; display: inline-flex; align-items: center; gap: 7px;
  transition: color var(--duration-fast) var(--ease-standard); margin-bottom: -1px;
}
.vk-tabs--line.vk-tabs--full .vk-tab { flex: 1; justify-content: center; }
.vk-tabs--line .vk-tab:hover { color: var(--text-secondary); }
.vk-tabs--line .vk-tab.is-active { color: var(--text-primary); }
.vk-tabs--line .vk-tab.is-active::after {
  content: ""; position: absolute; left: 8px; right: 8px; bottom: 0; height: 2.5px;
  background: var(--brand); border-radius: 2px;
}
.vk-tabs--line .vk-tab:focus-visible { outline: none; box-shadow: var(--ring-focus); border-radius: var(--radius-sm); }

/* segmented */
.vk-tabs--segmented {
  gap: 2px; background: var(--color-bg-sunken); border-radius: var(--radius-md);
  padding: 3px; border: 1px solid var(--border-subtle);
}
.vk-tabs--segmented .vk-tab {
  appearance: none; border: none; background: transparent; cursor: pointer;
  padding: 7px 14px; font-size: 14px; font-weight: 600; color: var(--text-secondary);
  border-radius: calc(var(--radius-md) - 3px); display: inline-flex; align-items: center;
  gap: 6px; justify-content: center; white-space: nowrap;
  transition: background var(--duration-fast) var(--ease-standard), color var(--duration-fast) var(--ease-standard);
}
.vk-tabs--segmented.vk-tabs--full .vk-tab { flex: 1; }
.vk-tabs--segmented .vk-tab:hover { color: var(--text-primary); }
.vk-tabs--segmented .vk-tab.is-active { background: var(--color-surface); color: var(--text-primary); box-shadow: var(--shadow-xs); }
.vk-tabs--segmented .vk-tab:focus-visible { outline: none; box-shadow: var(--ring-focus); }
.vk-tab__count { font-family: var(--font-mono); font-size: 12px; opacity: 0.7; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vk-tabs-css')) {
  const s = document.createElement('style');
  s.id = 'vk-tabs-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
function Tabs({
  items = [],
  value,
  onChange,
  variant = 'line',
  fullWidth = false,
  className = '',
  ...rest
}) {
  const cls = ['vk-tabs', `vk-tabs--${variant}`, fullWidth ? 'vk-tabs--full' : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("div", _extends({
    className: cls,
    role: "tablist"
  }, rest), items.map(it => {
    const active = it.value === value;
    return /*#__PURE__*/React.createElement("button", {
      key: it.value,
      type: "button",
      role: "tab",
      "aria-selected": active,
      className: ['vk-tab', active ? 'is-active' : ''].filter(Boolean).join(' '),
      onClick: () => onChange && onChange(it.value)
    }, it.icon, it.label, it.count != null && /*#__PURE__*/React.createElement("span", {
      className: "vk-tab__count"
    }, it.count));
  }));
}
Object.assign(__ds_scope, { Tabs });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/Tabs.jsx", error: String((e && e.message) || e) }); }

// components/surfaces/Card.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vk-card {
  background: var(--color-surface); border-radius: var(--radius-xl);
  border: 1px solid transparent; color: var(--text-primary);
  transition: transform var(--duration-fast) var(--ease-standard),
              box-shadow var(--duration-fast) var(--ease-standard),
              border-color var(--duration-fast) var(--ease-standard);
}
.vk-card--outlined { border-color: var(--border-default); }
.vk-card--raised { border-color: var(--border-subtle); box-shadow: var(--shadow-md); }
.vk-card--flat { background: var(--color-surface-sunken); }

.vk-card--pad-sm { padding: var(--space-3); }
.vk-card--pad-md { padding: var(--space-4); }
.vk-card--pad-lg { padding: var(--space-6); }

.vk-card--interactive { cursor: pointer; }
.vk-card--interactive:hover { transform: var(--lift); box-shadow: var(--shadow-lg); border-color: var(--border-strong); }
.vk-card--interactive:active { transform: scale(0.995); box-shadow: var(--shadow-sm); }
.vk-card--interactive:focus-visible { outline: none; box-shadow: var(--ring-focus); }
`;
if (typeof document !== 'undefined' && !document.getElementById('vk-card-css')) {
  const s = document.createElement('style');
  s.id = 'vk-card-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
function Card({
  children,
  variant = 'outlined',
  padding = 'md',
  interactive = false,
  className = '',
  ...rest
}) {
  const cls = ['vk-card', `vk-card--${variant}`, padding !== 'none' ? `vk-card--pad-${padding}` : '', interactive ? 'vk-card--interactive' : '', className].filter(Boolean).join(' ');
  const interactiveProps = interactive ? {
    tabIndex: 0,
    role: 'button'
  } : {};
  return /*#__PURE__*/React.createElement("div", _extends({
    className: cls
  }, interactiveProps, rest), children);
}
Object.assign(__ds_scope, { Card });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surfaces/Card.jsx", error: String((e && e.message) || e) }); }

// components/verdict/Metric.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vk-metric { display: inline-flex; flex-direction: column; gap: 4px; font-family: var(--font-sans); min-width: 0; }
.vk-metric__label {
  font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--text-tertiary); display: inline-flex; align-items: center; gap: 5px;
}
.vk-metric__value {
  font-family: var(--font-mono); font-feature-settings: var(--numeric-tabular);
  font-weight: 600; line-height: 1.05; letter-spacing: -0.01em; color: var(--text-primary);
  display: inline-flex; align-items: baseline; gap: 3px;
}
.vk-metric--sm .vk-metric__value { font-size: 16px; }
.vk-metric--md .vk-metric__value { font-size: 22px; }
.vk-metric--lg .vk-metric__value { font-size: 34px; }
.vk-metric__unit { font-size: 0.55em; font-weight: 500; color: var(--text-secondary); }
.vk-metric--go   .vk-metric__value { color: var(--verdict-go-text); }
.vk-metric--skip .vk-metric__value { color: var(--verdict-skip-text); }
.vk-metric--brand .vk-metric__value { color: var(--brand); }
.vk-metric__label .vk-icon { color: var(--text-tertiary); }
`;
if (typeof document !== 'undefined' && !document.getElementById('vk-metric-css')) {
  const s = document.createElement('style');
  s.id = 'vk-metric-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
function Metric({
  value,
  unit,
  label,
  icon = null,
  tone = 'default',
  size = 'md',
  className = '',
  ...rest
}) {
  const cls = ['vk-metric', `vk-metric--${size}`, `vk-metric--${tone}`, className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("div", _extends({
    className: cls
  }, rest), label != null && /*#__PURE__*/React.createElement("span", {
    className: "vk-metric__label"
  }, icon, label), /*#__PURE__*/React.createElement("span", {
    className: "vk-metric__value"
  }, value, unit && /*#__PURE__*/React.createElement("span", {
    className: "vk-metric__unit"
  }, unit)));
}
Object.assign(__ds_scope, { Metric });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/verdict/Metric.jsx", error: String((e && e.message) || e) }); }

// components/verdict/Verdict.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vk-verdict { font-family: var(--font-sans); display: inline-flex; }

/* --- pill (size sm) --- */
.vk-verdict--pill {
  align-items: center; gap: 6px; border-radius: var(--radius-pill);
  height: 28px; padding: 0 12px; font-size: 13px; font-weight: 700;
  letter-spacing: -0.01em; color: #fff;
}
.vk-verdict--pill.is-go   { background: var(--verdict-go); }
.vk-verdict--pill.is-edge { background: var(--verdict-edge); color: var(--ink); }
.vk-verdict--pill.is-skip { background: var(--verdict-skip); }

/* --- block (size md / lg) --- */
.vk-verdict--block {
  align-items: center; gap: 12px; border-radius: var(--radius-xl);
  border: 1.5px solid; padding: 12px 16px; width: 100%;
}
.vk-verdict--block.is-go   { background: var(--verdict-go-bg);   border-color: var(--verdict-go-border); }
.vk-verdict--block.is-edge { background: var(--verdict-edge-bg); border-color: var(--verdict-edge-border); }
.vk-verdict--block.is-skip { background: var(--verdict-skip-bg); border-color: var(--verdict-skip-border); }
.vk-verdict--lg { padding: 16px 18px; gap: 14px; }

.vk-verdict__badge {
  flex: none; display: inline-flex; align-items: center; justify-content: center;
  width: 40px; height: 40px; border-radius: var(--radius-pill); color: #fff;
}
.vk-verdict--lg .vk-verdict__badge { width: 48px; height: 48px; }
.is-go   .vk-verdict__badge { background: var(--verdict-go); box-shadow: var(--glow-go); }
.is-edge .vk-verdict__badge { background: var(--verdict-edge); color: var(--ink); }
.is-skip .vk-verdict__badge { background: var(--verdict-skip); box-shadow: var(--glow-skip); }

.vk-verdict__body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.vk-verdict__label { font-weight: 700; font-size: 16px; letter-spacing: -0.01em; }
.vk-verdict--lg .vk-verdict__label { font-size: 18px; }
.is-go   .vk-verdict__label { color: var(--verdict-go-text); }
.is-edge .vk-verdict__label { color: var(--verdict-edge-text); }
.is-skip .vk-verdict__label { color: var(--verdict-skip-text); }
.vk-verdict__reason { font-size: 13px; line-height: 1.4; color: var(--text-secondary); }
`;
if (typeof document !== 'undefined' && !document.getElementById('vk-verdict-css')) {
  const s = document.createElement('style');
  s.id = 'vk-verdict-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
const LEVELS = {
  go: {
    label: 'Стоит ехать',
    icon: 'circle-check'
  },
  edge: {
    label: 'На грани',
    icon: 'triangle-alert'
  },
  skip: {
    label: 'Не стоит',
    icon: 'circle-x'
  }
};
function Verdict({
  level = 'go',
  size = 'md',
  label,
  reason,
  className = '',
  ...rest
}) {
  const cfg = LEVELS[level] || LEVELS.go;
  const text = label != null ? label : cfg.label;
  if (size === 'sm') {
    const cls = ['vk-verdict', 'vk-verdict--pill', `is-${level}`, className].filter(Boolean).join(' ');
    return /*#__PURE__*/React.createElement("span", _extends({
      className: cls
    }, rest), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
      name: cfg.icon,
      size: 15,
      strokeWidth: 2.25
    }), text);
  }
  const cls = ['vk-verdict', 'vk-verdict--block', `is-${level}`, size === 'lg' ? 'vk-verdict--lg' : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("div", _extends({
    className: cls
  }, rest), /*#__PURE__*/React.createElement("span", {
    className: "vk-verdict__badge"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: cfg.icon,
    size: size === 'lg' ? 26 : 22,
    strokeWidth: 2.25
  })), /*#__PURE__*/React.createElement("span", {
    className: "vk-verdict__body"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vk-verdict__label"
  }, text), reason && /*#__PURE__*/React.createElement("span", {
    className: "vk-verdict__reason"
  }, reason)));
}
Object.assign(__ds_scope, { Verdict });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/verdict/Verdict.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/app-data.js
try { (() => {
/* Визиторкрут — mock data for the app UI kit (window.VK) */
window.VK = {
  professions: {
    taxi: {
      label: 'Такси',
      icon: 'car-front'
    },
    courier: {
      label: 'Курьер',
      icon: 'package'
    },
    doc: {
      label: 'Врач',
      icon: 'stethoscope'
    },
    master: {
      label: 'Мастер',
      icon: 'wrench'
    }
  },
  jobs: [{
    id: 'j1',
    prof: 'doc',
    level: 'go',
    title: 'Вызов на дом',
    addr: 'Пресня, ул. 1905 года, 8',
    pay: 3200,
    km: 4.1,
    min: 15,
    perHour: 980,
    client: 'Ирина М.',
    reason: 'Рядом и дорого — бери не думая.',
    steps: [{
      k: 'Оплата вызова',
      v: 3200,
      kind: 'plus'
    }, {
      k: 'Бензин 4 км',
      v: -60,
      kind: 'minus'
    }, {
      k: 'Время в пути 15 мин',
      v: -140,
      kind: 'minus'
    }]
  }, {
    id: 'j2',
    prof: 'taxi',
    level: 'go',
    title: 'До Шереметьево',
    addr: 'Тверская, 12 → SVO',
    pay: 2480,
    km: 38,
    min: 44,
    perHour: 640,
    client: 'Пассажир',
    reason: 'Загород без пробок — ₽640/ч чистыми.',
    steps: [{
      k: 'Тариф',
      v: 2480,
      kind: 'plus'
    }, {
      k: 'Бензин 38 км',
      v: -420,
      kind: 'minus'
    }, {
      k: 'Время в пути 44 мин',
      v: -410,
      kind: 'minus'
    }]
  }, {
    id: 'j3',
    prof: 'courier',
    level: 'go',
    title: 'Еда · 2 заказа рядом',
    addr: 'Патрики, два адреса по пути',
    pay: 560,
    km: 2.3,
    min: 12,
    perHour: 720,
    client: '2 клиента',
    reason: 'Два заказа по пути — быстрые деньги.',
    steps: [{
      k: 'Два заказа',
      v: 560,
      kind: 'plus'
    }, {
      k: 'Самокат',
      v: 0,
      kind: 'minus'
    }, {
      k: 'Время 12 мин',
      v: -120,
      kind: 'minus'
    }]
  }, {
    id: 'j4',
    prof: 'taxi',
    level: 'edge',
    title: 'По городу',
    addr: 'Арбат → Москва-Сити',
    pay: 640,
    km: 5.8,
    min: 26,
    perHour: 420,
    client: 'Пассажир',
    reason: 'Днём Садовое стоит — 50 на 50.',
    steps: [{
      k: 'Тариф',
      v: 640,
      kind: 'plus'
    }, {
      k: 'Бензин 6 км',
      v: -70,
      kind: 'minus'
    }, {
      k: 'Время в пробке 26 мин',
      v: -290,
      kind: 'minus'
    }]
  }, {
    id: 'j5',
    prof: 'courier',
    level: 'edge',
    title: 'Посылка, Китай-город',
    addr: '3 этажа без лифта',
    pay: 420,
    km: 6.2,
    min: 34,
    perHour: 310,
    client: 'Пункт выдачи',
    reason: 'Подъёмы без лифта съедят время.',
    steps: [{
      k: 'Доставка',
      v: 420,
      kind: 'plus'
    }, {
      k: 'Самокат 6 км',
      v: -20,
      kind: 'minus'
    }, {
      k: 'Время 34 мин',
      v: -260,
      kind: 'minus'
    }]
  }, {
    id: 'j6',
    prof: 'master',
    level: 'skip',
    title: 'Сборка шкафа',
    addr: 'Южное Бутово, далеко',
    pay: 1500,
    km: 22,
    min: 71,
    perHour: 280,
    client: 'Сергей П.',
    reason: 'Далеко и пробки — уйдёшь в минус по времени.',
    steps: [{
      k: 'Работа',
      v: 1500,
      kind: 'plus'
    }, {
      k: 'Бензин 22 км + обратно',
      v: -480,
      kind: 'minus'
    }, {
      k: 'Время в пути 71 мин',
      v: -660,
      kind: 'minus'
    }]
  }],
  earnings: {
    today: 4820,
    jobsDone: 7,
    hours: 5.5,
    perHour: 876,
    goal: 6000,
    week: [{
      d: 'Пн',
      v: 3200
    }, {
      d: 'Вт',
      v: 5100
    }, {
      d: 'Ср',
      v: 4200
    }, {
      d: 'Чт',
      v: 6100
    }, {
      d: 'Пт',
      v: 4820
    }, {
      d: 'Сб',
      v: 7300
    }, {
      d: 'Вс',
      v: 1900
    }],
    recent: [{
      title: 'Вызов на дом · Пресня',
      pay: 3060,
      level: 'go'
    }, {
      title: 'До Внуково',
      pay: 2140,
      level: 'go'
    }, {
      title: 'Еда · Патрики',
      pay: 320,
      level: 'edge'
    }]
  }
};
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/app-data.js", error: String((e && e.message) || e) }); }

// ui_kits/app/app.jsx
try { (() => {
/* Визиторкрут — App UI kit. Single-file app: reads window.VK (data),
   window.DesignSystem_ee81bc (components), window.IOSDevice (frame). */
(function () {
  const DS = window.DesignSystem_ee81bc;
  const {
    Button,
    IconButton,
    Icon,
    Verdict,
    Metric,
    Card,
    Badge,
    Tag,
    Switch,
    Tabs,
    Input,
    Select,
    Checkbox,
    Toast
  } = DS;
  const {
    professions: PROF,
    jobs: JOBS,
    earnings: EARN
  } = window.VK;
  const fmt = n => Math.round(n).toLocaleString('ru-RU');
  const toneFor = lvl => lvl === 'go' ? 'go' : lvl === 'skip' ? 'skip' : 'default';

  // ── shared bits ───────────────────────────────────────────
  function ScreenShell({
    children
  }) {
    return /*#__PURE__*/React.createElement("div", {
      style: {
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--paper)',
        fontFamily: 'var(--font-sans)',
        color: 'var(--text-primary)'
      }
    }, children);
  }
  function TopBar({
    title,
    sub,
    back,
    onBack,
    right
  }) {
    return /*#__PURE__*/React.createElement("div", {
      style: {
        paddingTop: 56,
        padding: '56px 16px 12px',
        flex: 'none',
        borderBottom: '1px solid var(--border-subtle)',
        background: 'var(--paper)',
        display: 'flex',
        alignItems: 'center',
        gap: 12
      }
    }, back && /*#__PURE__*/React.createElement(IconButton, {
      "aria-label": "\u041D\u0430\u0437\u0430\u0434",
      variant: "ghost",
      onClick: onBack
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "arrow-left"
    })), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1,
        minWidth: 0
      }
    }, sub && /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: '.08em',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)'
      }
    }, sub), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 22,
        fontWeight: 700,
        letterSpacing: '-0.01em',
        lineHeight: 1.15
      }
    }, title)), right);
  }
  function Main({
    children,
    pad = true
  }) {
    return /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1,
        minHeight: 0,
        overflowY: 'auto',
        padding: pad ? '16px 16px 24px' : 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 12
      }
    }, children);
  }
  function TabBar({
    tab,
    onTab,
    hasTrip
  }) {
    const items = [{
      k: 'feed',
      label: 'Лента',
      icon: 'layout-list'
    }, {
      k: 'trip',
      label: 'В пути',
      icon: 'navigation'
    }, {
      k: 'earn',
      label: 'Смена',
      icon: 'wallet'
    }, {
      k: 'profile',
      label: 'Профиль',
      icon: 'user-round'
    }];
    return /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 'none',
        display: 'flex',
        paddingBottom: 22,
        borderTop: '1px solid var(--border-default)',
        background: 'var(--color-surface)'
      }
    }, items.map(it => {
      const active = tab === it.k;
      return /*#__PURE__*/React.createElement("button", {
        key: it.k,
        onClick: () => onTab(it.k),
        style: {
          flex: 1,
          border: 'none',
          background: 'none',
          cursor: 'pointer',
          padding: '10px 0 4px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 3,
          position: 'relative',
          color: active ? 'var(--brand)' : 'var(--text-tertiary)'
        }
      }, /*#__PURE__*/React.createElement("div", {
        style: {
          position: 'relative'
        }
      }, /*#__PURE__*/React.createElement(Icon, {
        name: it.icon,
        size: 23,
        strokeWidth: active ? 2.25 : 1.9
      }), it.k === 'trip' && hasTrip && /*#__PURE__*/React.createElement("span", {
        style: {
          position: 'absolute',
          top: -2,
          right: -4,
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: 'var(--brand)',
          border: '1.5px solid var(--color-surface)'
        }
      })), /*#__PURE__*/React.createElement("span", {
        style: {
          fontSize: 11,
          fontWeight: 600
        }
      }, it.label));
    }));
  }
  function MapView({
    height = 200,
    radius = 16
  }) {
    return /*#__PURE__*/React.createElement("div", {
      style: {
        position: 'relative',
        height,
        borderRadius: radius,
        overflow: 'hidden',
        border: '1px solid var(--border-default)',
        background: '#E7E3D8',
        backgroundImage: `linear-gradient(0deg, rgba(23,22,15,0.035) 1px, transparent 1px),
          linear-gradient(90deg, rgba(23,22,15,0.035) 1px, transparent 1px),
          linear-gradient(0deg, rgba(255,255,255,0.6) 2px, transparent 2px),
          linear-gradient(90deg, rgba(255,255,255,0.6) 2px, transparent 2px)`,
        backgroundSize: '22px 22px, 22px 22px, 88px 88px, 88px 88px'
      }
    }, /*#__PURE__*/React.createElement("svg", {
      width: "100%",
      height: "100%",
      viewBox: "0 0 320 200",
      preserveAspectRatio: "none",
      style: {
        position: 'absolute',
        inset: 0
      }
    }, /*#__PURE__*/React.createElement("polyline", {
      points: "46,168 120,150 150,96 232,72 276,40",
      fill: "none",
      stroke: "var(--route)",
      strokeWidth: "6",
      strokeLinecap: "round",
      strokeLinejoin: "round",
      opacity: "0.9"
    })), /*#__PURE__*/React.createElement("span", {
      style: {
        position: 'absolute',
        left: 40,
        bottom: 150,
        width: 14,
        height: 14,
        borderRadius: '50%',
        background: '#fff',
        border: '4px solid var(--route)',
        transform: 'translate(-50%,50%)'
      }
    }), /*#__PURE__*/React.createElement("span", {
      style: {
        position: 'absolute',
        left: 276,
        top: 40,
        transform: 'translate(-50%,-90%)',
        color: 'var(--verdict-go)'
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "map-pin",
      size: 30,
      strokeWidth: 2.5
    })), /*#__PURE__*/React.createElement("span", {
      style: {
        position: 'absolute',
        top: 8,
        right: 8,
        background: 'rgba(255,255,255,0.85)',
        borderRadius: 6,
        padding: '3px 7px',
        fontSize: 10,
        color: 'var(--text-tertiary)',
        fontFamily: 'var(--font-mono)'
      }
    }, "\u043A\u0430\u0440\u0442\u0430 \u2014 \u0437\u0430\u0433\u043B\u0443\u0448\u043A\u0430"));
  }
  function ProfBadge({
    prof,
    size = 'md'
  }) {
    const p = PROF[prof];
    return /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        color: 'var(--text-secondary)',
        fontSize: size === 'sm' ? 12 : 13,
        fontWeight: 600
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: p.icon,
      size: size === 'sm' ? 14 : 16
    }), " ", p.label);
  }

  // ── job card (feed row) ───────────────────────────────────
  function JobCard({
    job,
    onOpen
  }) {
    return /*#__PURE__*/React.createElement(Card, {
      interactive: true,
      padding: "md",
      onClick: onOpen,
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 10
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }
    }, /*#__PURE__*/React.createElement(ProfBadge, {
      prof: job.prof
    }), /*#__PURE__*/React.createElement(Verdict, {
      level: job.level,
      size: "sm"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 16,
        fontWeight: 700,
        letterSpacing: '-0.01em'
      }
    }, job.title), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 13,
        color: 'var(--text-secondary)'
      }
    }, job.addr)), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: 20,
        paddingTop: 4,
        borderTop: '1px solid var(--border-subtle)'
      }
    }, /*#__PURE__*/React.createElement(Metric, {
      label: "\u041E\u043F\u043B\u0430\u0442\u0430",
      value: fmt(job.pay),
      unit: "\u20BD",
      tone: "brand",
      size: "sm"
    }), /*#__PURE__*/React.createElement(Metric, {
      label: "\u0414\u0438\u0441\u0442\u0430\u043D\u0446\u0438\u044F",
      value: String(job.km).replace('.', ','),
      unit: "\u043A\u043C",
      size: "sm"
    }), /*#__PURE__*/React.createElement(Metric, {
      label: "\u0412\u0440\u0435\u043C\u044F",
      value: job.min,
      unit: "\u043C\u0438\u043D",
      size: "sm"
    }), /*#__PURE__*/React.createElement(Metric, {
      label: "\u0427\u0438\u0441\u0442\u044B\u043C\u0438/\u0447",
      value: '₽' + fmt(job.perHour),
      tone: toneFor(job.level),
      size: "sm"
    })));
  }

  // ── FEED ──────────────────────────────────────────────────
  function FeedScreen({
    online,
    setOnline,
    onOpen
  }) {
    const [filter, setFilter] = React.useState('all');
    const filtered = filter === 'all' ? JOBS : JOBS.filter(j => j.prof === filter);
    const goodCount = JOBS.filter(j => j.level === 'go').length;
    return /*#__PURE__*/React.createElement(ScreenShell, null, /*#__PURE__*/React.createElement(TopBar, {
      title: "\u041B\u0435\u043D\u0442\u0430 \u0437\u0430\u043A\u0430\u0437\u043E\u0432",
      sub: `${goodCount} стоящих сейчас`,
      right: /*#__PURE__*/React.createElement(IconButton, {
        "aria-label": "\u0423\u0432\u0435\u0434\u043E\u043C\u043B\u0435\u043D\u0438\u044F",
        variant: "ghost"
      }, /*#__PURE__*/React.createElement(Icon, {
        name: "bell"
      }))
    }), /*#__PURE__*/React.createElement(Main, null, /*#__PURE__*/React.createElement(Card, {
      variant: "raised",
      padding: "md",
      style: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: '.08em',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)'
      }
    }, "\u0421\u0435\u0433\u043E\u0434\u043D\u044F \u0437\u0430\u0440\u0430\u0431\u043E\u0442\u0430\u043D\u043E"), /*#__PURE__*/React.createElement("div", {
      style: {
        fontFamily: 'var(--font-mono)',
        fontSize: 28,
        fontWeight: 600,
        color: 'var(--brand)',
        letterSpacing: '-0.01em'
      }
    }, "\u20BD", fmt(EARN.today))), /*#__PURE__*/React.createElement(Switch, {
      label: online ? 'На смене' : 'Не на смене',
      labelPosition: "left",
      checked: online,
      onChange: e => setOnline(e.target.checked)
    })), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: 8,
        overflowX: 'auto',
        margin: '0 -16px',
        padding: '2px 16px'
      }
    }, /*#__PURE__*/React.createElement(Tag, {
      selected: filter === 'all',
      onClick: () => setFilter('all')
    }, "\u0412\u0441\u0435"), Object.keys(PROF).map(k => /*#__PURE__*/React.createElement(Tag, {
      key: k,
      icon: /*#__PURE__*/React.createElement(Icon, {
        name: PROF[k].icon,
        size: 14
      }),
      selected: filter === k,
      onClick: () => setFilter(k)
    }, PROF[k].label))), filtered.map(j => /*#__PURE__*/React.createElement(JobCard, {
      key: j.id,
      job: j,
      onOpen: () => onOpen(j.id)
    }))));
  }

  // ── JOB DETAIL ────────────────────────────────────────────
  function DetailScreen({
    job,
    onBack,
    onTake
  }) {
    return /*#__PURE__*/React.createElement(ScreenShell, null, /*#__PURE__*/React.createElement(TopBar, {
      title: "\u0420\u0430\u0437\u0431\u043E\u0440 \u043F\u043E\u0435\u0437\u0434\u043A\u0438",
      back: true,
      onBack: onBack
    }), /*#__PURE__*/React.createElement(Main, null, /*#__PURE__*/React.createElement(MapView, {
      height: 168
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 20,
        fontWeight: 700,
        letterSpacing: '-0.01em'
      }
    }, job.title), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 13,
        color: 'var(--text-secondary)'
      }
    }, job.addr)), /*#__PURE__*/React.createElement(ProfBadge, {
      prof: job.prof
    })), /*#__PURE__*/React.createElement(Verdict, {
      level: job.level,
      size: "lg",
      reason: job.reason
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: 20,
        justifyContent: 'space-between'
      }
    }, /*#__PURE__*/React.createElement(Metric, {
      label: "\u041E\u043F\u043B\u0430\u0442\u0430",
      value: fmt(job.pay),
      unit: "\u20BD",
      tone: "brand",
      size: "md"
    }), /*#__PURE__*/React.createElement(Metric, {
      label: "\u0414\u0438\u0441\u0442\u0430\u043D\u0446\u0438\u044F",
      value: String(job.km).replace('.', ','),
      unit: "\u043A\u043C",
      size: "md"
    }), /*#__PURE__*/React.createElement(Metric, {
      label: "\u0412\u0440\u0435\u043C\u044F",
      value: job.min,
      unit: "\u043C\u0438\u043D",
      size: "md"
    })), /*#__PURE__*/React.createElement(Card, {
      padding: "md",
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 0
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: '.08em',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)',
        marginBottom: 10
      }
    }, "\u041A\u0430\u043A \u043F\u043E\u0441\u0447\u0438\u0442\u0430\u043B\u0438"), job.steps.map((s, i) => /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        display: 'flex',
        justifyContent: 'space-between',
        padding: '8px 0',
        borderBottom: '1px solid var(--border-subtle)',
        fontSize: 14
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        color: 'var(--text-secondary)'
      }
    }, s.k), /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'var(--font-mono)',
        fontWeight: 600,
        color: s.v > 0 ? 'var(--verdict-go-text)' : s.v < 0 ? 'var(--verdict-skip-text)' : 'var(--text-tertiary)'
      }
    }, s.v > 0 ? '+' : '', fmt(s.v), " \u20BD"))), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'baseline',
        paddingTop: 12
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        fontWeight: 700,
        fontSize: 15
      }
    }, "\u0427\u0438\u0441\u0442\u044B\u043C\u0438 \u0432 \u0447\u0430\u0441"), /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'var(--font-mono)',
        fontWeight: 600,
        fontSize: 24,
        color: job.level === 'skip' ? 'var(--verdict-skip-text)' : 'var(--brand)'
      }
    }, "\u20BD", fmt(job.perHour))))), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 'none',
        padding: '12px 16px 28px',
        borderTop: '1px solid var(--border-default)',
        background: 'var(--color-surface)',
        display: 'flex',
        gap: 10
      }
    }, /*#__PURE__*/React.createElement(Button, {
      variant: "secondary",
      size: "lg",
      onClick: onBack
    }, "\u041F\u0440\u043E\u043F\u0443\u0441\u0442\u0438\u0442\u044C"), /*#__PURE__*/React.createElement(Button, {
      variant: job.level === 'skip' ? 'secondary' : 'primary',
      size: "lg",
      fullWidth: true,
      iconLeft: /*#__PURE__*/React.createElement(Icon, {
        name: "circle-check",
        size: 20
      }),
      onClick: () => onTake(job)
    }, "\u0412\u0437\u044F\u0442\u044C \u0437\u0430\u043A\u0430\u0437")));
  }

  // ── ACTIVE TRIP ───────────────────────────────────────────
  function TripScreen({
    job,
    onFinish
  }) {
    if (!job) {
      return /*#__PURE__*/React.createElement(ScreenShell, null, /*#__PURE__*/React.createElement(TopBar, {
        title: "\u0412 \u043F\u0443\u0442\u0438"
      }), /*#__PURE__*/React.createElement(Main, null, /*#__PURE__*/React.createElement("div", {
        style: {
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          gap: 12,
          color: 'var(--text-tertiary)',
          paddingTop: 80
        }
      }, /*#__PURE__*/React.createElement(Icon, {
        name: "navigation",
        size: 40
      }), /*#__PURE__*/React.createElement("div", {
        style: {
          fontSize: 16,
          fontWeight: 600,
          color: 'var(--text-secondary)'
        }
      }, "\u0421\u0435\u0439\u0447\u0430\u0441 \u0442\u044B \u043D\u0438\u043A\u0443\u0434\u0430 \u043D\u0435 \u0435\u0434\u0435\u0448\u044C"), /*#__PURE__*/React.createElement("div", {
        style: {
          fontSize: 14,
          maxWidth: 240
        }
      }, "\u0412\u043E\u0437\u044C\u043C\u0438 \u0441\u0442\u043E\u044F\u0449\u0438\u0439 \u0437\u0430\u043A\u0430\u0437 \u0438\u0437 \u043B\u0435\u043D\u0442\u044B \u2014 \u0438 \u043E\u043D \u043F\u043E\u044F\u0432\u0438\u0442\u0441\u044F \u0437\u0434\u0435\u0441\u044C."))));
    }
    return /*#__PURE__*/React.createElement(ScreenShell, null, /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1,
        minHeight: 0,
        position: 'relative'
      }
    }, /*#__PURE__*/React.createElement(MapView, {
      height: 520,
      radius: 0
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        position: 'absolute',
        top: 60,
        left: 16,
        right: 16
      }
    }, /*#__PURE__*/React.createElement(Card, {
      variant: "raised",
      padding: "md",
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 12
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        width: 44,
        height: 44,
        borderRadius: 12,
        background: 'var(--brand-subtle)',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--brand-active)'
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "corner-up-right",
      size: 24,
      strokeWidth: 2.25
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
      style: {
        fontFamily: 'var(--font-mono)',
        fontSize: 20,
        fontWeight: 600
      }
    }, "\u0427\u0435\u0440\u0435\u0437 400 \u043C \u043D\u0430\u043F\u0440\u0430\u0432\u043E"), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 13,
        color: 'var(--text-secondary)'
      }
    }, "\u043D\u0430 \u0422\u0432\u0435\u0440\u0441\u043A\u0443\u044E \xB7 \u0437\u0430\u0442\u0435\u043C \u043F\u0440\u044F\u043C\u043E 2 \u043A\u043C")))), /*#__PURE__*/React.createElement("div", {
      style: {
        position: 'absolute',
        bottom: 12,
        right: 12
      }
    }, /*#__PURE__*/React.createElement(IconButton, {
      "aria-label": "\u041C\u043E\u0439 \u043A\u0443\u0440\u0441",
      variant: "solid",
      round: true
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "navigation"
    })))), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 'none',
        padding: '16px 16px 28px',
        borderTop: '1px solid var(--border-default)',
        background: 'var(--color-surface)',
        display: 'flex',
        flexDirection: 'column',
        gap: 14
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 16,
        fontWeight: 700
      }
    }, job.title), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 13,
        color: 'var(--text-secondary)'
      }
    }, job.client, " \xB7 ", job.addr)), /*#__PURE__*/React.createElement(Metric, {
      label: "\u0417\u0430\u0440\u0430\u0431\u043E\u0442\u043E\u043A",
      value: '₽' + fmt(job.pay),
      tone: "brand",
      size: "md"
    })), /*#__PURE__*/React.createElement(Button, {
      variant: "primary",
      size: "xl",
      fullWidth: true,
      iconLeft: /*#__PURE__*/React.createElement(Icon, {
        name: "flag",
        size: 20
      }),
      onClick: onFinish
    }, "\u042F \u043D\u0430 \u043C\u0435\u0441\u0442\u0435")));
  }

  // ── EARNINGS ──────────────────────────────────────────────
  function EarningsScreen() {
    const [period, setPeriod] = React.useState('week');
    const max = Math.max(...EARN.week.map(w => w.v));
    return /*#__PURE__*/React.createElement(ScreenShell, null, /*#__PURE__*/React.createElement(TopBar, {
      title: "\u0421\u043C\u0435\u043D\u0430",
      sub: "\u041F\u044F\u0442\u043D\u0438\u0446\u0430, 5 \u0438\u044E\u043B\u044F",
      right: /*#__PURE__*/React.createElement(IconButton, {
        "aria-label": "\u041A\u0430\u043B\u0435\u043D\u0434\u0430\u0440\u044C",
        variant: "ghost"
      }, /*#__PURE__*/React.createElement(Icon, {
        name: "calendar"
      }))
    }), /*#__PURE__*/React.createElement(Main, null, /*#__PURE__*/React.createElement(Card, {
      variant: "raised",
      padding: "lg",
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 12
      }
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: '.08em',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)'
      }
    }, "\u0417\u0430\u0440\u0430\u0431\u043E\u0442\u0430\u043D\u043E \u0441\u0435\u0433\u043E\u0434\u043D\u044F"), /*#__PURE__*/React.createElement("div", {
      style: {
        fontFamily: 'var(--font-mono)',
        fontSize: 40,
        fontWeight: 600,
        color: 'var(--brand)',
        letterSpacing: '-0.02em',
        lineHeight: 1.05
      }
    }, "\u20BD", fmt(EARN.today))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
      style: {
        height: 8,
        borderRadius: 999,
        background: 'var(--neutral-200)',
        overflow: 'hidden'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        width: Math.round(EARN.today / EARN.goal * 100) + '%',
        height: '100%',
        background: 'var(--brand)',
        borderRadius: 999
      }
    })), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 12,
        color: 'var(--text-secondary)',
        marginTop: 6
      }
    }, "\u0426\u0435\u043B\u044C \u043D\u0430 \u0434\u0435\u043D\u044C \u2014 \u20BD", fmt(EARN.goal), ". \u041E\u0441\u0442\u0430\u043B\u043E\u0441\u044C \u20BD", fmt(EARN.goal - EARN.today), ".")), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: 24,
        paddingTop: 4
      }
    }, /*#__PURE__*/React.createElement(Metric, {
      label: "\u0417\u0430\u043A\u0430\u0437\u043E\u0432",
      value: EARN.jobsDone,
      size: "md"
    }), /*#__PURE__*/React.createElement(Metric, {
      label: "\u0427\u0430\u0441\u043E\u0432",
      value: String(EARN.hours).replace('.', ','),
      size: "md"
    }), /*#__PURE__*/React.createElement(Metric, {
      label: "\u0427\u0438\u0441\u0442\u044B\u043C\u0438/\u0447",
      value: '₽' + fmt(EARN.perHour),
      tone: "go",
      size: "md"
    }))), /*#__PURE__*/React.createElement(Tabs, {
      variant: "segmented",
      fullWidth: true,
      value: period,
      onChange: setPeriod,
      items: [{
        value: 'day',
        label: 'День'
      }, {
        value: 'week',
        label: 'Неделя'
      }, {
        value: 'month',
        label: 'Месяц'
      }]
    }), /*#__PURE__*/React.createElement(Card, {
      padding: "md"
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'flex-end',
        gap: 10,
        height: 140
      }
    }, EARN.week.map((w, i) => {
      const isToday = i === 4;
      return /*#__PURE__*/React.createElement("div", {
        key: w.d,
        style: {
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 6,
          height: '100%',
          justifyContent: 'flex-end'
        }
      }, /*#__PURE__*/React.createElement("div", {
        style: {
          fontFamily: 'var(--font-mono)',
          fontSize: 10,
          color: 'var(--text-tertiary)'
        }
      }, Math.round(w.v / 1000), "\u043A"), /*#__PURE__*/React.createElement("div", {
        style: {
          width: '100%',
          height: Math.round(w.v / max * 96) + 'px',
          background: isToday ? 'var(--brand)' : 'var(--green-100)',
          borderRadius: 6
        }
      }), /*#__PURE__*/React.createElement("div", {
        style: {
          fontSize: 11,
          color: isToday ? 'var(--text-primary)' : 'var(--text-tertiary)',
          fontWeight: isToday ? 700 : 500
        }
      }, w.d));
    }))), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: '.08em',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)',
        marginTop: 4
      }
    }, "\u041F\u043E\u0441\u043B\u0435\u0434\u043D\u0438\u0435"), EARN.recent.map((r, i) => /*#__PURE__*/React.createElement(Card, {
      key: i,
      padding: "sm",
      style: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 10
      }
    }, /*#__PURE__*/React.createElement(Verdict, {
      level: r.level,
      size: "sm"
    }), /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: 14,
        fontWeight: 600
      }
    }, r.title)), /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'var(--font-mono)',
        fontWeight: 600,
        color: 'var(--brand)'
      }
    }, "+\u20BD", fmt(r.pay))))));
  }

  // ── PROFILE ───────────────────────────────────────────────
  function ProfileScreen() {
    return /*#__PURE__*/React.createElement(ScreenShell, null, /*#__PURE__*/React.createElement(TopBar, {
      title: "\u041F\u0440\u043E\u0444\u0438\u043B\u044C",
      right: /*#__PURE__*/React.createElement(IconButton, {
        "aria-label": "\u041D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u0438",
        variant: "ghost"
      }, /*#__PURE__*/React.createElement(Icon, {
        name: "settings"
      }))
    }), /*#__PURE__*/React.createElement(Main, null, /*#__PURE__*/React.createElement(Card, {
      padding: "md",
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 14
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        width: 56,
        height: 56,
        borderRadius: '50%',
        background: 'var(--ink)',
        color: '#fff',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'var(--font-display)',
        fontWeight: 700,
        fontSize: 20
      }
    }, "\u0410\u041A"), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 18,
        fontWeight: 700
      }
    }, "\u0410\u043B\u0435\u043A\u0441\u0435\u0439 \u041A."), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        marginTop: 2
      }
    }, /*#__PURE__*/React.createElement(ProfBadge, {
      prof: "taxi",
      size: "sm"
    }), /*#__PURE__*/React.createElement(Badge, {
      variant: "warning",
      size: "sm"
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "star",
      size: 12
    }), " 4,9")))), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: '.08em',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)',
        marginTop: 4
      }
    }, "\u0420\u0430\u0441\u0447\u0451\u0442 \u0432\u0435\u0440\u0434\u0438\u043A\u0442\u0430"), /*#__PURE__*/React.createElement(Card, {
      padding: "md",
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 14
      }
    }, /*#__PURE__*/React.createElement(Select, {
      label: "\u0422\u0440\u0430\u043D\u0441\u043F\u043E\u0440\u0442",
      defaultValue: "car",
      options: [{
        value: 'car',
        label: 'Авто · бензин'
      }, {
        value: 'bike',
        label: 'Велосипед'
      }, {
        value: 'foot',
        label: 'Пешком'
      }]
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: 12
      }
    }, /*#__PURE__*/React.createElement(Input, {
      label: "\u0426\u0435\u043D\u0430 \u0431\u0435\u043D\u0437\u0438\u043D\u0430",
      suffix: "\u20BD/\u043B",
      defaultValue: "58"
    }), /*#__PURE__*/React.createElement(Input, {
      label: "\u041C\u0438\u043D\u0438\u043C\u0443\u043C \u0434\u043B\u044F \xAB\u0441\u0442\u043E\u0438\u0442\xBB",
      suffix: "\u20BD/\u0447",
      defaultValue: "500"
    }))), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: '.08em',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)',
        marginTop: 4
      }
    }, "\u0427\u0442\u043E \u043F\u043E\u043A\u0430\u0437\u044B\u0432\u0430\u0442\u044C"), /*#__PURE__*/React.createElement(Card, {
      padding: "md",
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 14
      }
    }, /*#__PURE__*/React.createElement(Switch, {
      label: "\u0421\u0447\u0438\u0442\u0430\u0442\u044C \u0431\u0435\u043D\u0437\u0438\u043D \u0438 \u0438\u0437\u043D\u043E\u0441",
      labelPosition: "left",
      spread: true,
      defaultChecked: true
    }), /*#__PURE__*/React.createElement(Switch, {
      label: "\u041F\u0440\u044F\u0442\u0430\u0442\u044C \u0437\u0430\u043A\u0430\u0437\u044B \xAB\u043D\u0435 \u0441\u0442\u043E\u0438\u0442\xBB",
      labelPosition: "left",
      spread: true
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        height: 1,
        background: 'var(--border-subtle)'
      }
    }), /*#__PURE__*/React.createElement(Checkbox, {
      label: "\u0422\u043E\u043B\u044C\u043A\u043E \u0437\u0430\u043A\u0430\u0437\u044B \u0440\u044F\u0434\u043E\u043C",
      description: "\u0412 \u0440\u0430\u0434\u0438\u0443\u0441\u0435 5 \u043A\u043C \u043E\u0442 \u043C\u0435\u043D\u044F",
      defaultChecked: true
    })), /*#__PURE__*/React.createElement(Button, {
      variant: "ghost",
      fullWidth: true,
      iconLeft: /*#__PURE__*/React.createElement(Icon, {
        name: "log-out",
        size: 18
      }),
      style: {
        color: 'var(--danger-text)'
      }
    }, "\u0412\u044B\u0439\u0442\u0438")));
  }

  // ── APP shell ─────────────────────────────────────────────
  function App() {
    const IOSDevice = window.IOSDevice;
    const [tab, setTab] = React.useState('feed');
    const [view, setView] = React.useState({
      screen: 'feed'
    });
    const [online, setOnline] = React.useState(true);
    const [trip, setTrip] = React.useState(null);
    const [toast, setToast] = React.useState(null);
    const flash = t => {
      setToast(t);
      clearTimeout(window.__vkT);
      window.__vkT = setTimeout(() => setToast(null), 3000);
    };
    const openJob = id => setView({
      screen: 'detail',
      jobId: id
    });
    const backFeed = () => setView({
      screen: 'feed'
    });
    const takeJob = job => {
      setTrip(job);
      setView({
        screen: 'feed'
      });
      setTab('trip');
      flash({
        variant: 'success',
        title: 'Заказ взят. Погнали!'
      });
    };
    const finishTrip = job => {
      setTrip(null);
      setTab('earn');
      flash({
        variant: 'success',
        title: 'Готово. +₽' + fmt(job.pay) + ' на счёт'
      });
    };
    const goTab = k => {
      setView({
        screen: 'feed'
      });
      setTab(k);
    };
    let body;
    if (view.screen === 'detail') {
      body = /*#__PURE__*/React.createElement(DetailScreen, {
        job: JOBS.find(j => j.id === view.jobId),
        onBack: backFeed,
        onTake: takeJob
      });
    } else if (tab === 'feed') {
      body = /*#__PURE__*/React.createElement(FeedScreen, {
        online: online,
        setOnline: setOnline,
        onOpen: openJob
      });
    } else if (tab === 'trip') {
      body = /*#__PURE__*/React.createElement(TripScreen, {
        job: trip,
        onFinish: () => finishTrip(trip)
      });
    } else if (tab === 'earn') {
      body = /*#__PURE__*/React.createElement(EarningsScreen, null);
    } else {
      body = /*#__PURE__*/React.createElement(ProfileScreen, null);
    }
    const showTabs = view.screen !== 'detail';
    return /*#__PURE__*/React.createElement(IOSDevice, {
      width: 402,
      height: 874
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1,
        minHeight: 0
      }
    }, body), showTabs && /*#__PURE__*/React.createElement(TabBar, {
      tab: tab,
      onTab: goTab,
      hasTrip: !!trip
    }), toast && /*#__PURE__*/React.createElement("div", {
      style: {
        position: 'absolute',
        left: 16,
        right: 16,
        bottom: showTabs ? 96 : 40,
        zIndex: 80
      }
    }, /*#__PURE__*/React.createElement(Toast, {
      variant: toast.variant,
      title: toast.title,
      onClose: () => setToast(null)
    }))));
  }
  window.VKApp = App;
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/app.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/ios-frame.jsx
try { (() => {
// @ds-adherence-ignore -- omelette starter scaffold (raw elements/hex/px by design)

/* BEGIN USAGE */
// iOS.jsx — Simplified iOS 26 (Liquid Glass) device frame
// Based on the iOS 26 UI Kit + Figma status bar spec. No assets, no deps.
// Exports (to window): IOSDevice, IOSStatusBar, IOSNavBar, IOSGlassPill, IOSList, IOSListRow, IOSKeyboard
//
// Usage — wrap your screen content in <IOSDevice> to get the bezel, status bar
// and home indicator (props: title, dark, keyboard):
//
//   <IOSDevice title="Settings">
//     ...your screen content...
//   </IOSDevice>
//   <IOSDevice dark title="Search" keyboard>…</IOSDevice>
/* END USAGE */

// ─────────────────────────────────────────────────────────────
// Status bar
// ─────────────────────────────────────────────────────────────
function IOSStatusBar({
  dark = false,
  time = '9:41'
}) {
  const c = dark ? '#fff' : '#000';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 154,
      alignItems: 'center',
      justifyContent: 'center',
      padding: '21px 24px 19px',
      boxSizing: 'border-box',
      position: 'relative',
      zIndex: 20,
      width: '100%'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      height: 22,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      paddingTop: 1.5
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: '-apple-system, "SF Pro", system-ui',
      fontWeight: 590,
      fontSize: 17,
      lineHeight: '22px',
      color: c
    }
  }, time)), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      height: 22,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 7,
      paddingTop: 1,
      paddingRight: 1
    }
  }, /*#__PURE__*/React.createElement("svg", {
    width: "19",
    height: "12",
    viewBox: "0 0 19 12"
  }, /*#__PURE__*/React.createElement("rect", {
    x: "0",
    y: "7.5",
    width: "3.2",
    height: "4.5",
    rx: "0.7",
    fill: c
  }), /*#__PURE__*/React.createElement("rect", {
    x: "4.8",
    y: "5",
    width: "3.2",
    height: "7",
    rx: "0.7",
    fill: c
  }), /*#__PURE__*/React.createElement("rect", {
    x: "9.6",
    y: "2.5",
    width: "3.2",
    height: "9.5",
    rx: "0.7",
    fill: c
  }), /*#__PURE__*/React.createElement("rect", {
    x: "14.4",
    y: "0",
    width: "3.2",
    height: "12",
    rx: "0.7",
    fill: c
  })), /*#__PURE__*/React.createElement("svg", {
    width: "17",
    height: "12",
    viewBox: "0 0 17 12"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M8.5 3.2C10.8 3.2 12.9 4.1 14.4 5.6L15.5 4.5C13.7 2.7 11.2 1.5 8.5 1.5C5.8 1.5 3.3 2.7 1.5 4.5L2.6 5.6C4.1 4.1 6.2 3.2 8.5 3.2Z",
    fill: c
  }), /*#__PURE__*/React.createElement("path", {
    d: "M8.5 6.8C9.9 6.8 11.1 7.3 12 8.2L13.1 7.1C11.8 5.9 10.2 5.1 8.5 5.1C6.8 5.1 5.2 5.9 3.9 7.1L5 8.2C5.9 7.3 7.1 6.8 8.5 6.8Z",
    fill: c
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "8.5",
    cy: "10.5",
    r: "1.5",
    fill: c
  })), /*#__PURE__*/React.createElement("svg", {
    width: "27",
    height: "13",
    viewBox: "0 0 27 13"
  }, /*#__PURE__*/React.createElement("rect", {
    x: "0.5",
    y: "0.5",
    width: "23",
    height: "12",
    rx: "3.5",
    stroke: c,
    strokeOpacity: "0.35",
    fill: "none"
  }), /*#__PURE__*/React.createElement("rect", {
    x: "2",
    y: "2",
    width: "20",
    height: "9",
    rx: "2",
    fill: c
  }), /*#__PURE__*/React.createElement("path", {
    d: "M25 4.5V8.5C25.8 8.2 26.5 7.2 26.5 6.5C26.5 5.8 25.8 4.8 25 4.5Z",
    fill: c,
    fillOpacity: "0.4"
  }))));
}

// ─────────────────────────────────────────────────────────────
// Liquid glass pill — blur + tint + shine
// ─────────────────────────────────────────────────────────────
function IOSGlassPill({
  children,
  dark = false,
  style = {}
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      height: 44,
      minWidth: 44,
      borderRadius: 9999,
      position: 'relative',
      overflow: 'hidden',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      boxShadow: dark ? '0 2px 6px rgba(0,0,0,0.35), 0 6px 16px rgba(0,0,0,0.2)' : '0 1px 3px rgba(0,0,0,0.07), 0 3px 10px rgba(0,0,0,0.06)',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      borderRadius: 9999,
      backdropFilter: 'blur(12px) saturate(180%)',
      WebkitBackdropFilter: 'blur(12px) saturate(180%)',
      background: dark ? 'rgba(120,120,128,0.28)' : 'rgba(255,255,255,0.5)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      borderRadius: 9999,
      boxShadow: dark ? 'inset 1.5px 1.5px 1px rgba(255,255,255,0.15), inset -1px -1px 1px rgba(255,255,255,0.08)' : 'inset 1.5px 1.5px 1px rgba(255,255,255,0.7), inset -1px -1px 1px rgba(255,255,255,0.4)',
      border: dark ? '0.5px solid rgba(255,255,255,0.15)' : '0.5px solid rgba(0,0,0,0.06)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      zIndex: 1,
      display: 'flex',
      alignItems: 'center',
      padding: '0 4px'
    }
  }, children));
}

// ─────────────────────────────────────────────────────────────
// Navigation bar — glass pills + large title
// ─────────────────────────────────────────────────────────────
function IOSNavBar({
  title = 'Title',
  dark = false,
  trailingIcon = true
}) {
  const muted = dark ? 'rgba(255,255,255,0.6)' : '#404040';
  const text = dark ? '#fff' : '#000';
  const pillIcon = content => /*#__PURE__*/React.createElement(IOSGlassPill, {
    dark: dark
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 36,
      height: 36,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }
  }, content));
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      paddingTop: 62,
      paddingBottom: 10,
      position: 'relative',
      zIndex: 5
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 16px'
    }
  }, pillIcon(/*#__PURE__*/React.createElement("svg", {
    width: "12",
    height: "20",
    viewBox: "0 0 12 20",
    fill: "none",
    style: {
      marginLeft: -1
    }
  }, /*#__PURE__*/React.createElement("path", {
    d: "M10 2L2 10l8 8",
    stroke: muted,
    strokeWidth: "2.5",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }))), trailingIcon && pillIcon(/*#__PURE__*/React.createElement("svg", {
    width: "22",
    height: "6",
    viewBox: "0 0 22 6"
  }, /*#__PURE__*/React.createElement("circle", {
    cx: "3",
    cy: "3",
    r: "2.5",
    fill: muted
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "11",
    cy: "3",
    r: "2.5",
    fill: muted
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "19",
    cy: "3",
    r: "2.5",
    fill: muted
  })))), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '0 16px',
      fontFamily: '-apple-system, system-ui',
      fontSize: 34,
      fontWeight: 700,
      lineHeight: '41px',
      color: text,
      letterSpacing: 0.4
    }
  }, title));
}

// ─────────────────────────────────────────────────────────────
// Grouped list (inset card, r:26) + row (52px)
// ─────────────────────────────────────────────────────────────
function IOSListRow({
  title,
  detail,
  icon,
  chevron = true,
  isLast = false,
  dark = false
}) {
  const text = dark ? '#fff' : '#000';
  const sec = dark ? 'rgba(235,235,245,0.6)' : 'rgba(60,60,67,0.6)';
  const ter = dark ? 'rgba(235,235,245,0.3)' : 'rgba(60,60,67,0.3)';
  const sep = dark ? 'rgba(84,84,88,0.65)' : 'rgba(60,60,67,0.12)';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      minHeight: 52,
      padding: '0 16px',
      position: 'relative',
      fontFamily: '-apple-system, system-ui',
      fontSize: 17,
      letterSpacing: -0.43
    }
  }, icon && /*#__PURE__*/React.createElement("div", {
    style: {
      width: 30,
      height: 30,
      borderRadius: 7,
      background: icon,
      marginRight: 12,
      flexShrink: 0
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      color: text
    }
  }, title), detail && /*#__PURE__*/React.createElement("span", {
    style: {
      color: sec,
      marginRight: 6
    }
  }, detail), chevron && /*#__PURE__*/React.createElement("svg", {
    width: "8",
    height: "14",
    viewBox: "0 0 8 14",
    style: {
      flexShrink: 0
    }
  }, /*#__PURE__*/React.createElement("path", {
    d: "M1 1l6 6-6 6",
    stroke: ter,
    strokeWidth: "2",
    fill: "none",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  })), !isLast && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      bottom: 0,
      right: 0,
      left: icon ? 58 : 16,
      height: 0.5,
      background: sep
    }
  }));
}
function IOSList({
  header,
  children,
  dark = false
}) {
  const hc = dark ? 'rgba(235,235,245,0.6)' : 'rgba(60,60,67,0.6)';
  const bg = dark ? '#1C1C1E' : '#fff';
  return /*#__PURE__*/React.createElement("div", null, header && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: '-apple-system, system-ui',
      fontSize: 13,
      color: hc,
      textTransform: 'uppercase',
      padding: '8px 36px 6px',
      letterSpacing: -0.08
    }
  }, header), /*#__PURE__*/React.createElement("div", {
    style: {
      background: bg,
      borderRadius: 26,
      margin: '0 16px',
      overflow: 'hidden'
    }
  }, children));
}

// ─────────────────────────────────────────────────────────────
// Device frame
// ─────────────────────────────────────────────────────────────
function IOSDevice({
  children,
  width = 402,
  height = 874,
  dark = false,
  title,
  keyboard = false
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      width,
      height,
      borderRadius: 48,
      overflow: 'hidden',
      position: 'relative',
      background: dark ? '#000' : '#F2F2F7',
      boxShadow: '0 40px 80px rgba(0,0,0,0.18), 0 0 0 1px rgba(0,0,0,0.12)',
      fontFamily: '-apple-system, system-ui, sans-serif',
      WebkitFontSmoothing: 'antialiased'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 11,
      left: '50%',
      transform: 'translateX(-50%)',
      width: 126,
      height: 37,
      borderRadius: 24,
      background: '#000',
      zIndex: 50
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      zIndex: 10
    }
  }, /*#__PURE__*/React.createElement(IOSStatusBar, {
    dark: dark
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      height: '100%',
      display: 'flex',
      flexDirection: 'column'
    }
  }, title !== undefined && /*#__PURE__*/React.createElement(IOSNavBar, {
    title: title,
    dark: dark
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      overflow: 'auto'
    }
  }, children), keyboard && /*#__PURE__*/React.createElement(IOSKeyboard, {
    dark: dark
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      bottom: 0,
      left: 0,
      right: 0,
      zIndex: 60,
      height: 34,
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'flex-end',
      paddingBottom: 8,
      pointerEvents: 'none'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 139,
      height: 5,
      borderRadius: 100,
      background: dark ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.25)'
    }
  })));
}

// ─────────────────────────────────────────────────────────────
// Keyboard — iOS 26 liquid glass
// ─────────────────────────────────────────────────────────────
function IOSKeyboard({
  dark = false
}) {
  const glyph = dark ? 'rgba(255,255,255,0.7)' : '#595959';
  const sugg = dark ? 'rgba(255,255,255,0.6)' : '#333';
  const keyBg = dark ? 'rgba(255,255,255,0.22)' : 'rgba(255,255,255,0.85)';

  // special-key icons
  const icons = {
    shift: /*#__PURE__*/React.createElement("svg", {
      width: "19",
      height: "17",
      viewBox: "0 0 19 17"
    }, /*#__PURE__*/React.createElement("path", {
      d: "M9.5 1L1 9.5h4.5V16h8V9.5H18L9.5 1z",
      fill: glyph
    })),
    del: /*#__PURE__*/React.createElement("svg", {
      width: "23",
      height: "17",
      viewBox: "0 0 23 17"
    }, /*#__PURE__*/React.createElement("path", {
      d: "M7 1h13a2 2 0 012 2v11a2 2 0 01-2 2H7l-6-7.5L7 1z",
      fill: "none",
      stroke: glyph,
      strokeWidth: "1.6",
      strokeLinejoin: "round"
    }), /*#__PURE__*/React.createElement("path", {
      d: "M10 5l7 7M17 5l-7 7",
      stroke: glyph,
      strokeWidth: "1.6",
      strokeLinecap: "round"
    })),
    ret: /*#__PURE__*/React.createElement("svg", {
      width: "20",
      height: "14",
      viewBox: "0 0 20 14"
    }, /*#__PURE__*/React.createElement("path", {
      d: "M18 1v6H4m0 0l4-4M4 7l4 4",
      fill: "none",
      stroke: "#fff",
      strokeWidth: "1.8",
      strokeLinecap: "round",
      strokeLinejoin: "round"
    }))
  };
  const key = (content, {
    w,
    flex,
    ret,
    fs = 25,
    k
  } = {}) => /*#__PURE__*/React.createElement("div", {
    key: k,
    style: {
      height: 42,
      borderRadius: 8.5,
      flex: flex ? 1 : undefined,
      width: w,
      minWidth: 0,
      background: ret ? '#08f' : keyBg,
      boxShadow: '0 1px 0 rgba(0,0,0,0.075)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: '-apple-system, "SF Compact", system-ui',
      fontSize: fs,
      fontWeight: 458,
      color: ret ? '#fff' : glyph
    }
  }, content);
  const row = (keys, pad = 0) => /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 6.5,
      justifyContent: 'center',
      padding: `0 ${pad}px`
    }
  }, keys.map(l => key(l, {
    flex: true,
    k: l
  })));
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      zIndex: 15,
      borderRadius: 27,
      overflow: 'hidden',
      padding: '11px 0 2px',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      boxShadow: dark ? '0 -2px 20px rgba(0,0,0,0.09)' : '0 -1px 6px rgba(0,0,0,0.018), 0 -3px 20px rgba(0,0,0,0.012)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      borderRadius: 27,
      backdropFilter: 'blur(12px) saturate(180%)',
      WebkitBackdropFilter: 'blur(12px) saturate(180%)',
      background: dark ? 'rgba(120,120,128,0.14)' : 'rgba(255,255,255,0.25)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      borderRadius: 27,
      boxShadow: dark ? 'inset 1.5px 1.5px 1px rgba(255,255,255,0.15)' : 'inset 1.5px 1.5px 1px rgba(255,255,255,0.7), inset -1px -1px 1px rgba(255,255,255,0.4)',
      border: dark ? '0.5px solid rgba(255,255,255,0.15)' : '0.5px solid rgba(0,0,0,0.06)',
      pointerEvents: 'none'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 20,
      alignItems: 'center',
      padding: '8px 22px 13px',
      width: '100%',
      boxSizing: 'border-box',
      position: 'relative'
    }
  }, ['"The"', 'the', 'to'].map((w, i) => /*#__PURE__*/React.createElement(React.Fragment, {
    key: i
  }, i > 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      width: 1,
      height: 25,
      background: '#ccc',
      opacity: 0.3
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      textAlign: 'center',
      fontFamily: '-apple-system, system-ui',
      fontSize: 17,
      color: sugg,
      letterSpacing: -0.43,
      lineHeight: '22px'
    }
  }, w)))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 13,
      padding: '0 6.5px',
      width: '100%',
      boxSizing: 'border-box',
      position: 'relative'
    }
  }, row(['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p']), row(['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'], 20), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 14.25,
      alignItems: 'center'
    }
  }, key(icons.shift, {
    w: 45,
    k: 'shift'
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 6.5,
      flex: 1
    }
  }, ['z', 'x', 'c', 'v', 'b', 'n', 'm'].map(l => key(l, {
    flex: true,
    k: l
  }))), key(icons.del, {
    w: 45,
    k: 'del'
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 6,
      alignItems: 'center'
    }
  }, key('ABC', {
    w: 92.25,
    fs: 18,
    k: 'abc'
  }), key('', {
    flex: true,
    k: 'space'
  }), key(icons.ret, {
    w: 92.25,
    ret: true,
    k: 'ret'
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      height: 56,
      width: '100%',
      position: 'relative'
    }
  }));
}
Object.assign(window, {
  IOSDevice,
  IOSStatusBar,
  IOSNavBar,
  IOSGlassPill,
  IOSList,
  IOSListRow,
  IOSKeyboard
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/ios-frame.jsx", error: String((e && e.message) || e) }); }

// ui_kits/web/web.jsx
try { (() => {
/* Визиторкрут — Web (marketing) UI kit. Reads window.DesignSystem_ee81bc.
   Landing page for vizitorkrut.ru. Layout classes (.w-*) live in index.html. */
(function () {
  const DS = window.DesignSystem_ee81bc;
  const {
    Button,
    Icon,
    Card,
    Verdict,
    Metric,
    Badge,
    Tag
  } = DS;
  const AUDIENCES = [{
    icon: 'stethoscope',
    label: 'Врачам',
    text: 'Вызов на дом окупит дорогу — или лучше остаться на приёме.'
  }, {
    icon: 'car-front',
    label: 'Таксистам',
    text: 'Видно, где тариф съест бензин и пробки, ещё до подачи.'
  }, {
    icon: 'package',
    label: 'Курьерам',
    text: 'Пачка заказов по пути или один невыгодный крюк — сразу понятно.'
  }, {
    icon: 'wrench',
    label: 'Мастерам',
    text: 'Далёкий вызов за копейки отсекается до того, как ты выехал.'
  }];
  const STEPS = [{
    icon: 'inbox',
    n: '01',
    h: 'Приходит заказ',
    t: 'Адрес, оплата, расстояние — как везде.'
  }, {
    icon: 'gauge',
    n: '02',
    h: 'Считаем вердикт',
    t: 'Минус бензин, износ и время в пути — по твоим настройкам.'
  }, {
    icon: 'navigation',
    n: '03',
    h: 'Ты решаешь',
    t: 'Стоит — берёшь. Не стоит — ждёшь следующий. Без догадок.'
  }];
  function Phone() {
    const Row = ({
      prof,
      icon,
      level,
      title,
      pay,
      per
    }) => /*#__PURE__*/React.createElement(Card, {
      padding: "sm",
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 7
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        fontSize: 12,
        fontWeight: 600,
        color: 'var(--text-secondary)'
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: icon,
      size: 14
    }), " ", prof), /*#__PURE__*/React.createElement(Verdict, {
      level: level,
      size: "sm"
    })), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 14,
        fontWeight: 700
      }
    }, title), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: 16,
        borderTop: '1px solid var(--border-subtle)',
        paddingTop: 6
      }
    }, /*#__PURE__*/React.createElement(Metric, {
      label: "\u041E\u043F\u043B\u0430\u0442\u0430",
      value: pay,
      unit: "\u20BD",
      tone: "brand",
      size: "sm"
    }), /*#__PURE__*/React.createElement(Metric, {
      label: "\u0427\u0438\u0441\u0442\u044B\u043C\u0438/\u0447",
      value: '₽' + per,
      tone: level === 'skip' ? 'skip' : 'go',
      size: "sm"
    })));
    return /*#__PURE__*/React.createElement("div", {
      className: "w-phone"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-phone-top"
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: '.08em',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)'
      }
    }, "\u041B\u0435\u043D\u0442\u0430 \xB7 3 \u0441\u0442\u043E\u044F\u0449\u0438\u0445"), /*#__PURE__*/React.createElement(Badge, {
      variant: "success",
      dot: true,
      size: "sm"
    }, "\u041D\u0430 \u0441\u043C\u0435\u043D\u0435")), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 10
      }
    }, /*#__PURE__*/React.createElement(Row, {
      prof: "\u0412\u0440\u0430\u0447",
      icon: "stethoscope",
      level: "go",
      title: "\u0412\u044B\u0437\u043E\u0432 \u043D\u0430 \u0434\u043E\u043C \xB7 \u041F\u0440\u0435\u0441\u043D\u044F",
      pay: "3 200",
      per: "980"
    }), /*#__PURE__*/React.createElement(Row, {
      prof: "\u0422\u0430\u043A\u0441\u0438",
      icon: "car-front",
      level: "go",
      title: "\u0414\u043E \u0428\u0435\u0440\u0435\u043C\u0435\u0442\u044C\u0435\u0432\u043E",
      pay: "2 480",
      per: "640"
    }), /*#__PURE__*/React.createElement(Row, {
      prof: "\u041C\u0430\u0441\u0442\u0435\u0440",
      icon: "wrench",
      level: "skip",
      title: "\u0421\u0431\u043E\u0440\u043A\u0430 \xB7 \u0411\u0443\u0442\u043E\u0432\u043E",
      pay: "1 500",
      per: "280"
    })));
  }
  function App() {
    return /*#__PURE__*/React.createElement("div", {
      className: "w-page"
    }, /*#__PURE__*/React.createElement("header", {
      className: "w-nav"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-container w-nav-inner"
    }, /*#__PURE__*/React.createElement("span", {
      className: "w-wordmark"
    }, "\u0412\u0438\u0437\u0438\u0442\u043E\u0440\u043A\u0440\u0443\u0442"), /*#__PURE__*/React.createElement("nav", {
      className: "w-nav-links"
    }, /*#__PURE__*/React.createElement("a", {
      href: "#audience"
    }, "\u0414\u043B\u044F \u043A\u043E\u0433\u043E"), /*#__PURE__*/React.createElement("a", {
      href: "#how"
    }, "\u041A\u0430\u043A \u0440\u0430\u0431\u043E\u0442\u0430\u0435\u0442"), /*#__PURE__*/React.createElement("a", {
      href: "#calc"
    }, "\u0420\u0430\u0441\u0447\u0451\u0442")), /*#__PURE__*/React.createElement("div", {
      className: "w-nav-cta"
    }, /*#__PURE__*/React.createElement(Button, {
      variant: "ghost",
      size: "sm"
    }, "\u0412\u043E\u0439\u0442\u0438"), /*#__PURE__*/React.createElement(Button, {
      variant: "primary",
      size: "sm",
      iconLeft: /*#__PURE__*/React.createElement(Icon, {
        name: "download",
        size: 16
      })
    }, "\u0421\u043A\u0430\u0447\u0430\u0442\u044C")))), /*#__PURE__*/React.createElement("section", {
      className: "w-hero"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-container w-hero-grid"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-hero-copy"
    }, /*#__PURE__*/React.createElement("span", {
      className: "w-eyebrow"
    }, "\u041F\u0440\u0438\u043B\u043E\u0436\u0435\u043D\u0438\u0435 \u0434\u043B\u044F \u0432\u044B\u0435\u0437\u0434\u043D\u044B\u0445 \u0440\u0430\u0431\u043E\u0442\u043D\u0438\u043A\u043E\u0432"), /*#__PURE__*/React.createElement("h1", {
      className: "w-h1"
    }, "\u0421\u0442\u043E\u0438\u0442 \u043B\u0438 \u0432\u043E\u043E\u0431\u0449\u0435", /*#__PURE__*/React.createElement("br", null), /*#__PURE__*/React.createElement("span", {
      className: "w-accent"
    }, "\u0442\u0443\u0434\u0430 \u0435\u0445\u0430\u0442\u044C?")), /*#__PURE__*/React.createElement("p", {
      className: "w-lead"
    }, "\u041D\u0430\u0432\u0438\u0433\u0430\u0442\u043E\u0440 \u043F\u043E\u043A\u0430\u0437\u044B\u0432\u0430\u0435\u0442, \u043A\u0443\u0434\u0430 \u0435\u0445\u0430\u0442\u044C. \u0412\u0438\u0437\u0438\u0442\u043E\u0440\u043A\u0440\u0443\u0442 \u043F\u043E\u043A\u0430\u0437\u044B\u0432\u0430\u0435\u0442 \u2014 ", /*#__PURE__*/React.createElement("b", null, "\u0441\u0442\u043E\u0438\u0442 \u043B\u0438"), ". \u0421\u0447\u0438\u0442\u0430\u0435\u043C \u0442\u0432\u043E\u0439 \u0447\u0435\u0441\u0442\u043D\u044B\u0439 \u0437\u0430\u0440\u0430\u0431\u043E\u0442\u043E\u043A \u0437\u0430 \u0447\u0430\u0441 \u0441 \u0443\u0447\u0451\u0442\u043E\u043C \u0431\u0435\u043D\u0437\u0438\u043D\u0430, \u0438\u0437\u043D\u043E\u0441\u0430 \u0438 \u043F\u0440\u043E\u0431\u043E\u043A \u2014 \u0434\u043E \u0442\u043E\u0433\u043E, \u043A\u0430\u043A \u0442\u044B \u0432\u043E\u0437\u044C\u043C\u0451\u0448\u044C \u0437\u0430\u043A\u0430\u0437."), /*#__PURE__*/React.createElement("div", {
      className: "w-cta-row"
    }, /*#__PURE__*/React.createElement(Button, {
      variant: "primary",
      size: "lg",
      iconLeft: /*#__PURE__*/React.createElement(Icon, {
        name: "smartphone",
        size: 20
      })
    }, "\u0421\u043A\u0430\u0447\u0430\u0442\u044C \u0431\u0435\u0441\u043F\u043B\u0430\u0442\u043D\u043E"), /*#__PURE__*/React.createElement(Button, {
      variant: "secondary",
      size: "lg",
      iconRight: /*#__PURE__*/React.createElement(Icon, {
        name: "play",
        size: 18
      })
    }, "\u041A\u0430\u043A \u044D\u0442\u043E \u0440\u0430\u0431\u043E\u0442\u0430\u0435\u0442")), /*#__PURE__*/React.createElement("div", {
      className: "w-hero-note"
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "shield-check",
      size: 16
    }), " \u0411\u0435\u0441\u043F\u043B\u0430\u0442\u043D\u043E \xB7 \u0431\u0435\u0437 \u043F\u0440\u0438\u0432\u044F\u0437\u043A\u0438 \u043A \u0430\u0433\u0440\u0435\u0433\u0430\u0442\u043E\u0440\u0443")), /*#__PURE__*/React.createElement("div", {
      className: "w-hero-visual"
    }, /*#__PURE__*/React.createElement(Phone, null)))), /*#__PURE__*/React.createElement("section", {
      className: "w-section",
      id: "audience"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-container"
    }, /*#__PURE__*/React.createElement("span", {
      className: "w-eyebrow w-center"
    }, "\u0414\u043B\u044F \u043A\u043E\u0433\u043E"), /*#__PURE__*/React.createElement("h2", {
      className: "w-h2 w-center"
    }, "\u041E\u0434\u0438\u043D \u0432\u044B\u0435\u0437\u0434 \u2014 \u043E\u0434\u043D\u043E \u0440\u0435\u0448\u0435\u043D\u0438\u0435.", /*#__PURE__*/React.createElement("br", null), "\u0414\u043B\u044F \u0432\u0441\u0435\u0445, \u043A\u0442\u043E \u0437\u0430\u0440\u0430\u0431\u0430\u0442\u044B\u0432\u0430\u0435\u0442 \u0432 \u0434\u043E\u0440\u043E\u0433\u0435."), /*#__PURE__*/React.createElement("div", {
      className: "w-aud-grid"
    }, AUDIENCES.map(a => /*#__PURE__*/React.createElement(Card, {
      key: a.label,
      padding: "lg",
      className: "w-aud-card"
    }, /*#__PURE__*/React.createElement("span", {
      className: "w-aud-ico"
    }, /*#__PURE__*/React.createElement(Icon, {
      name: a.icon,
      size: 26,
      strokeWidth: 1.9
    })), /*#__PURE__*/React.createElement("h3", {
      className: "w-aud-h"
    }, a.label), /*#__PURE__*/React.createElement("p", {
      className: "w-aud-t"
    }, a.text)))))), /*#__PURE__*/React.createElement("section", {
      className: "w-section w-section-sunken",
      id: "how"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-container"
    }, /*#__PURE__*/React.createElement("span", {
      className: "w-eyebrow w-center"
    }, "\u041A\u0430\u043A \u0440\u0430\u0431\u043E\u0442\u0430\u0435\u0442"), /*#__PURE__*/React.createElement("h2", {
      className: "w-h2 w-center"
    }, "\u0422\u0440\u0438 \u0441\u0435\u043A\u0443\u043D\u0434\u044B \u043D\u0430 \u0440\u0435\u0448\u0435\u043D\u0438\u0435"), /*#__PURE__*/React.createElement("div", {
      className: "w-steps"
    }, STEPS.map(s => /*#__PURE__*/React.createElement("div", {
      key: s.n,
      className: "w-step"
    }, /*#__PURE__*/React.createElement("span", {
      className: "w-step-ico"
    }, /*#__PURE__*/React.createElement(Icon, {
      name: s.icon,
      size: 26,
      strokeWidth: 1.9
    })), /*#__PURE__*/React.createElement("span", {
      className: "w-step-n"
    }, s.n), /*#__PURE__*/React.createElement("h3", {
      className: "w-step-h"
    }, s.h), /*#__PURE__*/React.createElement("p", {
      className: "w-step-t"
    }, s.t)))))), /*#__PURE__*/React.createElement("section", {
      className: "w-section",
      id: "calc"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-container w-feature"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-feature-copy"
    }, /*#__PURE__*/React.createElement("span", {
      className: "w-eyebrow"
    }, "\u0427\u0435\u0441\u0442\u043D\u044B\u0439 \u20BD \u0432 \u0447\u0430\u0441"), /*#__PURE__*/React.createElement("h2", {
      className: "w-h2"
    }, "\u041C\u044B \u0432\u044B\u0447\u0438\u0442\u0430\u0435\u043C \u0442\u043E,", /*#__PURE__*/React.createElement("br", null), "\u0447\u0442\u043E \u043F\u0440\u044F\u0447\u0443\u0442 \u0430\u0433\u0440\u0435\u0433\u0430\u0442\u043E\u0440\u044B"), /*#__PURE__*/React.createElement("p", {
      className: "w-lead"
    }, "\u041E\u043F\u043B\u0430\u0442\u0430 \u0437\u0430 \u0437\u0430\u043A\u0430\u0437 \u2014 \u044D\u0442\u043E \u043D\u0435 \u0442\u043E, \u0447\u0442\u043E \u0442\u044B \u0437\u0430\u0440\u0430\u0431\u043E\u0442\u0430\u0435\u0448\u044C. \u041C\u044B \u043E\u0442\u043D\u0438\u043C\u0430\u0435\u043C \u0431\u0435\u043D\u0437\u0438\u043D \u043F\u043E \u0442\u0432\u043E\u0435\u0439 \u0446\u0435\u043D\u0435, \u0438\u0437\u043D\u043E\u0441 \u043C\u0430\u0448\u0438\u043D\u044B \u0438 \u0432\u0440\u0435\u043C\u044F \u0432 \u043F\u0443\u0442\u0438 \u0441 \u043F\u0440\u043E\u0431\u043A\u0430\u043C\u0438. \u041E\u0441\u0442\u0430\u0451\u0442\u0441\u044F \u0447\u0435\u0441\u0442\u043D\u0430\u044F \u0446\u0438\u0444\u0440\u0430 \u2014 \u0441\u043A\u043E\u043B\u044C\u043A\u043E \u0440\u0435\u0430\u043B\u044C\u043D\u043E \u0443\u043F\u0430\u0434\u0451\u0442 \u0432 \u043A\u0430\u0440\u043C\u0430\u043D \u0437\u0430 \u0447\u0430\u0441."), /*#__PURE__*/React.createElement("ul", {
      className: "w-list"
    }, /*#__PURE__*/React.createElement("li", null, /*#__PURE__*/React.createElement(Icon, {
      name: "check",
      size: 18
    }), " \u0422\u0432\u043E\u044F \u0446\u0435\u043D\u0430 \u0431\u0435\u043D\u0437\u0438\u043D\u0430 \u0438 \u0440\u0430\u0441\u0445\u043E\u0434"), /*#__PURE__*/React.createElement("li", null, /*#__PURE__*/React.createElement(Icon, {
      name: "check",
      size: 18
    }), " \u041F\u0440\u043E\u0431\u043A\u0438 \u0432 \u0440\u0435\u0430\u043B\u044C\u043D\u043E\u043C \u0432\u0440\u0435\u043C\u0435\u043D\u0438"), /*#__PURE__*/React.createElement("li", null, /*#__PURE__*/React.createElement(Icon, {
      name: "check",
      size: 18
    }), " \u041F\u043E\u0440\u043E\u0433 \xAB\u0441\u0442\u043E\u0438\u0442 / \u043D\u0435 \u0441\u0442\u043E\u0438\u0442\xBB \u043F\u043E\u0434 \u0442\u0435\u0431\u044F"))), /*#__PURE__*/React.createElement(Card, {
      variant: "raised",
      padding: "lg",
      className: "w-breakdown"
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 4
      }
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 17,
        fontWeight: 700
      }
    }, "\u0414\u043E \u0428\u0435\u0440\u0435\u043C\u0435\u0442\u044C\u0435\u0432\u043E"), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 13,
        color: 'var(--text-secondary)'
      }
    }, "\u0422\u0432\u0435\u0440\u0441\u043A\u0430\u044F, 12 \u2192 SVO \xB7 38 \u043A\u043C")), /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        fontSize: 13,
        fontWeight: 600,
        color: 'var(--text-secondary)'
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "car-front",
      size: 16
    }), " \u0422\u0430\u043A\u0441\u0438")), [['Тариф', '+2 480'], ['Бензин 38 км', '−420'], ['Время в пути 44 мин', '−410']].map(([k, v], i) => /*#__PURE__*/React.createElement("div", {
      key: i,
      className: "w-brk-row"
    }, /*#__PURE__*/React.createElement("span", null, k), /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'var(--font-mono)',
        fontWeight: 600,
        color: v[0] === '+' ? 'var(--verdict-go-text)' : 'var(--verdict-skip-text)'
      }
    }, v, " \u20BD"))), /*#__PURE__*/React.createElement("div", {
      className: "w-brk-total"
    }, /*#__PURE__*/React.createElement("span", null, "\u0427\u0438\u0441\u0442\u044B\u043C\u0438 \u0432 \u0447\u0430\u0441"), /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'var(--font-mono)',
        fontWeight: 600,
        fontSize: 26,
        color: 'var(--brand)'
      }
    }, "\u20BD640")), /*#__PURE__*/React.createElement(Verdict, {
      level: "go",
      reason: "\u0412\u044B\u0448\u0435 \u0442\u0432\u043E\u0435\u0439 \u043D\u043E\u0440\u043C\u044B \u20BD500/\u0447 \u2014 \u0431\u0435\u0440\u0438."
    })))), /*#__PURE__*/React.createElement("section", {
      className: "w-stats-band"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-container w-stats"
    }, [['1,2 млн', 'выездов оценено'], ['+34%', 'к среднему ₽/ч у водителей'], ['48', 'городов России']].map(([v, l], i) => /*#__PURE__*/React.createElement("div", {
      key: i,
      className: "w-stat"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-stat-v"
    }, v), /*#__PURE__*/React.createElement("div", {
      className: "w-stat-l"
    }, l))))), /*#__PURE__*/React.createElement("section", {
      className: "w-ctaband"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-container w-cta-inner"
    }, /*#__PURE__*/React.createElement("h2", {
      className: "w-cta-h"
    }, "\u0425\u0432\u0430\u0442\u0438\u0442 \u0435\u0437\u0434\u0438\u0442\u044C \u0432\u043F\u0443\u0441\u0442\u0443\u044E"), /*#__PURE__*/React.createElement("p", {
      className: "w-cta-sub"
    }, "\u041F\u043E\u0441\u0442\u0430\u0432\u044C \u043F\u0440\u0438\u043B\u043E\u0436\u0435\u043D\u0438\u0435 \u0438 \u043F\u043E\u0441\u043C\u043E\u0442\u0440\u0438 \u043F\u0435\u0440\u0432\u044B\u0439 \u0432\u0435\u0440\u0434\u0438\u043A\u0442 \u0437\u0430 \u043C\u0438\u043D\u0443\u0442\u0443."), /*#__PURE__*/React.createElement("div", {
      className: "w-cta-row"
    }, /*#__PURE__*/React.createElement(Button, {
      variant: "primary",
      size: "xl",
      iconLeft: /*#__PURE__*/React.createElement(Icon, {
        name: "download",
        size: 20
      })
    }, "\u0421\u043A\u0430\u0447\u0430\u0442\u044C \u0412\u0438\u0437\u0438\u0442\u043E\u0440\u043A\u0440\u0443\u0442")))), /*#__PURE__*/React.createElement("footer", {
      className: "w-footer"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-container w-foot-grid"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", {
      className: "w-wordmark w-wordmark-inv"
    }, "\u0412\u0438\u0437\u0438\u0442\u043E\u0440\u043A\u0440\u0443\u0442"), /*#__PURE__*/React.createElement("p", {
      className: "w-foot-tag"
    }, "\u041D\u0430\u0432\u0438\u0433\u0430\u0442\u043E\u0440 \u043F\u043E\u043A\u0430\u0437\u044B\u0432\u0430\u0435\u0442, \u043A\u0443\u0434\u0430 \u0435\u0445\u0430\u0442\u044C.", /*#__PURE__*/React.createElement("br", null), "\u041C\u044B \u2014 \u0441\u0442\u043E\u0438\u0442 \u043B\u0438.")), /*#__PURE__*/React.createElement("div", {
      className: "w-foot-col"
    }, /*#__PURE__*/React.createElement("h4", null, "\u041F\u0440\u043E\u0434\u0443\u043A\u0442"), /*#__PURE__*/React.createElement("a", {
      href: "#how"
    }, "\u041A\u0430\u043A \u0440\u0430\u0431\u043E\u0442\u0430\u0435\u0442"), /*#__PURE__*/React.createElement("a", {
      href: "#calc"
    }, "\u0420\u0430\u0441\u0447\u0451\u0442 \u20BD/\u0447"), /*#__PURE__*/React.createElement("a", {
      href: "#audience"
    }, "\u0414\u043B\u044F \u043A\u043E\u0433\u043E")), /*#__PURE__*/React.createElement("div", {
      className: "w-foot-col"
    }, /*#__PURE__*/React.createElement("h4", null, "\u041A\u043E\u043C\u043F\u0430\u043D\u0438\u044F"), /*#__PURE__*/React.createElement("a", {
      href: "#"
    }, "\u041E \u043D\u0430\u0441"), /*#__PURE__*/React.createElement("a", {
      href: "#"
    }, "\u0411\u043B\u043E\u0433"), /*#__PURE__*/React.createElement("a", {
      href: "#"
    }, "\u0412\u0430\u043A\u0430\u043D\u0441\u0438\u0438")), /*#__PURE__*/React.createElement("div", {
      className: "w-foot-col"
    }, /*#__PURE__*/React.createElement("h4", null, "\u041F\u043E\u043C\u043E\u0449\u044C"), /*#__PURE__*/React.createElement("a", {
      href: "#"
    }, "\u041F\u043E\u0434\u0434\u0435\u0440\u0436\u043A\u0430"), /*#__PURE__*/React.createElement("a", {
      href: "#"
    }, "\u0414\u043E\u0433\u043E\u0432\u043E\u0440"), /*#__PURE__*/React.createElement("a", {
      href: "#"
    }, "vizitorkrut.ru"))), /*#__PURE__*/React.createElement("div", {
      className: "w-container w-foot-legal"
    }, /*#__PURE__*/React.createElement("span", null, "\xA9 2026 \u0412\u0438\u0437\u0438\u0442\u043E\u0440\u043A\u0440\u0443\u0442"), /*#__PURE__*/React.createElement("span", null, "\u0421\u0434\u0435\u043B\u0430\u043D\u043E \u0434\u043B\u044F \u0442\u0435\u0445, \u043A\u0442\u043E \u0432 \u0434\u043E\u0440\u043E\u0433\u0435"))));
  }
  window.VKWeb = App;
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/web/web.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Button = __ds_scope.Button;

__ds_ns.IconButton = __ds_scope.IconButton;

__ds_ns.Checkbox = __ds_scope.Checkbox;

__ds_ns.Radio = __ds_scope.Radio;

__ds_ns.Switch = __ds_scope.Switch;

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Tag = __ds_scope.Tag;

__ds_ns.Toast = __ds_scope.Toast;

__ds_ns.Tooltip = __ds_scope.Tooltip;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.Select = __ds_scope.Select;

__ds_ns.Textarea = __ds_scope.Textarea;

__ds_ns.Icon = __ds_scope.Icon;

__ds_ns.Tabs = __ds_scope.Tabs;

__ds_ns.Card = __ds_scope.Card;

__ds_ns.Metric = __ds_scope.Metric;

__ds_ns.Verdict = __ds_scope.Verdict;

})();
