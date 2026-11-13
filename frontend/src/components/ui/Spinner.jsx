/**
 * Indicador de carga con motivo de obra.
 * Grande: tres bloques que una grúa va apilando. Pequeño: tres pisos que suben y bajan.
 * Usa el color del texto (currentColor), así que sirve dentro de botones y sobre fondos oscuros.
 */
export default function Spinner({ size = "md", className = "" }) {
  if (size === "sm") {
    return (
      <span
        className={`inline-flex h-4 w-4 items-end justify-center gap-[2px] ${className}`}
        role="status"
        aria-label="Cargando"
      >
        {[0, 150, 300].map((d) => (
          <span
            key={d}
            className="piso-sube block h-full w-[3px] rounded-[1px] bg-current"
            style={{ animationDelay: `${d}ms` }}
          />
        ))}
      </span>
    );
  }
  return (
    <span
      className={`relative inline-block h-9 w-9 ${className}`}
      role="status"
      aria-label="Cargando"
    >
      <svg viewBox="0 0 36 36" className="h-full w-full overflow-visible" aria-hidden="true">
        <line x1="2" y1="34" x2="34" y2="34" stroke="currentColor" strokeWidth="2" opacity=".35" />
        <rect className="bloque-apila" x="5" y="24" width="12" height="9" rx="1" fill="currentColor" />
        <rect
          className="bloque-apila"
          style={{ animationDelay: "0.2s" }}
          x="19"
          y="24"
          width="12"
          height="9"
          rx="1"
          fill="currentColor"
          opacity=".75"
        />
        <rect
          className="bloque-apila"
          style={{ animationDelay: "0.4s" }}
          x="12"
          y="14"
          width="12"
          height="9"
          rx="1"
          fill="#f5b800"
        />
      </svg>
    </span>
  );
}
