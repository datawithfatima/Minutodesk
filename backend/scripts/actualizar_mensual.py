"""Actualización mensual con el export de tickets (CSV).

Uso (desde backend/):
    python scripts/actualizar_mensual.py ruta\\al\\export.csv
    python scripts/actualizar_mensual.py ruta\\al\\export.csv --sin-entrenar

Hace tres cosas, en orden:
  1. Guarda el CSV como data/tickets_historicos_raw.csv (reemplaza el anterior).
  2. Lo importa a la base para los reportes (los tickets existentes se
     actualizan por su ID; los nuevos se agregan; no se duplican).
  3. Limpia el dataset y reentrena el clasificador (omitir con --sin-entrenar).

Después de reentrenar, reinicia el backend para que cargue los modelos nuevos.
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session

from app.database import engine, init_db
from app.ml import prepare_dataset, train_classifier
from app.services.historico import importar_csv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path, help="export mensual de tickets")
    parser.add_argument("--sin-entrenar", action="store_true")
    args = parser.parse_args()

    if not args.csv.is_file():
        sys.exit(f"No encuentro el archivo: {args.csv}")

    destino = prepare_dataset.RAW_PATH
    destino.parent.mkdir(parents=True, exist_ok=True)
    if args.csv.resolve() != destino.resolve():
        shutil.copyfile(args.csv, destino)
    print(f"1/3 CSV guardado en {destino}")

    init_db()
    with Session(engine) as session:
        r = importar_csv(destino, session)
    print(
        f"2/3 Histórico: {r['nuevos']} nuevos, {r['actualizados']} actualizados, "
        f"{r['omitidos']} omitidos de {r['filas']} filas. Total en la base: {r['total_en_base']}"
    )

    if args.sin_entrenar:
        print("3/3 Entrenamiento omitido (--sin-entrenar).")
        return
    prepare_dataset.preparar()
    train_classifier.main()
    print("3/3 Clasificador reentrenado. Reinicia el backend para usar los modelos nuevos.")


if __name__ == "__main__":
    main()
