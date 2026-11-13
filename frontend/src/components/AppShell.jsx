import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
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
  const { pathname } = useLocation();
  const contenido = useRef(null);
  const [cinta, setCinta] = useState(0);

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

  // Animación de entrada al cambiar de sección: los bloques «se levantan» como pisos.
  // Solo se reinicia la animación (no se vuelve a montar la pantalla), y dentro de una
  // misma sección (p. ej. pasar de un ticket a otro) no se repite.
  const seccion = pathname.split("/").slice(0, 3).join("/");
  useLayoutEffect(() => {
    const el = contenido.current;
    if (!el) return;
    el.classList.remove("anim-levantar");
    void el.offsetWidth; // fuerza el reinicio de la animación CSS
    el.classList.add("anim-levantar");
  }, [seccion]);

  // Cinta de seguridad en la parte superior en cada cambio de pantalla.
  useEffect(() => setCinta((n) => n + 1), [pathname]);

  return (
    <div className="papel-plano min-h-screen">
      <a
        href="#contenido"
        className="sr-only z-[60] rounded-md bg-white px-4 py-2 text-sm font-medium text-noche shadow-lg focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
      >
        Saltar al contenido
      </a>
      <span
        key={cinta}
        aria-hidden="true"
        className="franja-obra cinta-ruta pointer-events-none fixed inset-x-0 top-0 z-[70] h-[3px]"
      />
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
          <div ref={contenido} className="anim-levantar mx-auto w-full max-w-[1400px]">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
