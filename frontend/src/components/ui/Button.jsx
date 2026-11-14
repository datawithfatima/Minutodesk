const VARIANTES = {
  primary: "bg-acento text-white shadow-[0_1px_0_rgb(0_0_0/0.15)] hover:bg-acento-600 disabled:bg-acento/40",
  dark: "bg-grafito text-white shadow-[0_1px_0_rgb(0_0_0/0.2)] hover:bg-grafito-700 disabled:bg-grafito/40",
  secondary: "bg-gray-600 text-white hover:bg-gray-700 disabled:bg-gray-300",
  outlineSecondary:
    "border border-linea bg-superficie text-noche hover:border-noche/40 hover:bg-marfil disabled:opacity-50",
  outlinePrimary:
    "border border-acento/40 bg-superficie text-acento hover:border-acento hover:bg-acento-50 disabled:opacity-50",
  outlineSuccess:
    "border border-green-600/50 bg-superficie text-green-700 hover:bg-green-50 disabled:opacity-50",
  outlineDanger:
    "border border-red-500/50 bg-superficie text-red-600 hover:bg-red-50 disabled:opacity-50",
};

const TAMANOS = {
  sm: "h-8 px-3 text-sm",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-5 text-[15px]",
};

/** Botón con el comportamiento «de obra»: se hunde al presionar y muestra una franja de seguridad al pasar. */
export default function Button({
  variant = "primary",
  size = "md",
  className = "",
  ...props
}) {
  const base =
    "btn-obra inline-flex items-center justify-center gap-2 rounded-md font-semibold tracking-[0.005em] disabled:cursor-not-allowed";
  return (
    <button
      className={`${base} ${TAMANOS[size] || TAMANOS.md} ${VARIANTES[variant] || VARIANTES.primary} ${className}`}
      {...props}
    />
  );
}
