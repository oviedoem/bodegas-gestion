"""
descargar_stock_critico_lc.py  V1.0  2026-08-24
Genera data/stock-critico-lc.json desde SQL Server (R_STOCK_PRODUCTOS).

Trae parametros de abastecimiento configurados en ERP por Adquisiciones:
ST_MIN, ST_MAX, ST_CRITICO, ST_REPOSICION por producto, sumados sobre las
bodegas comerciales de Las Cabras.

Fuente: Foviedo.dbo.R_STOCK_PRODUCTOS
Bodegas comerciales Las Cabras: SLC=33, PLC=34, CLC=35, GLC=37 (suc 06).
Limitacion: SQL sincroniza con JustWeb 1 vez/dia (~22:00). LAN: sin VPN.

Salida:
  data/stock-critico-lc.json
    { "generado":..., "fuente":..., "bodegas":[...],
      "productos": { "<CODIGO>": {"min":N,"max":N,"critico":N,"repo":N,"disp":N} } }
"""

import json
import sys
import datetime
import configparser
from pathlib import Path

try:
    import pyodbc
except ImportError:
    print('[ERROR] pyodbc no instalado.')
    sys.exit(1)

BASE_DIR  = Path(r"E:\BODEGAS GESTION")
DATA_DIR  = BASE_DIR / "data"
CRED_FILE = Path(r"E:\ferreteria-oviedo\credenciales_db.ini")
ENC_FILE  = Path(r"E:\config\credenciales_db.enc")

# Bodegas comerciales Las Cabras (IDBODEGA SQL) — IDSUCURSAL='06'
# SLC=Sala, PLC=Patio, CLC=Calzada, GLC=Gestion
BODEGAS_LC = {33: 'SLC', 34: 'PLC', 35: 'CLC', 37: 'GLC'}


def log(msg):
    print(msg, flush=True)


def leer_credenciales():
    if ENC_FILE.exists():
        try:
            import ctypes, ctypes.wintypes
            class _BLOB(ctypes.Structure):
                _fields_ = [("cbData", ctypes.wintypes.DWORD),
                            ("pbData", ctypes.POINTER(ctypes.c_char))]
            raw = ENC_FILE.read_bytes()
            buf = ctypes.create_string_buffer(raw)
            blob_in  = _BLOB(len(raw), buf)
            blob_out = _BLOB()
            ok = ctypes.windll.crypt32.CryptUnprotectData(
                ctypes.byref(blob_in), None, None, None, None, 0,
                ctypes.byref(blob_out))
            if ok:
                dec = bytes(ctypes.string_at(blob_out.pbData, blob_out.cbData))
                ctypes.windll.kernel32.LocalFree(blob_out.pbData)
                d = json.loads(dec.decode('utf-8'))['DB']
                return d['server'], d['database'], d['user'], d['password']
        except Exception as e:
            log(f'[WARN] No se pudo leer credenciales_db.enc: {e} — usando .ini')

    cfg = configparser.ConfigParser()
    cfg.read(str(CRED_FILE), encoding='utf-8')
    return (cfg['DB']['server'], cfg['DB']['database'],
            cfg['DB']['user'], cfg['DB']['password'])


def conectar():
    server, database, user, password = leer_credenciales()
    conn_str = (
        f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};"
        f"UID={user};PWD={password};TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str, timeout=30)


# IDBODEGA tránsito Las Cabras
IDBODEGA_TLC = 16

SQL_PARAMS = """
SELECT
    R.CODIGO_TECNICO,
    R.IDBODEGA,
    CAST(ISNULL(R.ST_MIN,        0) AS DECIMAL(18,2)) AS ST_MIN,
    CAST(ISNULL(R.ST_MAX,        0) AS DECIMAL(18,2)) AS ST_MAX,
    CAST(ISNULL(R.ST_CRITICO,    0) AS DECIMAL(18,2)) AS ST_CRITICO,
    CAST(ISNULL(R.ST_REPOSICION, 0) AS DECIMAL(18,2)) AS ST_REPOSICION,
    CAST(ISNULL(R.ST_DISPONIBLE, 0) AS DECIMAL(18,2)) AS ST_DISPONIBLE,
    ISNULL(B.DESCRIPCION, '') AS DESCRIPCION,
    ISNULL(MA.MARCA, '') AS MARCA
FROM Foviedo.dbo.R_STOCK_PRODUCTOS R
LEFT JOIN Foviedo.dbo.M_PRODUCTOS B ON B.CODIGO_TECNICO = R.CODIGO_TECNICO
LEFT JOIN Foviedo.dbo.P_MARCAS MA ON MA.IDMARCA = B.IDMARCA
WHERE R.IDBODEGA IN ({ph})
  AND ( ISNULL(R.ST_MIN,0) > 0 OR ISNULL(R.ST_MAX,0) > 0
        OR ISNULL(R.ST_CRITICO,0) > 0 OR ISNULL(R.ST_REPOSICION,0) > 0 )
"""

