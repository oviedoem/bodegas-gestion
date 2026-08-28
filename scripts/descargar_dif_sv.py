"""
descargar_dif_sv.py  — v1.0  2026-08-27
Analisis Disp vs Fisico para bodegas de facturacion de San Vicente.

Bodegas incluidas:
  PSV=40  Patio San Vicente        IDSUCURSAL=05
  SSV=39  Sala San Vicente         IDSUCURSAL=05
  CSV=44  Calzada San Vicente      IDSUCURSAL=05
  MSV=42  Mermas San Vicente       IDSUCURSAL=05
  DSV=88  Distribucion San Vicente IDSUCURSAL=14

Output:
  E:\\BODEGAS GESTION\\data\\dif-bodegas-sv.json

Estructura por producto:
  bodega, codigo, desc, marca, familia,
  fisico, disp, dif, ped, dvta, dcom,
  tipo (normal | anomalia_jt),
  docs: [{tipo, folio, fecha, cant, obs, usuario}]
"""
import json, datetime, sys, ctypes, ctypes.wintypes
from pathlib import Path
from collections import defaultdict

try:
    import pyodbc
except ImportError:
    print('[ERROR] pyodbc no instalado')
    sys.exit(1)

BASE_DIR = Path(__file__).parent.parent
OUT_PATH = BASE_DIR / 'data' / 'dif-bodegas-sv.json'

# Bodegas de facturacion SV — IDs verificados en P_BODEGAS 2026-08-27
BODEGAS_SV = [
    {'id': 40, 'simbolo': 'PSV',  'nombre': 'Patio San Vicente',         'idsucursal': '05'},
    {'id': 39, 'simbolo': 'SSV',  'nombre': 'Sala San Vicente',          'idsucursal': '05'},
    {'id': 44, 'simbolo': 'CSV',  'nombre': 'Calzada San Vicente',       'idsucursal': '05'},
    {'id': 42, 'simbolo': 'MSV',  'nombre': 'Mermas San Vicente',        'idsucursal': '05'},
    {'id': 88, 'simbolo': 'DSV',  'nombre': 'Distribucion San Vicente',  'idsucursal': '14'},
]

# Tipos de documento que generan compromiso (St_Pedido, St_DVen, St_DCom)
DOCS_COMPROMISO = (
    'NVM','VMP','VMN',          # Notas de venta → ST_PEDIDO
    'GME','GDF','GCE','GDV',    # Guias despacho → ST_DEVENGADOVENTA
    'OC', 'OCL', 'OCE',         # Ordenes compra → ST_DEVENGADOCOMPRA
    'GRT','GIB',                 # Traslados — posible anomalia JT
)

# ─── CREDENCIALES (igual que descargar_bodegas_sql.py) ────────────────────────

CRED_ENC = Path(r'E:\config\credenciales_db.enc')
CRED_INI = Path(r'E:\ferreteria-oviedo\credenciales_db.ini')

def leer_credenciales():
    if CRED_ENC.exists():
        try:
            import base64
            datos = CRED_ENC.read_bytes()
            lib = ctypes.WinDLL('crypt32')
            class DATA_BLOB(ctypes.Structure):
                _fields_ = [('cbData', ctypes.wintypes.DWORD),
                             ('pbData', ctypes.POINTER(ctypes.c_char))]
            blob_in = DATA_BLOB(len(datos), ctypes.cast(ctypes.c_char_p(datos), ctypes.POINTER(ctypes.c_char)))
            blob_out = DATA_BLOB()
            ok = lib.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out))
            if ok:
                plain = ctypes.string_at(blob_out.pbData, blob_out.cbData)
                d = json.loads(plain.decode('utf-8'))
                return d['server'], d['database'], d['user'], d['password']
        except Exception as e:
            print(f'[WARN] credenciales_db.enc: {e} — usando .ini')
    if CRED_INI.exists():
        import configparser
        cfg = configparser.ConfigParser()
        cfg.read(str(CRED_INI))
        sec = cfg['DB'] if 'DB' in cfg else (cfg['database'] if 'database' in cfg else cfg[cfg.sections()[0]])
        return sec['server'], sec['database'], sec.get('user', sec.get('username','')), sec['password']
    print('[ERROR] No se encontro credenciales_db.enc ni credenciales_db.ini')
    sys.exit(1)

