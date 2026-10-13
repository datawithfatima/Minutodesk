import { COLOR_PRIORIDAD, GRIS_SIN_DATO, hexA } from "../charts/tokens";

export function Pastilla({ texto, color, className = "" }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium text-gray-700 ${className}`}
      style={{ background: hexA(color, 0.14) }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
      {texto}
    </span>
  );
}

// La prioridad usa la misma escala azul (de menor a mayor urgencia) que el dashboard.
export function PrioridadPastilla({ prioridad }) {
  if (!prioridad) return <span className="text-xs text-gray-400">—</span>;
  return <Pastilla texto={prioridad} color={COLOR_PRIORIDAD[prioridad] ?? GRIS_SIN_DATO} />;
}
