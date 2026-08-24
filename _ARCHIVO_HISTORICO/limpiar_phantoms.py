"""
limpiar_phantoms.py
Post-procesa bodegas_gestion.json y bodegas_ir_otras.json para eliminar registros
phantom: fisico < 0 AND diasAntiguedad > UMBRAL_DIAS.

Estos registros son artefactos de R_STOCK_PRODUCTOS sin filtro IDSUCURSAL — el script
generar_bodegas_gestion.py ya tiene el fix correcto en SQL, pero los JSONs actuales
fueron generados con el codigo viejo. Este script limpia los datos existentes hasta que
se pueda regenerar con conexion SQL.

Regla: fisico < 0 AND diasAntiguedad > 730 (2 anios) → phantom, eliminar.
Bodegas con stock negativo legitimo reciente (CAL, GO, CEM) conservan sus negativos
recientes (dias <= 730).

ANTI-RETROCESO: si la limpieza elimina mas del 30% de registros de una bodega
especifica, aborta esa bodega y conserva los datos originales (para no destruir
bodegas con stock negativo legitimo abundante).
"""
import json
import datetime
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).parent
UMBRAL_DIAS = 730
MAX_REDUCCION_POR_BODEGA = 0.30  # 30%


def log(msg):
    print(msg, flush=True)


def limpiar_registros(registros, label):
    por_bodega = defaultdict(list)
    for r in registros:
        por_bodega[r.get("bodega", "?")].append(r)

    resultado = []
    resumen = []
    for bod, regs in sorted(por_bodega.items()):
        phantoms = [r for r in regs if (r.get("fisico", 0) < 0 and (r.get("diasAntiguedad") or 0) > UMBRAL_DIAS)]
        ratio = len(phantoms) / len(regs) if regs else 0

        if ratio > MAX_REDUCCION_POR_BODEGA:
            # Demasiado agresivo para esta bodega — conservar todo y solo loguear
            resultado.extend(regs)
            resumen.append((bod, len(regs), 0, f"OMITIDO (reduccion {ratio:.0%} > limite {MAX_REDUCCION_POR_BODEGA:.0%})"))
        else:
            limpios = [r for r in regs if r not in phantoms]
            resultado.extend(limpios)
            resumen.append((bod, len(regs), len(phantoms), f"OK (-{len(phantoms)})"))

    log(f"\n  [{label}] Resumen por bodega:")
    for bod, total, eliminados, estado in resumen:
        log(f"    {bod:6s}: {total:4d} → -{eliminados:3d}  {estado}")

    return resultado


def procesar_bodegas_gestion():
    path = BASE_DIR / "bodegas_gestion.json"
    if not path.exists():
        log("[SKIP] bodegas_gestion.json no existe")
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    total_antes = data.get("total", 0)

    for suc in data.get("sucursales", []):
        suc["registros"] = limpiar_registros(suc["registros"], suc["nombre"])
        suc["total"] = len(suc["registros"])

    if "compartidas" in data:
        data["compartidas"]["registros"] = limpiar_registros(data["compartidas"]["registros"], "Compartidas")
        data["compartidas"]["total"] = len(data["compartidas"]["registros"])

    total_despues = sum(s["total"] for s in data["sucursales"])
    if "compartidas" in data:
        total_despues += data["compartidas"]["total"]

    data["total"] = total_despues
    data["generado"] = datetime.date.today().isoformat()
    data["nota_limpieza"] = f"Phantoms eliminados (fisico<0 AND dias>{UMBRAL_DIAS}). Regenerar con SQL cuando este disponible."

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"\n[OK] bodegas_gestion.json: {total_antes} → {total_despues} registros (-{total_antes - total_despues})")


def procesar_bodegas_ir_otras():
    path = BASE_DIR / "bodegas_ir_otras.json"
    if not path.exists():
        log("[SKIP] bodegas_ir_otras.json no existe")
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    total_antes = data.get("total", 0)

    data["registros"] = limpiar_registros(data["registros"], "IR-otras")
    total_despues = len(data["registros"])
    data["total"] = total_despues
    data["generado"] = datetime.date.today().isoformat()
    data["nota_limpieza"] = f"Phantoms eliminados (fisico<0 AND dias>{UMBRAL_DIAS}). Regenerar con SQL cuando este disponible."

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"\n[OK] bodegas_ir_otras.json: {total_antes} → {total_despues} registros (-{total_antes - total_despues})")


def main():
    log(f"=== limpiar_phantoms.py — umbral={UMBRAL_DIAS} dias, max_reduccion={MAX_REDUCCION_POR_BODEGA:.0%} ===")
    procesar_bodegas_gestion()
    procesar_bodegas_ir_otras()

    log("\n=== VERIFICACION FINAL ===")
    for fname in ["bodegas_gestion.json", "bodegas_ir_otras.json"]:
        path = BASE_DIR / fname
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            log(f"  {fname}: total={data.get('total','?')}")


if __name__ == "__main__":
    main()