def conectar():
    server, database, user, password = leer_credenciales()
    conn_str = (
        f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};'
        f'UID={user};PWD={password};TrustServerCertificate=yes;'
    )
    return pyodbc.connect(conn_str, timeout=30)

# ─── QUERY STOCK ──────────────────────────────────────────────────────────────

SQL_STOCK = """
SELECT
    A.CODIGO_TECNICO,
    ISNULL(B.DESCRIPCION, ''),
    ISNULL(MA.MARCA, ''),
    ISNULL(FA.FAMILIA, ''),
    ISNULL(HF.HIPERFAMILIA, ''),
    CAST(ISNULL(A.ST_FISICO,             0) AS DECIMAL(18,2)),
    CAST(ISNULL(A.ST_DISPONIBLE,         0) AS DECIMAL(18,2)),
    CAST(ISNULL(A.ST_PEDIDO,             0) AS DECIMAL(18,2)),
    CAST(ISNULL(A.ST_DEVENGADOVENTA,     0) AS DECIMAL(18,2)),
    CAST(ISNULL(A.ST_DEVENGADOCOMPRA,    0) AS DECIMAL(18,2)),
    CAST(ISNULL(A.ST_CONTABLE,           0) AS DECIMAL(18,2)),
    CAST(ISNULL(A.ST_TRANSITO,           0) AS DECIMAL(18,2)),
    CAST(ISNULL(A.ST_MIN,                0) AS DECIMAL(18,2)),
    CAST(ISNULL(A.ST_MAX,                0) AS DECIMAL(18,2)),
    CAST(ISNULL(A.ST_CRITICO,            0) AS DECIMAL(18,2)),
    CAST(ISNULL(A.ST_REPOSICION,         0) AS DECIMAL(18,2)),
    CAST(ISNULL(A.COSTOPROMEDIOBODEGA,   0) AS DECIMAL(18,2)),
    ISNULL(CONVERT(VARCHAR(10), A.FECHAPROMEDIOBODEGA, 120), '')
FROM Foviedo.dbo.R_STOCK_PRODUCTOS A
INNER JOIN Foviedo.dbo.M_PRODUCTOS B ON B.CODIGO_TECNICO = A.CODIGO_TECNICO
LEFT  JOIN Foviedo.dbo.P_MARCAS MA ON MA.IDMARCA = B.IDMARCA
LEFT  JOIN Foviedo.dbo.P_FAMILIAS FA
    ON FA.IDFAMILIA = B.IDFAMILIA AND FA.IDHIPERFAMILIA = B.IDHIPERFAMILIA
LEFT  JOIN Foviedo.dbo.P_HIPERFAMILIAS HF ON HF.IDHIPERFAMILIA = B.IDHIPERFAMILIA
WHERE A.IDBODEGA = ?
  AND A.IDSUCURSAL = ?
  AND (ISNULL(A.ST_FISICO,0) <> 0 OR ISNULL(A.ST_DISPONIBLE,0) <> 0)
ORDER BY A.CODIGO_TECNICO
"""

# ─── QUERY DOCUMENTOS (drill-down) ────────────────────────────────────────────

