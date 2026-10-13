const VARIANTES = {
  primary: "bg-acento text-white shadow-sm hover:bg-acento-600 disabled:bg-acento/40",
  dark: "bg-noche text-white shadow-sm hover:bg-noche-700 disabled:bg-noche/40",
  secondary: "bg-gray-600 text-white hover:bg-gray-700 disabled:bg-gray-300",
  outlineSecondary:
    "border border-linea bg-white text-noche hover:border-gray-300 hover:bg-marfil disabled:opacity-50",
  outlinePrimary:
    "border border-acento/40 bg-white text-acento hover:bg-acento-50 disabled:opacity-50",
  outlineSuccess:
    "border border-green-600/50 bg-white text-green-700 hover:bg-green-50 disabled:opacity-50",
  outlineDanger:
    "border border-red-500/50 bg-white text-red-600 hover:bg-red-50 disabled:opacity-50",
};

const TAMANOS = {
  sm: "h-8 px-3 text-sm",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-5 text-[15px]",
};

export default function Button({
  variant = "primary",
  size = "md",
  className = "",
  ...props
}) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors duration-150 disabled:cursor-not-allowed";
  return (
    <button
      className={`${base} ${TAMANOS[size] || TAMANOS.md} ${VARIANTES[variant] || VARIANTES.primary} ${className}`}
      {...props}
    />
  );
}
