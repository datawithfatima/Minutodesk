import { AlertCircle, AlertTriangle, CheckCircle2, Info } from "lucide-react";

// Cada aviso lleva icono además del color: el estado nunca depende solo del color.
const VARIANTES = {
  danger: { cls: "bg-red-50 text-red-800 border-red-200", Icono: AlertCircle },
  success: { cls: "bg-green-50 text-green-800 border-green-200", Icono: CheckCircle2 },
  secondary: { cls: "bg-white text-gray-600 border-linea", Icono: Info },
  info: { cls: "bg-acento-50 text-noche border-acento-100", Icono: Info },
  warning: { cls: "bg-amber-50 text-amber-900 border-amber-200", Icono: AlertTriangle },
};

export default function Alert({ variant = "secondary", children, className = "" }) {
  const { cls, Icono } = VARIANTES[variant] || VARIANTES.secondary;
  return (
    <div
      role={variant === "danger" ? "alert" : "status"}
      className={`flex items-start gap-2.5 rounded-xl border px-4 py-3 text-sm ${cls} ${className}`}
    >
      <Icono size={17} className="mt-px shrink-0 opacity-80" aria-hidden="true" />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
