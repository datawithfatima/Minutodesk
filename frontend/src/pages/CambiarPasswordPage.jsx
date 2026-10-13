import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { cambiarPassword } from "../api";
import { cerrarSesion, guardarSesion, obtenerToken, obtenerUsuario, rutaInicio } from "../auth";
import AuthShell from "../components/AuthShell";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import CampoPassword from "../components/ui/CampoPassword";
import Spinner from "../components/ui/Spinner";
import { labelClass } from "../components/ui/formStyles";

export default function CambiarPasswordPage() {
  const usuario = obtenerUsuario();
  const navegar = useNavigate();
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  if (!obtenerToken() || !usuario) return <Navigate to="/login" replace />;

  const obligatorio = usuario.debe_cambiar_password;

  async function manejarEnvio(e) {
    e.preventDefault();
    setError(null);
    if (nueva !== confirmacion) {
      setError("Las contraseñas nuevas no coinciden");
      return;
    }
    setEnviando(true);
    try {
      // El servidor cierra las demás sesiones y entrega un token nuevo para esta.
      const { access_token, cliente } = await cambiarPassword({
        passwordActual: actual,
        passwordNueva: nueva,
      });
      guardarSesion(access_token, cliente);
      navegar(rutaInicio(cliente.rol), { replace: true });
    } catch (e) {
      setError(e.message);
    } finally {
      setEnviando(false);
    }
  }

  function salir() {
    cerrarSesion();
    navegar("/login", { replace: true });
  }

  return (
    <AuthShell
      titulo={obligatorio ? "Cambia tu contraseña temporal" : "Cambiar contraseña"}
      descripcion={
        obligatorio
          ? "Por seguridad, antes de continuar elige una contraseña propia."
          : "Escribe tu contraseña actual y elige una nueva."
      }
      pie={
        obligatorio ? (
          <button onClick={salir} className="rounded text-acento hover:underline">
            Cerrar sesión
          </button>
        ) : (
          <Link to={rutaInicio(usuario.rol)} className="rounded text-acento hover:underline">
            Volver a mi panel
          </Link>
        )
      }
    >
      {error && (
        <Alert variant="danger" className="mb-4">
          {error}
        </Alert>
      )}

      <form onSubmit={manejarEnvio} className="flex flex-col gap-4">
        <div>
          <label htmlFor="pw-actual" className={labelClass}>
            {obligatorio ? "Contraseña temporal" : "Contraseña actual"}
          </label>
          <CampoPassword
            id="pw-actual"
            value={actual}
            onChange={(e) => setActual(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>
        <div>
          <label htmlFor="pw-nueva" className={labelClass}>
            Contraseña nueva
          </label>
          <CampoPassword
            id="pw-nueva"
            value={nueva}
            onChange={(e) => setNueva(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
            aria-describedby="pw-reglas"
          />
          <p id="pw-reglas" className="mt-1.5 text-xs text-gray-500">
            Mínimo 8 caracteres, con letras y números.
          </p>
        </div>
        <div>
          <label htmlFor="pw-confirmacion" className={labelClass}>
            Repite la contraseña nueva
          </label>
          <CampoPassword
            id="pw-confirmacion"
            value={confirmacion}
            onChange={(e) => setConfirmacion(e.target.value)}
            required
            autoComplete="new-password"
          />
        </div>
        <Button type="submit" size="lg" disabled={enviando} className="mt-1 w-full">
          {enviando ? <Spinner size="sm" /> : "Guardar contraseña"}
        </Button>
      </form>
    </AuthShell>
  );
}