SQL_DOCS = """
SELECT TOP 50
    MD.DOC,
    ISNULL(NULLIF(CAST(N.NUMERO AS VARCHAR(20)),''), CAST(N.IDNUMERO AS VARCHAR(20))) AS FOLIO,
    CAST(N.IDNUMERO AS VARCHAR(20))                AS IDNUMERO,
    CONVERT(VARCHAR(19), N.FECHA_EMISION, 120)     AS FECHA,
    CAST(ISNULL(N.CANTIDAD, 0) AS DECIMAL(18,2))   AS CANTIDAD,
    ISNULL(ENC.IDRESPONZABLE, ISNULL(ENC.IDVENDEDOR, '')) AS USUARIO,
    ISNULL(OBS.OBSERVACION_IMPRESA, '')            AS OBS
FROM Foviedo.dbo.M_DOCUMENTOS_DETALLE N
INNER JOIN Foviedo.dbo.M_DOCUMENTOS MD
    ON MD.IDDOCUMENTO = N.IDDOCUMENTO
OUTER APPLY (
    SELECT TOP 1 ENC2.IDRESPONZABLE, ENC2.IDVENDEDOR
    FROM Foviedo.dbo.M_DOCUMENTOS_ENCABEZADO ENC2
    WHERE ENC2.IDDOCUMENTO = N.IDDOCUMENTO
      AND ENC2.IDNUMERO    = N.IDNUMERO
) ENC
OUTER APPLY (
    SELECT TOP 1 G2.OBSERVACION_IMPRESA
    FROM Foviedo.dbo.M_Documentos_Encabezado_Observacion G2
    WHERE G2.IDDOCUMENTO = N.IDDOCUMENTO
      AND G2.IDNUMERO    = N.IDNUMERO
) OBS
WHERE N.IDBODEGA       = ?
  AND N.CODIGO_TECNICO = ?
  AND MD.DOC IN (
    'NVM','VMP','VMN',
    'BVE','FVE','BVN','BEL','FEL',
    'GME','GDF','GCE','GDV','GDC',
    'OC','OCL','OCE','FCN',
    'GRC','GRS',
    'GET','GRT','GIB','GTS','GST',
    'GII','GEI',
    'Gdc','NCE',
    'GBR','GRP','GRI','GRN','GIN','GRE'
  )
ORDER BY N.FECHA_EMISION DESC
"""

