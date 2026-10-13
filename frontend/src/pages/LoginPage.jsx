import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { iniciarSesion } from "../api";
import { guardarSesion, rutaInicio } from "../auth";
import AuthShell from "../components/AuthShell";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import CampoPassword from "../components/ui/CampoPassword";
import Spinner from "../components/ui/Spinner";
import { inputClass, labelClass } from "../components/ui/formStyles";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const navegar = useNavigate();

  async function manejarEnvio(e) {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      const { access_token, cliente } = await iniciarSesion({ email, password });
      guardarSesion(access_token, cliente);
      navegar(cliente.debe_cambiar_password ? "/cambiar-password" : rutaInicio(cliente.rol));
    } catch (e) {
      setError(e.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <AuthShell
      titulo="Inicia sesión"
      descripcion="Accede con la cuenta que te entregó el administrador."
      pie="¿Primer ingreso? Usa tu contraseña temporal; te pediremos cambiarla."
    >
      {error && (
        <Alert variant="danger" className="mb-4">
          {error}
        </Alert>
      )}
      <form onSubmit={manejarEnvio} className="flex flex-col gap-4">
        <div>
          <label htmlFor="login-email" className={labelClass}>
            Correo electrónico
          </label>
          <input
            id="login-email"
            type="email"
            className={inputClass}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="username"
            autoFocus
            placeholder="nombre@empresa.com"
          />
        </div>
        <div>
          <div className="mb-1.5 flex items-baseline justify-between gap-3">
            <label htmlFor="login-password" className="text-sm font-medium text-noche">
              Contraseña
            </label>
            <Link to="/olvide-password" className="rounded text-sm text-acento hover:underline">
              ¿La olvidaste?
            </Link>
          </div>
          <CampoPassword
            id="login-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>
        <Button type="submit" size="lg" disabled={enviando} className="mt-1 w-full">
          {enviando ? (
            <>
              <Spinner size="sm" /> Ingresando…
            </>
          ) : (
            "Ingresar"
          )}
        </Button>
      </form>
    </AuthShell>
  );
}
