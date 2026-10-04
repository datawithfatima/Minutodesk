import { useNavigate } from "react-router-dom";
import Button from "../components/ui/Button";

export default function InicioPage() {
  const navegar = useNavigate();

  return (
    <div className="mt-24 text-center">
      <h1 className="mb-2 text-3xl font-bold">MinutoDesk</h1>
      <p className="mb-6 text-gray-500">
        Mesa de ayuda con clasificación automática y Minutito.
      </p>
      <Button onClick={() => navegar("/login")}>Iniciar sesión</Button>
    </div>
  );
}