SQL_TRANSITO = """
SELECT
    R.CODIGO_TECNICO,
    CAST(ISNULL(R.ST_DISPONIBLE, 0) AS DECIMAL(18,2)) AS TRANSITO
FROM Foviedo.dbo.R_STOCK_PRODUCTOS R
WHERE R.IDBODEGA = ?
  AND ISNULL(R.ST_DISPONIBLE, 0) <> 0
"""

# Ventas últimos 90 días en bodegas comerciales LC
# IDDOCUMENTO verificados en IDS_REFERENCIA.md:
#   1=FCV, 2=BVN, 35=FVE-exenta, 301=FVE-elect, 316=BVE-elect,
#   335=FVE-exenta-elect, 401=FVP-POS, 405=BVP-POS, 601=FVE-WEB, 605=BVE-WEB
SQL_VENTAS = """
SELECT
    E.CODIGO_TECNICO,
    SUM(ABS(ISNULL(E.CANTIDAD, 0))) AS VTA_TOTAL
FROM Foviedo.dbo.M_DOCUMENTOS_DETALLE E
WHERE E.IDBODEGA IN ({ph})
  AND E.IDDOCUMENTO IN (1, 2, 35, 301, 316, 335, 401, 405, 601, 605)
  AND E.FECHA_EMISION >= DATEADD(day, -90, GETDATE())
GROUP BY E.CODIGO_TECNICO
"""


def generar(cursor):
    ids = list(BODEGAS_LC.keys())
    ph  = ','.join(['?'] * len(ids))

    # 1. Parámetros ERP (ST_MIN, ST_MAX, ST_CRITICO, ST_REPO, ST_DISP, DESCRIPCION, MARCA)
    cursor.execute(SQL_PARAMS.format(ph=ph), *ids)
    prods = {}
    for cod, idbod, smin, smax, scrit, srepo, sdisp, desc, marca in cursor.fetchall():
        cod = str(cod or '').strip().upper()
        if not cod:
            continue
        p = prods.setdefault(cod, {'min': 0, 'max': 0, 'critico': 0, 'repo': 0,
                                    'disp': 0, 'transito': 0, 'vta90': 0,
                                    'desc': '', 'marca': ''})
        p['min']     += int(smin or 0)
        p['max']     += int(smax or 0)
        p['critico'] += int(scrit or 0)
        p['repo']    += int(srepo or 0)
        p['disp']    += int(sdisp or 0)
        if not p['desc'] and desc:
            p['desc'] = str(desc).strip()
        if not p['marca'] and marca:
            p['marca'] = str(marca).strip()
    log(f'[stats] productos con parametros configurados: {len(prods)}')

    # 2. Tránsito (bodega TLC = IDBODEGA {IDBODEGA_TLC})
    try:
        cursor.execute(SQL_TRANSITO, IDBODEGA_TLC)
        for cod, trans in cursor.fetchall():
            cod = str(cod or '').strip().upper()
            if cod in prods:
                prods[cod]['transito'] += int(trans or 0)
        log(f'[stats] tránsito cargado (TLC={IDBODEGA_TLC})')
    except Exception as e:
        log(f'[WARN] tránsito no disponible: {e}')

    # 3. Ventas últimos 90 días (bodegas comerciales SLC/PLC/CLC/GLC)
    try:
        cursor.execute(SQL_VENTAS.format(ph=ph), *ids)
        for cod, vta in cursor.fetchall():
            cod = str(cod or '').strip().upper()
            if cod in prods:
                prods[cod]['vta90'] = int(vta or 0)
        log(f'[stats] ventas 90d cargadas')
    except Exception as e:
        log(f'[WARN] ventas 90d no disponibles: {e}')

    return prods


def main():
    log('[descargar_stock_critico_lc] Iniciando...')
    log(f'[cfg] Bodegas: {", ".join(BODEGAS_LC.values())}')

    if not CRED_FILE.exists() and not ENC_FILE.exists():
        log(f'[ERROR] No existe {CRED_FILE} ni {ENC_FILE}')
        sys.exit(1)

    try:
        conn = conectar()
        log('[DB] Conexion OK')
    except Exception as e:
        log(f'[ERROR] Conexion SQL: {e}')
        sys.exit(1)

    cursor = conn.cursor()
    try:
        prods = generar(cursor)
    except Exception as e:
        log(f'[ERROR] generar: {e}')
        cursor.close(); conn.close()
        sys.exit(1)
    cursor.close(); conn.close()

    out = DATA_DIR / 'stock-critico-lc.json'
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with open(out, 'w', encoding='utf-8') as f:
            json.dump({
                'generado': datetime.datetime.now().isoformat(timespec='seconds'),
                'fuente':   'R_STOCK_PRODUCTOS + M_DOCUMENTOS_DETALLE (SQL) — LC comerciales SLC/PLC/CLC/GLC + tránsito TLC',
                'bodegas':  list(BODEGAS_LC.values()),
                'transito': 'TLC',
                'vta90_dias': 90,
                'productos': prods,
            }, f, ensure_ascii=False, separators=(',', ':'))
    except Exception as e:
        log(f'[ERROR] No se pudo escribir {out}: {e}')
        sys.exit(1)

    log(f'[OK] stock-critico-lc.json: {len(prods)} productos')
    log('[descargar_stock_critico_lc] FINALIZADO')


if __name__ == '__main__':
    main()
