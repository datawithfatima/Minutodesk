/**
 * Símbolo de MinutoDesk: una «M» trazada como dos columnas y una viga, con un bloque
 * amarillo recién colocado en su base: cada solicitud, un bloque más de la obra.
 * Es SVG, así que se ve nítido en cualquier tamaño. Al pasar el cursor, el bloque «cae» en su lugar.
 */
export default function Logo({ size = "h-9 w-9", invertido = false, className = "" }) {
  const fondo = invertido ? "#ffffff" : "#1b1e22";
  const trazo = invertido ? "#1b1e22" : "#ffffff";
  return (
    <svg
      viewBox="0 0 32 32"
      className={`group/logo ${size} shrink-0 ${className}`}
      role="img"
      aria-label="MinutoDesk"
    >
      <rect width="32" height="32" rx="6" fill={fondo} />
      <path
        d="M9 23.5V9l7 8.2L23 9v14.5"
        fill="none"
        stroke={trazo}
        strokeWidth="3.2"
        strokeLinecap="square"
        strokeLinejoin="miter"
      />
      <rect
        x="13.6"
        y="20.6"
        width="4.8"
        height="4.8"
        rx=".6"
        fill="#f5b800"
        className="transition-transform duration-300 ease-[cubic-bezier(.34,1.4,.64,1)] group-hover/logo:-translate-y-[3px]"
      />
    </svg>
  );
}

/** Símbolo + nombre. `oscuro` para fondos grafito. */
export function Marca({ oscuro = false, subtitulo = false, size = "h-9 w-9" }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <Logo size={size} invertido={oscuro} />
      <span className="leading-tight">
        <span
          className={`block text-[17px] font-bold tracking-[-0.01em] [font-variation-settings:'wdth'_118] ${
            oscuro ? "text-white" : "text-noche"
          }`}
        >
          Minuto<span className={oscuro ? "text-casco" : "text-acento"}>Desk</span>
        </span>
        {subtitulo && (
          <span
            className={`block font-mono text-[10px] uppercase tracking-[0.14em] ${
              oscuro ? "text-noche-300" : "text-gray-500"
            }`}
          >
            Mesa de ayuda de TI
          </span>
        )}
      </span>
    </span>
  );
}
