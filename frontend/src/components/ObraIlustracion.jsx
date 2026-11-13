/**
 * Ilustración del panel de acceso: el alzado de un edificio que se dibuja solo, como un
 * plano, y una grúa torre que iza un bloque amarillo. Es decorativa (aria-hidden).
 * Todo con trazos SVG: sin imágenes externas y nítido en cualquier pantalla.
 */
const PISOS = [0, 1, 2, 3, 4, 5];

function Trazo({ d, retraso = 0, className = "", ...props }) {
  return (
    <path
      d={d}
      pathLength={1}
      fill="none"
      className={`anim-trazar ${className}`}
      style={{ "--largo": 1, animationDelay: `${retraso}s` }}
      {...props}
    />
  );
}

export default function ObraIlustracion({ className = "" }) {
  return (
    <svg viewBox="0 0 420 280" className={className} aria-hidden="true" fill="none">
      {/* Terreno */}
      <Trazo d="M0 250H420" stroke="rgb(255 255 255 / .35)" strokeWidth="1.5" />
      <path d="M0 256H420" stroke="rgb(255 255 255 / .12)" strokeDasharray="2 6" />

      {/* Torre principal: estructura terminada abajo y pisos en obra arriba */}
      <Trazo d="M70 250V100H190V250" stroke="rgb(255 255 255 / .7)" strokeWidth="1.5" retraso={0.2} />
      {PISOS.map((p) => (
        <Trazo
          key={p}
          d={`M70 ${225 - p * 25}H190`}
          stroke="rgb(255 255 255 / .35)"
          retraso={0.6 + p * 0.12}
        />
      ))}
      {PISOS.slice(0, 4).map((p) =>
        [88, 118, 148].map((x) => (
          <rect
            key={`${p}-${x}`}
            x={x}
            y={232 - p * 25}
            width="16"
            height="11"
            fill="rgb(255 255 255 / .1)"
            stroke="rgb(255 255 255 / .3)"
            className="anim-levantar-ventana"
            style={{ animationDelay: `${1.2 + p * 0.15}s` }}
          />
        ))
      )}
      {/* Pisos en construcción: línea discontinua */}
      <path d="M70 100V62H190V100" stroke="rgb(245 184 0 / .55)" strokeDasharray="4 4" />
      <path d="M100 62V100M130 62V100M160 62V100" stroke="rgb(245 184 0 / .3)" strokeDasharray="4 4" />

      {/* Edificio bajo */}
      <Trazo d="M206 250V160H286V250" stroke="rgb(255 255 255 / .55)" strokeWidth="1.5" retraso={0.5} />
      <Trazo d="M206 190H286M206 220H286" stroke="rgb(255 255 255 / .25)" retraso={1} />

      {/* Cotas */}
      <g stroke="rgb(255 255 255 / .4)" className="anim-aparecer-tarde">
        <path d="M48 100V250M44 100H52M44 250H52" />
        <path d="M70 268H190M70 264V272M190 264V272" />
      </g>
      <g fill="rgb(255 255 255 / .55)" fontFamily="IBM Plex Mono, monospace" fontSize="9" className="anim-aparecer-tarde">
        <text x="40" y="178" transform="rotate(-90 40 178)" textAnchor="middle">
          45,00 m
        </text>
        <text x="130" y="279" textAnchor="middle">
          24,00 m
        </text>
      </g>

      {/* Grúa torre */}
      <g stroke="#f5b800" strokeWidth="1.5">
        <path d="M330 250V44M346 250V44" />
        <path d="M330 250L346 230L330 210L346 190L330 170L346 150L330 130L346 110L330 90L346 70L330 50" strokeWidth="1" />
        <path d="M150 44H404M150 32H346L404 44M338 20V44M338 20L150 32M338 20L404 40" strokeWidth="1.2" />
        <rect x="372" y="44" width="24" height="12" fill="#f5b800" fillOpacity=".25" />
        <rect x="324" y="56" width="28" height="14" fill="#1b1e22" />
        <rect x="324" y="56" width="28" height="14" />
      </g>
      {/* Carro e izado: el carro recorre la pluma y el gancho sube y baja con el bloque */}
      <g style={{ animation: "carro 7s ease-in-out infinite" }}>
        <rect x="246" y="44" width="16" height="6" fill="#f5b800" />
        <path
          d="M252 50V180M256 50V180"
          stroke="rgb(255 255 255 / .55)"
          strokeWidth=".8"
          style={{ transformBox: "view-box", transformOrigin: "254px 50px", animation: "cable 7s ease-in-out infinite" }}
        />
        <g style={{ animation: "izar 7s ease-in-out infinite" }}>
          <g style={{ transformOrigin: "254px 180px", animation: "balanceo 3.5s ease-in-out infinite" }}>
            <path d="M254 180v6a4 4 0 1 1-4 4" stroke="#f5b800" strokeWidth="1.6" />
            <path d="M254 194L238 206M254 194L270 206" stroke="rgb(255 255 255 / .5)" strokeWidth=".8" />
            <rect x="234" y="206" width="40" height="22" fill="#f5b800" />
            <path d="M234 214H274M247 206V214M261 214V228" stroke="#1b1e22" strokeOpacity=".35" />
          </g>
        </g>
      </g>
    </svg>
  );
}
