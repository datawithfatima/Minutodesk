/**
 * Encabezado de pantalla con forma de cartela de plano: icono en un bloque grafito,
 * título rotulado y una regla de medición que se extiende al entrar.
 */
export default function PageHeader({ icon: Icon, title, children }) {
  return (
    <header className="mb-5 sm:mb-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-grafito text-casco shadow-[0_1px_0_rgb(0_0_0/0.2)]">
            <Icon size={19} aria-hidden="true" />
            <span aria-hidden="true" className="absolute -bottom-1 -right-1 h-2.5 w-2.5 rounded-[2px] bg-acento" />
          </span>
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-noche sm:text-[24px]">{title}</h1>
          </div>
        </div>
        {children}
      </div>
      <div aria-hidden="true" className="regla mt-4" />
    </header>
  );
}
