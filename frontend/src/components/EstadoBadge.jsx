import { Ban, CheckCircle2, CircleDot, Clock3 } from "lucide-react";
import { ETIQUETA_ESTADO } from "../texto";

// Texto + icono + color: el estado se entiende aunque no se distinga el color.
const ESTADOS = {
  abierto: { Icono: CircleDot, cls: "bg-amber-50 text-amber-800 ring-amber-200" },
  en_proceso: { Icono: Clock3, cls: "bg-acento-50 text-acento-600 ring-acento-100" },
  resuelto: { Icono: CheckCircle2, cls: "bg-green-50 text-green-800 ring-green-200" },
  cancelado: { Icono: Ban, cls: "bg-gray-100 text-gray-600 ring-gray-200" },
};

export default function EstadoBadge({ estado }) {
  const e = ESTADOS[estado] ?? { Icono: CircleDot, cls: "bg-gray-100 text-gray-700 ring-gray-200" };
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${e.cls}`}
    >
      <e.Icono size={12} aria-hidden="true" />
      {ETIQUETA_ESTADO[estado] ?? estado}
    </span>
  );
}
