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
  return (
    <div className="min-h-screen bg-gray-50">
      <TopBar usuario={usuario} rutaBusqueda={rutaBusqueda} />
      <div className="flex">
        <Sidebar navItems={navItems} onLogout={onLogout} footer={footer} dark={dark}>
          {sidebarExtra}
        </Sidebar>
        <main className="min-w-0 flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
