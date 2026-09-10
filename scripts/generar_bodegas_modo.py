# -*- coding: utf-8 -*-
"""
generar_bodegas_modo.py — BODEGAS GESTION

Extrae de bodegas_gestion.json (ya generado por descargar_bodegas_sql.py) los
subconjuntos que consumen los usuarios restringidos MODO_SV (saliaga) y MODO_LC
(spavez), para no descargarles el dataset completo (12+ MB) en el login.

No hace ninguna consulta SQL nueva — solo recorta el JSON ya bajado. Por eso va
DESPUES de descargar_bodegas_sql.py en el pipeline (paso 2), nunca antes.

Bug corregido 09-09-2026: estos dos archivos se generaron una sola vez a mano
(commit 22a7cae, 28-08-2026) al implementar la carga optimizada por modo usuario,
y nunca quedaron en el pipeline — San Vicente y Las Cabras vieron datos de esa
fecha durante 12 dias mientras el admin ya tenia datos frescos. Este script cierra
ese hueco corriendo en cada ACTUALIZAR_DATOS.bat.

Anti-retroceso: aborta por archivo si el nuevo total < 50% del anterior.
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
IN_GESTION = BASE_DIR / 'bodegas_gestion.json'

OBJETIVOS = [
    {'idSucursal': '05', 'out': BASE_DIR / 'data' / 'bodegas-sv.json'},
    {'idSucursal': '06', 'out': BASE_DIR / 'data' / 'bodegas-lc.json'},
]


def anti_retroceso(out_path, nuevo_total):
    if not out_path.exists():
        return True
    try:
        ant = json.loads(out_path.read_text(encoding='utf-8'))
        ant_total = ant.get('total', 0)
    except Exception:
        return True
    if ant_total > 0 and nuevo_total < ant_total * 0.5:
        print(f'  [ABORTADO] {out_path.name}: {nuevo_total} vs {ant_total} '
              f'anteriores (caida >50%). Se conserva JSON anterior.')
        return False
    return True


def main():
    if not IN_GESTION.exists():
        print(f'ERROR: no existe {IN_GESTION} — correr descargar_bodegas_sql.py primero.')
        raise SystemExit(1)

    data = json.loads(IN_GESTION.read_text(encoding='utf-8'))
    generado = data.get('generado', '')
    sucursales = data.get('sucursales', [])

    for obj in OBJETIVOS:
        suc = next((s for s in sucursales if s.get('idSucursal') == obj['idSucursal']), None)
        if not suc:
            print(f'  [OMITIDO] idSucursal={obj["idSucursal"]} no encontrada en bodegas_gestion.json')
            continue

        registros = suc.get('registros', [])
        nuevo_total = len(registros)

        if not anti_retroceso(obj['out'], nuevo_total):
            continue

        payload = {
            'generado': generado,
            'sucursal': suc.get('nombre', ''),
            'idSucursal': suc.get('idSucursal', ''),
            'total': nuevo_total,
            'bodegasIncluidas': suc.get('bodegasIncluidas', []),
            'registros': registros,
        }
        obj['out'].parent.mkdir(parents=True, exist_ok=True)
        obj['out'].write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'  [OK] {obj["out"].name}: {nuevo_total} registros (generado {generado})')


if __name__ == '__main__':
    main()