# BVE/FVE asociada al IDNUMERO de la VMN — sin filtro IDBODEGA (son docs de sucursal)
SQL_BVE = """
SELECT TOP 5
    MD.DOC,
    ISNULL(NULLIF(CAST(N.NUMERO AS VARCHAR(20)),''), CAST(N.IDNUMERO AS VARCHAR(20))) AS FOLIO,
    CONVERT(VARCHAR(19), N.FECHA_EMISION, 120) AS FECHA,
    CAST(ISNULL(N.CANTIDAD, 0) AS DECIMAL(18,2)) AS CANTIDAD
FROM Foviedo.dbo.M_DOCUMENTOS_DETALLE N
INNER JOIN Foviedo.dbo.M_DOCUMENTOS MD ON MD.IDDOCUMENTO = N.IDDOCUMENTO
WHERE N.CODIGO_TECNICO = ?
  AND N.IDNUMERO IN ({placeholders})
  AND MD.DOC IN ('BVE','FVE','BVN','BEL','FEL')
ORDER BY N.FECHA_EMISION DESC
"""

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print('[dif-sv] Iniciando analisis Disp vs Fisico San Vicente...')
    conn = conectar()
    print('[DB] Conexion OK')
    cur  = conn.cursor()

    productos = []
    totales_por_bodega = {}

    for bod in BODEGAS_SV:
        idbodega   = bod['id']
        idsucursal = bod['idsucursal']
        simbolo    = bod['simbolo']
        nombre     = bod['nombre']

        print(f'  [{simbolo}] {nombre} (id={idbodega}, suc={idsucursal})... ', end='', flush=True)
        cur.execute(SQL_STOCK, idbodega, idsucursal)
        rows = cur.fetchall()
        n = 0

        for row in rows:
            codigo     = str(row[0]  or '').strip()
            desc       = str(row[1]  or '').strip()
            marca      = str(row[2]  or '').strip()
            familia    = str(row[3]  or '').strip()
            hiperfam   = str(row[4]  or '').strip()
            fisico     = float(row[5])
            disp       = float(row[6])
            ped        = float(row[7])
            dvta       = float(row[8])
            dcom       = float(row[9])
            contable   = float(row[10])
            transito   = float(row[11])
            st_min     = float(row[12])
            st_max     = float(row[13])
            st_critico = float(row[14])
            st_repo    = float(row[15])
            costo_prom = float(row[16])
            fecha_costo= str(row[17] or '').strip()
            dif        = round(fisico - disp, 2)

            if abs(dif) < 0.001 and fisico == 0:
                continue  # sin stock ni diferencia, ignorar

            # Clasificacion
            if dif < 0:
                tipo = 'anomalia_jt'  # Disp > Fis: GRT/GIB sin 2 paso JustWeb
            elif dif == 0:
                tipo = 'cuadrado'
            else:
                tipo = 'normal'

            prod = {
                'bodega':     simbolo,
                'idbodega':   idbodega,
                'codigo':     codigo,
                'desc':       desc,
                'marca':      marca,
                'familia':    familia,
                'hiperfam':   hiperfam,
                'fisico':     fisico,
                'disp':       disp,
                'dif':        dif,
                'ped':        ped,
                'dvta':       dvta,
                'dcom':       dcom,
                'contable':   contable,
                'transito':   transito,
                'st_min':     st_min,
                'st_max':     st_max,
                'st_critico': st_critico,
                'st_repo':    st_repo,
                'costo_prom': costo_prom,
                'fecha_costo':fecha_costo,
                'tipo':       tipo,
                'docs':       [],
            }

            # Drill-down documentos solo si hay diferencia
            if abs(dif) > 0.001:
                try:
                    cur.execute(SQL_DOCS, idbodega, codigo)
                    for dr in cur.fetchall():
                        prod['docs'].append({
                            'tipo':    str(dr[0] or '').strip(),
                            'folio':   str(dr[1] or '').strip(),
                            'idnum':   str(dr[2] or '').strip(),
                            'fecha':   str(dr[3] or '').strip(),
                            'cant':    float(dr[4]),
                            'usuario': str(dr[5] or '').strip(),
                            'obs':     str(dr[6] or '').strip(),
                            'bve':     [],
                        })
                except Exception as e:
                    print(f'\n  [WARN] docs {codigo}: {e}')

                # Buscar BVE/FVE asociada a cada VMN por IDNUMERO
                vmn_docs = [d for d in prod['docs'] if d['tipo'] in ('NVM','VMN','VMP') and d['idnum']]
                if vmn_docs:
                    idnums = [d['idnum'] for d in vmn_docs]
                    ph = ','.join(['?']*len(idnums))
                    try:
                        cur.execute(SQL_BVE.format(placeholders=ph), codigo, *idnums)
                        bve_rows = cur.fetchall()
                        # Asociar cada BVE al VMN con mismo idnum
                        bve_by_idnum = defaultdict(list)
                        # BVE no filtra por idnum exacto — asociar al VMN de cant similar
                        for br in bve_rows:
                            bve_entry = {
                                'tipo':  str(br[0] or '').strip(),
                                'folio': str(br[1] or '').strip(),
                                'fecha': str(br[2] or '').strip(),
                                'cant':  float(br[3]),
                            }
                            # Agregar al primer VMN con misma cant
                            for d in vmn_docs:
                                if abs(d['cant'] - bve_entry['cant']) < 0.001 and not d['bve']:
                                    d['bve'].append(bve_entry)
                                    break
                            else:
                                # Si no coincide cant, agregar al primero sin BVE
                                for d in vmn_docs:
                                    if not d['bve']:
                                        d['bve'].append(bve_entry)
                                        break
                    except Exception as e:
                        print(f'\n  [WARN] bve {codigo}: {e}')

            productos.append(prod)
            n += 1

        totales_por_bodega[simbolo] = n
        print(f'{n} productos')

    cur.close()
    conn.close()

    # Estadisticas
    total      = len(productos)
    con_dif    = sum(1 for p in productos if abs(p['dif']) > 0.001)
    anomalias  = sum(1 for p in productos if p['tipo'] == 'anomalia_jt')

    out = {
        'generado':   datetime.datetime.now().isoformat(timespec='seconds'),
        'sucursal':   'San Vicente',
        'bodegas':    [{'simbolo': b['simbolo'], 'idbodega': b['id'], 'nombre': b['nombre']} for b in BODEGAS_SV],
        'totales':    totales_por_bodega,
        'total':      total,
        'con_dif':    con_dif,
        'anomalias':  anomalias,
        'productos':  productos,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    kb = OUT_PATH.stat().st_size // 1024
    print(f'\n[OK] {OUT_PATH.name}: {total} productos, {con_dif} con diferencia, {anomalias} anomalias JT ({kb} KB)')

if __name__ == '__main__':
    main()
