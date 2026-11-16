# -*- coding: utf-8 -*-
"""Punto único de entrada para DenunciaFácil 360.

Ejemplo:
python src/analisis/ejecutar_analisis.py --denuncia-id 125 --nombre "JUAN CARLOS" --primer-apellido "PEREZ" --segundo-apellido "LOPEZ"

Cada ejecución guarda sus artefactos en resultados/denuncias/<denuncia-id>/.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "src" / "analisis"
MODELS = ROOT / "src" / "modelos" / "entrenados"
ORIGINALS = Path(os.environ.get("PDN_DATOS_ORIGINALES", str(ROOT / "datos" / "originales"))).resolve()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_step(label, script, args, env, log_path):
    command = [sys.executable, str(SCRIPTS / script)] + args
    completed = subprocess.run(command, cwd=str(ROOT), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    with log_path.open("a", encoding="utf-8") as log:
        log.write("\n" + "=" * 70 + "\n" + label + "\n")
        log.write("COMMAND: " + " ".join(command) + "\n")
        log.write(completed.stdout or "")
        if completed.stderr:
            log.write("\nSTDERR:\n" + completed.stderr)
    if completed.returncode != 0:
        raise RuntimeError(f"Falló {label} (código {completed.returncode}). Revisá {log_path}")
    return completed.stdout


def main():
    parser = argparse.ArgumentParser(description="Ejecuta el análisis PDN completo para una denuncia.")
    parser.add_argument("--denuncia-id", help="Identificador interno o clave única de ejecución")
    parser.add_argument("--nombre", default="")
    parser.add_argument("--primer-apellido", default="")
    parser.add_argument("--segundo-apellido", default="")
    parser.add_argument("--solicitud-json", help="Archivo JSON privado con los datos de una solicitud")
    args = parser.parse_args()

    if args.solicitud_json:
        solicitud_path = Path(args.solicitud_json).resolve()
        if not solicitud_path.is_file():
            parser.error("No existe el archivo de solicitud indicado.")
        try:
            solicitud = json.loads(solicitud_path.read_text(encoding="utf-8"))
        except Exception as exc:
            parser.error(f"No se pudo leer el archivo de solicitud: {exc}")
        args.denuncia_id = str(solicitud.get("clave_ejecucion", ""))
        args.nombre = str(solicitud.get("nombre", ""))
        args.primer_apellido = str(solicitud.get("primer_apellido", ""))
        args.segundo_apellido = str(solicitud.get("segundo_apellido", ""))

    if not args.denuncia_id:
        parser.error("Debe indicar --denuncia-id o --solicitud-json.")
    denuncia_id = str(args.denuncia_id).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", denuncia_id):
        parser.error("--denuncia-id solo puede contener letras, números, guion y guion bajo.")
    if not args.nombre.strip() or not args.primer_apellido.strip():
        parser.error("Nombre y primer apellido son obligatorios.")
    if not ORIGINALS.is_dir() or not any(ORIGINALS.rglob("*.json")):
        parser.error(f"No se encontraron JSON de PDN en: {ORIGINALS}")
    for model in ["isolation_forest_inicial.joblib", "isolation_forest_modificacion.joblib", "isolation_forest_conclusion.joblib"]:
        if not (MODELS / model).is_file():
            parser.error(f"Falta el modelo requerido: {MODELS / model}")

    run_dir = ROOT / "resultados" / "denuncias" / denuncia_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "ejecucion.log"
    manifest_path = run_dir / "estado_ejecucion.json"
    env = os.environ.copy()
    env["PDN_DATOS_ORIGINALES"] = str(ORIGINALS)
    env["PDN_RESULTADOS_DIR"] = str(run_dir)
    env["PDN_MODELOS_DIR"] = str(MODELS)

    manifest = {
        "denuncia_id": denuncia_id,
        "estado": "EN_PROCESO",
        "inicio_utc": datetime.now(timezone.utc).isoformat(),
        "fin_utc": None,
        "archivos": {},
        "mensaje": "Análisis iniciado.",
    }
    write_json(manifest_path, manifest)
    log_path.write_text("INICIO DE EJECUCIÓN " + manifest["inicio_utc"] + "\n", encoding="utf-8")
    try:
        run_step("1. BÚSQUEDA DE DECLARACIONES", "buscar_declaraciones_persona.py", [
            "--nombre", args.nombre, "--primer-apellido", args.primer_apellido,
            "--segundo-apellido", args.segundo_apellido
        ], env, log_path)
        matches_path = run_dir / "coincidencias_persona.json"
        matches = json.loads(matches_path.read_text(encoding="utf-8"))
        total = int(matches.get("resumen", {}).get("coincidencias", 0))
        manifest["coincidencias_encontradas"] = total
        if total == 0:
            manifest.update({"estado": "SIN_COINCIDENCIAS", "mensaje": "No se encontraron declaraciones con los datos proporcionados."})
            manifest["archivos"] = {"coincidencias": str(matches_path.relative_to(ROOT)).replace("\\", "/")}
        else:
            run_step("2. ANÁLISIS INTEGRAL PATRIMONIAL", "analizador_integral_patrimonial.py", [], env, log_path)
            run_step("3. INTERPRETACIÓN AUTOMÁTICA", "interpretar_resultados.py", [], env, log_path)
            expected = ["informe_integral_patrimonial.json", "interpretacion_patrimonial.json"]
            missing = [name for name in expected if not (run_dir / name).is_file()]
            if missing:
                raise RuntimeError("No se generaron todos los informes requeridos: " + ", ".join(missing))
            interpreted = json.loads((run_dir / "interpretacion_patrimonial.json").read_text(encoding="utf-8"))
            summary = interpreted.get("resumen", {})
            manifest.update({
                "estado": "FINALIZADO",
                "mensaje": "Análisis e interpretación completados.",
                "declaraciones_analizadas": len(interpreted.get("declaraciones", [])),
                "comparaciones": len(interpreted.get("comparaciones", [])),
                "resultados_modelo": summary.get("resultados_modelo", {}),
            })
            manifest["archivos"] = {
                "coincidencias": f"resultados/denuncias/{denuncia_id}/coincidencias_persona.json",
                "informe_integral": f"resultados/denuncias/{denuncia_id}/informe_integral_patrimonial.json",
                "interpretacion": f"resultados/denuncias/{denuncia_id}/interpretacion_patrimonial.json",
                "dashboard_html": f"resultados/denuncias/{denuncia_id}/interpretacion_patrimonial.html",
                "log": f"resultados/denuncias/{denuncia_id}/ejecucion.log",
            }
        manifest["fin_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(manifest_path, manifest)
        print(json.dumps(manifest, ensure_ascii=False))
        return 0
    except Exception as exc:
        manifest.update({"estado": "ERROR", "mensaje": str(exc), "fin_utc": datetime.now(timezone.utc).isoformat(), "log": f"resultados/denuncias/{denuncia_id}/ejecucion.log"})
        write_json(manifest_path, manifest)
        print(json.dumps(manifest, ensure_ascii=False))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
