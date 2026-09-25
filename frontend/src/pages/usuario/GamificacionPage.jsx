import { Trophy } from "lucide-react";
import { useEffect, useState } from "react";
import { obtenerGamificacion } from "../../api";
import { obtenerUsuario } from "../../auth";
import Alert from "../../components/ui/Alert";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";
import GamificacionCard from "../../components/GamificacionCard";

export default function GamificacionPage() {
  const usuario = obtenerUsuario();
  const [detalle, setDetalle] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    obtenerGamificacion(usuario.id)
      .then(setDetalle)
      .catch((e) => setError(e.message));
  }, [usuario.id]);

  return (
    <>
      <PageHeader
        icon={Trophy}
        title="Mi gamificación"
        subtitle="Revisa tus puntos e historial por usar el autoservicio."
      />
      {error && <Alert variant="danger">{error}</Alert>}
      {!detalle && !error && <Spinner size="sm" />}
      {detalle && <GamificacionCard detalle={detalle} />}
    </>
  );
}
