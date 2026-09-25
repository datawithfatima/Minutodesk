const VARIANTES = {
  primary: "bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300",
  dark: "bg-slate-800 text-white hover:bg-slate-900 disabled:bg-slate-400",
  secondary: "bg-gray-600 text-white hover:bg-gray-700 disabled:bg-gray-300",
  outlineSecondary:
    "border border-gray-400 text-gray-700 hover:bg-gray-100 disabled:opacity-50",
  outlinePrimary:
    "border border-blue-600 text-blue-600 hover:bg-blue-50 disabled:opacity-50",
  outlineSuccess:
    "border border-green-600 text-green-700 hover:bg-green-50 disabled:opacity-50",
};

export default function Button({
  variant = "primary",
  size = "md",
  className = "",
  ...props
}) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors disabled:cursor-not-allowed";
  const sizeCls = size === "sm" ? "px-3 py-1.5 text-sm" : "px-4 py-2 text-sm";
  return (
    <button
      className={`${base} ${sizeCls} ${VARIANTES[variant] || VARIANTES.primary} ${className}`}
      {...props}
    />
  );
}
