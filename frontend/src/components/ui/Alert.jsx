import { AlertCircle, AlertTriangle, CheckCircle2, Info } from "lucide-react";

// Cada aviso lleva icono además del color: el estado nunca depende solo del color.
// Cada tipo tiene su gesto: el éxito se «estampa» como un sello de inspección, el error vibra
// un instante y la advertencia lleva el borde con franja de seguridad.
const VARIANTES = {
  danger: { cls: "bg-red-50 text-red-800 border-red-200 anim-vibrar", Icono: AlertCircle, icono: "" },
  success: { cls: "bg-green-50 text-green-800 border-green-200", Icono: CheckCircle2, icono: "anim-sello" },
  secondary: { cls: "bg-white text-gray-600 border-linea", Icono: Info, icono: "" },
  info: { cls: "bg-acento-50 text-noche border-acento-100", Icono: Info, icono: "" },
  warning: { cls: "bg-amber-50 text-amber-900 border-amber-200", Icono: AlertTriangle, icono: "", franja: true },
};

export default function Alert({ variant = "secondary", children, className = "" }) {
  const { cls, Icono, icono, franja } = VARIANTES[variant] || VARIANTES.secondary;
  return (
    <div
      role={variant === "danger" ? "alert" : "status"}
      className={`relative flex items-start gap-2.5 overflow-hidden rounded-md border px-4 py-3 text-sm ${
        franja ? "pl-5" : ""
      } ${cls} ${className}`}
    >
      {franja && <span aria-hidden="true" className="franja-obra absolute inset-y-0 left-0 w-1.5" />}
      <Icono size={17} className={`mt-px shrink-0 opacity-80 ${icono}`} aria-hidden="true" />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
