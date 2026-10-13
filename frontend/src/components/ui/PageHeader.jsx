export default function PageHeader({ icon: Icon, title, subtitle, children }) {
  return (
    <header className="mb-5 flex flex-wrap items-start justify-between gap-3 sm:mb-6">
      <div className="flex min-w-0 items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white text-acento shadow-[0_1px_2px_rgba(16,27,48,0.06)] ring-1 ring-linea">
          <Icon size={19} aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <h1 className="text-xl font-semibold tracking-[-0.015em] text-noche sm:text-[22px]">{title}</h1>
          {subtitle && <p className="mt-0.5 text-sm text-gray-500">{subtitle}</p>}
        </div>
      </div>
      {children}
    </header>
  );
}
