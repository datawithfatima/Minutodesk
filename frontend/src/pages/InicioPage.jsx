import {
  ArrowRight,
  Bot,
  CheckCircle2,
  Layers3,
  LockKeyhole,
  Paperclip,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import { Link } from "react-router-dom";
import { obtenerToken, obtenerUsuario, rutaInicio } from "../auth";
import EstadoBadge from "../components/EstadoBadge";
import Logo, { Marca } from "../components/Logo";
import { PrioridadPastilla } from "../components/tickets/Pastillas";

/* Todo lo que se describe aquí existe hoy en la plataforma. Los tickets y la conversación
   son contenido de muestra y se rotulan como «Vista de ejemplo». */

const ANCHO = "mx-auto w-full max-w-[1200px] px-4 sm:px-6 lg:px-8";

const BOTON_PRIMARIO =
  "inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-acento px-5 text-[15px] font-medium text-white shadow-sm transition-colors duration-150 hover:bg-acento-600";
const BOTON_SECUNDARIO =
  "inline-flex h-12 items-center justify-center gap-2 rounded-xl border border-linea bg-white px-5 text-[15px] font-medium text-noche transition-colors duration-150 hover:border-gray-300 hover:bg-white/60";

function EtiquetaEjemplo({ oscura = false }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${
        oscura ? "bg-white/10 text-white/70" : "bg-marfil text-gray-500 ring-1 ring-inset ring-linea"
      }`}
    >
      Vista de ejemplo
    </span>
  );
}

/* ───────────── Encabezado ───────────── */

function Encabezado({ destino, sesionActiva }) {
  return (
    <header className="sticky top-0 z-30 border-b border-linea/80 bg-marfil">
      <div className={`${ANCHO} flex h-16 items-center justify-between gap-4`}>
        <Link to="/" className="rounded-lg" aria-label="MinutoDesk, inicio">
          <Marca />
        </Link>
        <nav aria-label="Secciones de la portada" className="hidden items-center gap-1 md:flex">
          {[
            ["#plataforma", "Plataforma"],
            ["#minutito", "Minutito"],
            ["#acceso", "Acceso"],
          ].map(([href, texto]) => (
            <a
              key={href}
              href={href}
              className="rounded-lg px-3 py-2 text-sm text-gray-600 transition-colors duration-150 hover:bg-white hover:text-noche"
            >
              {texto}
            </a>
          ))}
        </nav>
        <Link
          to={destino}
          className="inline-flex h-10 items-center gap-2 rounded-lg bg-noche px-4 text-sm font-medium text-white transition-colors duration-150 hover:bg-noche-700"
        >
          {sesionActiva ? "Ir a mi panel" : "Iniciar sesión"}
        </Link>
      </div>
    </header>
  );
}

/* ───────────── Vista del producto (muestra) ───────────── */

const TICKETS_MUESTRA = [
  { id: 128, texto: "No me conecta la VPN desde casa", categoria: "Internet", prioridad: "Alta", estado: "en_proceso" },
  { id: 127, texto: "La impresora del segundo piso no imprime", categoria: "Laptops - Impresoras", prioridad: "Normal", estado: "abierto" },
  { id: 126, texto: "Alta de colaborador para el área de Compras", categoria: "Creación de Usuario", prioridad: "Normal", estado: "abierto" },
  { id: 125, texto: "Error al guardar una oportunidad en Salesforce", categoria: "Salesforce", prioridad: "Crítica", estado: "resuelto" },
];

function VistaProducto() {
  return (
    <div className="relative sm:mb-16">
      <div className="overflow-hidden rounded-2xl border border-linea bg-white shadow-[0_1px_2px_rgba(16,27,48,0.04),0_24px_48px_-24px_rgba(16,27,48,0.22)]">
        <div className="flex items-center justify-between gap-3 border-b border-linea px-4 py-3 sm:px-5">
          <div className="flex items-center gap-2.5">
            <Logo size="h-6 w-6" />
            <span className="text-sm font-semibold text-noche">Bandeja de tickets</span>
          </div>
          <EtiquetaEjemplo />
        </div>

        <div className="flex gap-1.5 overflow-hidden border-b border-linea px-4 py-2.5 text-xs sm:px-5" aria-hidden="true">
          <span className="rounded-md bg-noche px-2 py-1 font-medium text-white">Todos</span>
          <span className="rounded-md px-2 py-1 text-gray-500 ring-1 ring-inset ring-linea">En proceso</span>
          <span className="rounded-md px-2 py-1 text-gray-500 ring-1 ring-inset ring-linea">Nuevos</span>
          <span className="hidden rounded-md px-2 py-1 text-gray-500 ring-1 ring-inset ring-linea sm:inline">Resueltos</span>
        </div>

        <ul className="divide-y divide-linea">
          {TICKETS_MUESTRA.map((t, i) => (
            <li
              key={t.id}
              className={`flex items-start justify-between gap-3 px-4 py-3 sm:px-5 ${i === 0 ? "bg-acento-50/60" : ""}`}
            >
              <div className="min-w-0">
                <div className="text-[11px] font-medium text-gray-400">#{t.id}</div>
                <div className="truncate text-sm font-medium text-noche">{t.texto}</div>
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                  <span className="rounded-full bg-marfil px-2 py-0.5 text-[11px] font-medium text-gray-600 ring-1 ring-inset ring-linea">
                    {t.categoria}
                  </span>
                  <PrioridadPastilla prioridad={t.prioridad} />
                </div>
              </div>
              <EstadoBadge estado={t.estado} />
            </li>
          ))}
        </ul>
      </div>

      {/* Lo que ve quien crea el ticket: la categoría propuesta mientras escribe. */}
      <div className="mt-4 rounded-2xl border border-linea bg-white p-4 shadow-[0_16px_32px_-20px_rgba(16,27,48,0.35)] sm:absolute sm:-bottom-[4.5rem] sm:-left-6 sm:mt-0 sm:w-[290px] lg:-left-10">
        <div className="flex items-center gap-2 text-xs font-medium text-gray-500">
          <Sparkles size={14} className="text-acento" aria-hidden="true" />
          Categoría sugerida al escribir
        </div>
        <div className="mt-1.5 flex items-center justify-between gap-2">
          <span className="text-sm font-semibold text-noche">Laptops - Impresoras</span>
          <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700">
            <CheckCircle2 size={13} aria-hidden="true" /> Confiable
          </span>
        </div>
        <p className="mt-1 text-xs text-gray-500">Puedes confirmarla o elegir otra antes de enviar.</p>
      </div>
    </div>
  );
}

/* ───────────── Secciones ───────────── */

const BENEFICIOS = [
  {
    Icono: Layers3,
    titulo: "Solicitudes organizadas",
    texto:
      "Cada ticket guarda su tipo, categoría, prioridad y estado: nuevo, en proceso, resuelto o cancelado con su motivo. El historial muestra quién hizo cada cambio.",
    detalles: ["Hasta 3 archivos adjuntos por ticket", "Formulario guiado para el alta de colaboradores"],
  },
  {
    Icono: Sparkles,
    titulo: "Clasificación automática",
    texto:
      "Mientras describes la solicitud, un modelo entrenado con el histórico de tickets propone el tipo y la categoría, con su nivel de confianza.",
    detalles: ["Tú confirmas o eliges otra categoría", "El técnico puede corregirla al atender"],
  },
  {
    Icono: Bot,
    titulo: "Minutito, tu asistente",
    texto:
      "Atiende las consultas de primer nivel con pasos concretos. Si no logra resolverlo, el ticket queda listo para el equipo de soporte.",
    detalles: ["Solo cuenta como resuelto si tú lo confirmas", "Nunca te pide contraseñas"],
  },
];

function Beneficios() {
  return (
    <section id="plataforma" className="scroll-mt-16 border-y border-linea bg-white py-20 sm:py-24">
      <div className={ANCHO}>
        <div className="max-w-2xl">
          <p className="text-sm font-semibold text-acento">La plataforma</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-[-0.025em] text-noche sm:text-[38px] sm:leading-[1.15]">
            Del primer mensaje a la solución, sin perder el rastro.
          </h2>
          <p className="mt-4 text-base leading-relaxed text-gray-600">
            Usuarios, técnicos y administradores trabajan sobre la misma información, cada uno con
            los permisos de su rol.
          </p>
        </div>

        <div className="mt-14 grid gap-10 md:grid-cols-3 md:gap-0 md:divide-x md:divide-linea">
          {BENEFICIOS.map(({ Icono, titulo, texto, detalles }) => (
            <article key={titulo} className="md:px-8 md:first:pl-0 md:last:pr-0">
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-acento-50 text-acento ring-1 ring-inset ring-acento-100">
                <Icono size={20} aria-hidden="true" />
              </span>
              <h3 className="mt-5 text-lg font-semibold tracking-[-0.01em] text-noche">{titulo}</h3>
              <p className="mt-2 text-[15px] leading-relaxed text-gray-600">{texto}</p>
              <ul className="mt-4 space-y-2">
                {detalles.map((d) => (
                  <li key={d} className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-acento" aria-hidden="true" />
                    {d}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>

        <dl className="mt-16 grid gap-4 rounded-2xl border border-linea bg-marfil p-5 sm:grid-cols-3 sm:p-6">
          {[
            [Users, "Tres roles", "Usuario, técnico y administrador, con accesos distintos."],
            [LockKeyhole, "Cuentas controladas", "Las crea el administrador; la primera contraseña es temporal."],
            [Paperclip, "Evidencia a mano", "Capturas, documentos o registros adjuntos al ticket."],
          ].map(([Icono, titulo, texto]) => (
            <div key={titulo} className="flex items-start gap-3">
              <Icono size={18} className="mt-0.5 shrink-0 text-noche" aria-hidden="true" />
              <div>
                <dt className="text-sm font-semibold text-noche">{titulo}</dt>
                <dd className="mt-0.5 text-sm text-gray-600">{texto}</dd>
              </div>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

function Minutito() {
  return (
    <section id="minutito" className="scroll-mt-16 py-20 sm:py-24">
      <div className={`${ANCHO} grid grid-cols-1 items-center gap-12 lg:grid-cols-2 lg:gap-16`}>
        <div>
          <p className="text-sm font-semibold text-acento">Asistente virtual</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-[-0.025em] text-noche sm:text-[38px] sm:leading-[1.15]">
            Minutito resuelve lo frecuente para que el equipo atienda lo importante.
          </h2>
          <p className="mt-4 text-base leading-relaxed text-gray-600">
            Responde consultas habituales como contraseñas, VPN, impresoras, Office o videollamadas
            con pasos claros. Siempre se presenta como asistente virtual.
          </p>
          <ul className="mt-6 space-y-3">
            {[
              "Te pregunta si se resolvió: solo así cuenta como resuelto por Minutito.",
              "Si pides hablar con una persona, deja tu caso al equipo de soporte.",
              "No solicita contraseñas ni datos personales.",
            ].map((t) => (
              <li key={t} className="flex items-start gap-2.5 text-[15px] text-gray-700">
                <ShieldCheck size={18} className="mt-0.5 shrink-0 text-acento" aria-hidden="true" />
                {t}
              </li>
            ))}
          </ul>
        </div>

        <figure className="rounded-2xl border border-linea bg-white shadow-[0_24px_48px_-28px_rgba(16,27,48,0.25)]">
          <div className="flex items-center justify-between gap-3 border-b border-linea px-5 py-3.5">
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-acento text-white">
                <Bot size={16} aria-hidden="true" />
              </span>
              <div>
                <div className="text-sm font-semibold text-noche">Minutito</div>
                <div className="text-xs text-gray-500">Asistente virtual de MinutoDesk</div>
              </div>
            </div>
            <EtiquetaEjemplo />
          </div>
          <div className="space-y-3 p-5">
            <div className="flex justify-end">
              <p className="max-w-[85%] rounded-2xl rounded-br-md bg-noche px-3.5 py-2.5 text-sm text-white">
                No me conecta la VPN desde casa.
              </p>
            </div>
            <div className="max-w-[92%] rounded-2xl rounded-tl-md border border-linea bg-marfil px-3.5 py-3 text-sm leading-relaxed text-gray-700">
              Dale una revisada a esto:
              <ol className="mt-1.5 list-decimal space-y-1 pl-5">
                <li>Comprueba que tengas internet sin la VPN, por ejemplo abriendo una página web.</li>
                <li>Cierra por completo el programa de la VPN y ábrelo otra vez.</li>
                <li>Revisa que el usuario y la contraseña estén bien escritos, sin espacios al final.</li>
              </ol>
            </div>
            <div className="rounded-xl border border-linea p-3" aria-hidden="true">
              <div className="text-sm font-medium text-noche">¿Se resolvió tu problema?</div>
              <div className="mt-2 flex flex-wrap gap-2 text-sm">
                <span className="rounded-lg bg-noche px-3 py-1.5 font-medium text-white">Sí, se resolvió</span>
                <span className="rounded-lg border border-linea px-3 py-1.5 font-medium text-noche">
                  No, necesito un técnico
                </span>
              </div>
            </div>
          </div>
          <figcaption className="sr-only">
            Ejemplo de conversación: Minutito responde con tres pasos y pregunta si el problema se resolvió.
          </figcaption>
        </figure>
      </div>
    </section>
  );
}

function Cierre({ destino, sesionActiva }) {
  return (
    <section id="acceso" className="scroll-mt-16 px-4 pb-20 sm:px-6 sm:pb-24 lg:px-8">
      <div className="relative mx-auto max-w-[1200px] overflow-hidden rounded-3xl bg-noche px-6 py-14 text-center sm:px-12 sm:py-16">
        <svg aria-hidden="true" className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.06]">
          <defs>
            <pattern id="trama-cierre" width="32" height="32" patternUnits="userSpaceOnUse">
              <path d="M32 0H0v32" fill="none" stroke="#fff" strokeWidth="1" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#trama-cierre)" />
        </svg>
        <div className="relative">
          <h2 className="text-3xl font-semibold tracking-[-0.025em] text-white sm:text-[38px]">
            {sesionActiva ? "Tu panel te espera." : "Entra y registra tu próxima solicitud."}
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-white/70">
            Ingresa con la cuenta que te entregó el administrador. En el primer ingreso te pediremos
            cambiar la contraseña temporal.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link to={destino} className={`${BOTON_PRIMARIO} w-full sm:w-auto`}>
              {sesionActiva ? "Ir a mi panel" : "Iniciar sesión"} <ArrowRight size={17} aria-hidden="true" />
            </Link>
            <Link
              to="/olvide-password"
              className="inline-flex h-12 items-center rounded-xl px-4 text-[15px] font-medium text-white/80 transition-colors duration-150 hover:text-white hover:underline"
            >
              ¿Olvidaste tu contraseña?
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

function Pie() {
  return (
    <footer className="border-t border-linea bg-white">
      <div className={`${ANCHO} flex flex-col gap-6 py-8 sm:flex-row sm:items-center sm:justify-between`}>
        <div>
          <Marca size="h-8 w-8" />
          <p className="mt-2 text-sm text-gray-500">
            Mesa de ayuda con clasificación automática y asistente virtual.
          </p>
        </div>
        <nav aria-label="Enlaces del pie" className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-gray-600">
          <a href="#plataforma" className="rounded hover:text-noche">Plataforma</a>
          <a href="#minutito" className="rounded hover:text-noche">Minutito</a>
          <Link to="/login" className="rounded hover:text-noche">Iniciar sesión</Link>
          <Link to="/olvide-password" className="rounded hover:text-noche">Recuperar contraseña</Link>
        </nav>
      </div>
      <div className="border-t border-linea">
        <p className={`${ANCHO} py-4 text-xs text-gray-400`}>© {new Date().getFullYear()} MinutoDesk</p>
      </div>
    </footer>
  );
}

/* ───────────── Página ───────────── */

export default function InicioPage() {
  const usuario = obtenerToken() ? obtenerUsuario() : null;
  const sesionActiva = Boolean(usuario);
  // Con sesión abierta, la acción principal lleva al panel de su rol (o a cambiar la temporal).
  const destino = !usuario
    ? "/login"
    : usuario.debe_cambiar_password
      ? "/cambiar-password"
      : rutaInicio(usuario.rol);

  return (
    <div className="min-h-screen bg-marfil text-noche">
      <a
        href="#principal"
        className="sr-only z-[60] rounded-lg bg-white px-4 py-2 text-sm font-medium shadow-lg focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
      >
        Saltar al contenido
      </a>
      <Encabezado destino={destino} sesionActiva={sesionActiva} />

      <main id="principal">
        <section className={`${ANCHO} grid grid-cols-1 items-center gap-14 pb-24 pt-12 sm:pt-16 lg:grid-cols-[1.05fr_1fr] lg:gap-16 lg:pb-28 lg:pt-20`}>
          <div>
            <p className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-xs font-medium text-gray-600 ring-1 ring-inset ring-linea">
              <span className="h-1.5 w-1.5 rounded-full bg-acento" aria-hidden="true" />
              Mesa de ayuda TI
            </p>
            <h1 className="mt-5 text-[42px] font-semibold leading-[1.05] tracking-[-0.035em] text-noche sm:text-[56px] lg:text-[60px]">
              Cada solicitud,
              <br />
              <span className="text-acento">en su lugar.</span>
            </h1>
            <p className="mt-5 max-w-[30rem] text-lg leading-relaxed text-gray-600">
              Centraliza las solicitudes de soporte y agiliza su clasificación con MinutoDesk.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link to={destino} className={BOTON_PRIMARIO}>
                {sesionActiva ? "Ir a mi panel" : "Iniciar sesión"} <ArrowRight size={17} aria-hidden="true" />
              </Link>
              <a href="#plataforma" className={BOTON_SECUNDARIO}>
                Conocer la plataforma
              </a>
            </div>
            <ul className="mt-10 flex flex-wrap gap-x-6 gap-y-2 text-sm text-gray-600">
              {["Tipo y categoría sugeridos", "Prioridad y adjuntos", "Seguimiento por estado"].map((t) => (
                <li key={t} className="flex items-center gap-2">
                  <CheckCircle2 size={16} className="text-acento" aria-hidden="true" />
                  {t}
                </li>
              ))}
            </ul>
          </div>

          <VistaProducto />
        </section>

        <Beneficios />
        <Minutito />
        <Cierre destino={destino} sesionActiva={sesionActiva} />
      </main>

      <Pie />
    </div>
  );
}
