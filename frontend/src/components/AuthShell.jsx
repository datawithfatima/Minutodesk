import Logo from "./Logo";

export default function AuthShell({ children }) {
  return (
    <div
      className="relative flex min-h-screen items-center justify-center bg-slate-800 bg-cover bg-center px-4"
      style={{ backgroundImage: "url(/img/fondo-login.jpg)" }}
    >
      <div className="absolute inset-0 bg-slate-900/60" />
      <div className="relative z-10 w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex flex-col items-center text-center">
          <Logo />
          <h1 className="mt-3 text-lg font-bold tracking-wide text-gray-900">MINUTODESK</h1>
          <p className="text-sm text-gray-500">Mesa de ayuda</p>
        </div>
        <hr className="mb-4 border-gray-200" />
        {children}
      </div>
    </div>
  );
}
