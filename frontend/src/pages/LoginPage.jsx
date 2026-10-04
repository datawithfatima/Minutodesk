import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { iniciarSesion } from "../api";
import { guardarSesion, rutaInicio } from "../auth";
import AuthShell from "../components/AuthShell";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
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
      navegar(rutaInicio(cliente.rol));
    } catch (e) {
      setError(e.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <AuthShell>
      {error && (
        <Alert variant="danger" className="mb-3">
          {error}
        </Alert>
      )}
      <form onSubmit={manejarEnvio} className="flex flex-col gap-3">
        <div>
          <label className={labelClass}>Correo electrónico</label>
          <input
            type="email"
            className={inputClass}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="correo@ejemplo.com"
          />
        </div>
        <div>
          <label className={labelClass}>Contraseña</label>
          <input
            type="password"
            className={inputClass}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <Button type="submit" variant="dark" disabled={enviando} className="mt-1 w-full">
          {enviando ? <Spinner size="sm" /> : "Ingresar"}
        </Button>
      </form>
      <div className="mt-4 border-t border-gray-100 pt-3 text-center text-sm text-gray-500">
        <Link to="/olvide-password" className="text-blue-600 hover:underline">
          ¿Olvidaste tu contraseña?
        </Link>
        <p className="mt-2 text-xs text-gray-400">
          Las cuentas las crea el administrador. Si aún no activaste la tuya, usa el enlace del
          correo de invitación.
        </p>
      </div>
    </AuthShell>
  );
}
