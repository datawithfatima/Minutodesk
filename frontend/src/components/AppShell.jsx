import { useEffect, useState } from "react";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";

export default function AppShell({
  navItems,
  usuario,
  rutaBusqueda,
  onLogout,
  footer,
  dark,
  sidebarExtra,
  children,
}) {
  // En pantallas angostas el menú es un cajón que se abre desde la barra superior.
  const [menuAbierto, setMenuAbierto] = useState(false);

  useEffect(() => {
    if (!menuAbierto) return undefined;
    const alTeclear = (e) => e.key === "Escape" && setMenuAbierto(false);
    const desbordeAnterior = document.body.style.overflow;
    document.body.style.overflow = "hidden"; // la página de atrás no se desplaza
    window.addEventListener("keydown", alTeclear);
    return () => {
      document.body.style.overflow = desbordeAnterior;
      window.removeEventListener("keydown", alTeclear);
    };
  }, [menuAbierto]);

  return (
    <div className="min-h-screen bg-marfil">
      <a
        href="#contenido"
        className="sr-only z-[60] rounded-lg bg-white px-4 py-2 text-sm font-medium text-noche shadow-lg focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
      >
        Saltar al contenido
      </a>
      <TopBar
        usuario={usuario}
        rutaBusqueda={rutaBusqueda}
        menuAbierto={menuAbierto}
        onAbrirMenu={() => setMenuAbierto(true)}
        onLogout={onLogout}
      />
      <div className="flex">
        <Sidebar
          navItems={navItems}
          footer={footer}
          dark={dark}
          rutaBusqueda={rutaBusqueda}
          abierto={menuAbierto}
          onCerrar={() => setMenuAbierto(false)}
        >
          {sidebarExtra}
        </Sidebar>
        <main id="contenido" className="min-w-0 flex-1 px-3 py-4 sm:p-6 lg:px-8 lg:py-7">
          <div className="mx-auto w-full max-w-[1400px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
