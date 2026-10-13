/**
 * Símbolo de MinutoDesk: un ticket con su talón perforado y un punto de acento,
 * la idea de «cada solicitud, en su lugar». Es SVG, así que se ve nítido en cualquier tamaño.
 */
export default function Logo({ size = "h-9 w-9", invertido = false, className = "" }) {
  const fondo = invertido ? "#ffffff" : "#101b30";
  const ticket = invertido ? "#101b30" : "#ffffff";
  return (
    <svg
      viewBox="0 0 32 32"
      className={`${size} shrink-0 ${className}`}
      role="img"
      aria-label="MinutoDesk"
    >
      <rect width="32" height="32" rx="9" fill={fondo} />
      <path
        d="M8 10.5A1.5 1.5 0 0 1 9.5 9h13A1.5 1.5 0 0 1 24 10.5v3.1a2.4 2.4 0 0 0 0 4.8v3.1a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 8 21.5v-3.1a2.4 2.4 0 0 0 0-4.8z"
        fill={ticket}
      />
      <path d="M19 10.6v10.8" stroke={fondo} strokeWidth="1.3" strokeDasharray="1.6 1.7" strokeLinecap="round" />
      <rect x="11.2" y="12.4" width="5" height="1.7" rx=".85" fill="#3458eb" />
      <rect x="11.2" y="15.2" width="4.2" height="1.5" rx=".75" fill={fondo} opacity=".28" />
      <rect x="11.2" y="17.9" width="3.2" height="1.5" rx=".75" fill={fondo} opacity=".28" />
    </svg>
  );
}

/** Símbolo + nombre. `oscuro` para fondos azul noche. */
export function Marca({ oscuro = false, subtitulo = false, size = "h-9 w-9" }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <Logo size={size} invertido={oscuro} />
      <span className="leading-tight">
        <span
          className={`block text-[17px] font-semibold tracking-[-0.02em] ${
            oscuro ? "text-white" : "text-noche"
          }`}
        >
          Minuto<span className={oscuro ? "text-acento-100" : "text-acento"}>Desk</span>
        </span>
        {subtitulo && (
          <span className={`block text-xs ${oscuro ? "text-noche-300" : "text-gray-500"}`}>
            Tu soporte, más cerca
          </span>
        )}
      </span>
    </span>
  );
}
