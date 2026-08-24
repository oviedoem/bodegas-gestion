"""
descargar_bodegas_sql.py  — v1.0  2026-08-24
Descarga stock de TODAS las bodegas/sucursales directamente desde SQL Server (pyodbc).
Replica modBodegas.bas (VBA) sin necesitar XLSM — conexion directa Python -> SQL.

Campos completos por registro:
  bodega, bodegaNombre, tipoDoc, tipoDocNombre, folio, codigoTecnico, descripcion,
  disp, fisico, cantidad, costo, fechaRegistro, fechaRegistroIso, diasAntiguedad,
  observacion, usuario, estacionPc, fechaRegistroSistema,
  hiperfamilia, familia, subfamilia, marca

Output:
  E:\\BODEGAS GESTION\\bodegas_gestion.json   (EM / SV / LC / LT + CD compartidas)
  E:\\BODEGAS GESTION\\bodegas_ir_otras.json  (Isabel Riquelme)

Uso:
  python descargar_bodegas_sql.py            # todas las bodegas
  python descargar_bodegas_sql.py SV         # solo San Vicente
  python descargar_bodegas_sql.py EM SV LC   # varias sucursales

Anti-retroceso: aborta si nuevo total < 50% del anterior (por sucursal).
"""
import json, datetime, sys, ctypes, ctypes.wintypes
from pathlib import Path
from collections import defaultdict

try:
    import pyodbc
except ImportError:
    print('[ERROR] pyodbc no instalado: pip install pyodbc')
    sys.exit(1)

BASE_DIR    = Path(__file__).parent.parent        # E:\BODEGAS GESTION\
OUT_GESTION = BASE_DIR / 'bodegas_gestion.json'
OUT_IR      = BASE_DIR / 'bodegas_ir_otras.json'

CRED_ENC = Path(r'E:\config\credenciales_db.enc')
CRED_INI = Path(r'E:\ferreteria-oviedo\credenciales_db.ini')

DOC_NOMBRES = {
    'GRT': 'Guia Recepcion Traslado',
    'GIB': 'Guia Ingreso Entre Bodegas',
    'GII': 'Guia Ingreso Inventario',
    'GME': 'Guia Elect. Despacho Factura',
    'Gdc': 'Guia Devolucion Cliente',
    'GRC': 'Guia Recepcion Compra',
    'GTS': 'Guia Traslados Entre Sucursales',
    'GST': 'Solicitud de Traslado',
    'GEI': 'Guia Egreso Inventario / Merma',
    'GDV': 'Guia Despacho Venta',
    'GDC': 'Guia Despacho Cliente',
}

# Mapa completo — identico a modBodegas.bas y xlsm_a_json_bodegas.py
# CONSV = simbolo interno para Consumo SV (evita colision con CSV=Calzada SV)
GRUPOS = [
    {
        'clave': 'EM', 'idSucursal': '04', 'nombre': 'El Manzano', 'destino': 'gestion',
        'bodegas': [
            {'id': 28, 'simbolo': 'GEM', 'nombre': 'Gestion El Manzano',   'idsucursal': '04'},
            {'id': 29, 'simbolo': 'MEM', 'nombre': 'Mermas El Manzano',    'idsucursal': '04'},
            {'id': 55, 'simbolo': 'RCE', 'nombre': 'Recepcion El Manzano', 'idsucursal': '04'},
            {'id': 72, 'simbolo': 'IEM', 'nombre': 'Ingreso El Manzano',   'idsucursal': '04'},
            {'id': 46, 'simbolo': 'TEM', 'nombre': 'Transito El Manzano',  'idsucursal': '04'},
            {'id': 83, 'simbolo': 'EEM', 'nombre': 'Exhibicion El Manzano','idsucursal': '04'},
        ],
    },
    {
        'clave': 'SV', 'idSucursal': '05', 'nombre': 'San Vicente', 'destino': 'gestion',
        'bodegas': [
            {'id': 41, 'simbolo': 'GSV',  'nombre': 'Gestion San Vicente',      'idsucursal': '05'},
            {'id': 42, 'simbolo': 'MSV',  'nombre': 'Mermas San Vicente',        'idsucursal': '05'},
            {'id': 56, 'simbolo': 'RSV',  'nombre': 'Recepcion San Vicente',     'idsucursal': '05'},
            {'id': 70, 'simbolo': 'ISV',  'nombre': 'Ingreso San Vicente',       'idsucursal': '05'},
            {'id': 45, 'simbolo': 'TSV',  'nombre': 'Transito San Vicente',      'idsucursal': '05'},
            {'id': 44, 'simbolo': 'CSV',  'nombre': 'Calzada San Vicente',       'idsucursal': '05'},
            {'id': 88, 'simbolo': 'DSV',  'nombre': 'Distribucion San Vicente',  'idsucursal': '14'},
            {'id': 95, 'simbolo': 'ESV',  'nombre': 'Exhibicion San Vicente',    'idsucursal': '05'},
            {'id': 43, 'simbolo': 'CONSV','nombre': 'Consumo San Vicente',       'idsucursal': '05'},
        ],
    },
    {
        'clave': 'LC', 'idSucursal': '06', 'nombre': 'Las Cabras', 'destino': 'gestion',
        'bodegas': [
            {'id': 37, 'simbolo': 'GLC', 'nombre': 'Gestion Las Cabras',   'idsucursal': '06'},
            {'id': 38, 'simbolo': 'MLC', 'nombre': 'Mermas Las Cabras',    'idsucursal': '06'},
            {'id': 57, 'simbolo': 'RLC', 'nombre': 'Recepcion Las Cabras', 'idsucursal': '06'},
            {'id': 71, 'simbolo': 'ILC', 'nombre': 'Ingreso Las Cabras',   'idsucursal': '06'},
            {'id': 16, 'simbolo': 'TLC', 'nombre': 'Transito Las Cabras',  'idsucursal': '06'},
            {'id': 35, 'simbolo': 'CLC', 'nombre': 'Calzada Las Cabras',   'idsucursal': '06'},
            {'id': 91, 'simbolo': 'GFL', 'nombre': 'Garantia Las Cabras',  'idsucursal': '06'},
            {'id': 96, 'simbolo': 'ELC', 'nombre': 'Exhibicion Las Cabras','idsucursal': '06'},
            {'id': 97, 'simbolo': 'VLC', 'nombre': 'Volumen Las Cabras',   'idsucursal': '06'},
        ],
    },
    {
        'clave': 'LT', 'idSucursal': '11', 'nombre': 'Litueche', 'destino': 'gestion',
        'bodegas': [
            {'id': 63, 'simbolo': 'GLE', 'nombre': 'Gestion Litueche',    'idsucursal': '11'},
            {'id': 76, 'simbolo': 'MLE', 'nombre': 'Mermas Litueche',     'idsucursal': '11'},
            {'id': 74, 'simbolo': 'ILE', 'nombre': 'Ingreso Litueche',    'idsucursal': '11'},
            {'id': 59, 'simbolo': 'TLE', 'nombre': 'Transito Litueche',   'idsucursal': '11'},
            {'id': 78, 'simbolo': 'CLT', 'nombre': 'Calzada Litueche',    'idsucursal': '11'},
            {'id': 79, 'simbolo': 'DLT', 'nombre': 'Distribucion Litueche','idsucursal': '09'},
            {'id': 64, 'simbolo': 'ELE', 'nombre': 'Exhibicion Litueche', 'idsucursal': '11'},
        ],
    },
    {
        'clave': 'IR', 'idSucursal': '02', 'nombre': 'Isabel Riquelme', 'destino': 'ir',
        'bodegas': [
            {'id':  5, 'simbolo': 'CAL', 'nombre': 'Calzada',                   'idsucursal': '02'},
            {'id':  6, 'simbolo': 'SER', 'nombre': 'Servicio Tecnico',           'idsucursal': '02'},
            {'id': 25, 'simbolo': 'WEB', 'nombre': 'Retiro Web Santiago',        'idsucursal': '02'},
            {'id': 30, 'simbolo': 'GO',  'nombre': 'Gestion Isabel Riquelme',    'idsucursal': '02'},
            {'id': 53, 'simbolo': 'GAR', 'nombre': 'Garantia Santiago',          'idsucursal': '02'},
            {'id': 69, 'simbolo': 'IIR', 'nombre': 'Ingreso Isabel Riquelme',    'idsucursal': '02'},
            {'id': 77, 'simbolo': 'BMC', 'nombre': 'Marticorena Stgo',           'idsucursal': '02'},
            {'id': 92, 'simbolo': 'RST', 'nombre': 'Recepcion Santiago',         'idsucursal': '02'},
            {'id': 99, 'simbolo': 'HEL', 'nombre': 'Herramientas Electricas',    'idsucursal': '02'},
            {'id': 85, 'simbolo': 'EIR', 'nombre': 'Exhibicion Isabel Riquelme', 'idsucursal': '02'},
        ],
    },
    {
        'clave': 'CD', 'idSucursal': 'COMPARTIDAS', 'nombre': 'Compartidas/CD', 'destino': 'gestion',
        'bodegas': [
            {'id': 23, 'simbolo': 'CD',  'nombre': 'Centro de Distribucion',        'idsucursal': '08'},
            {'id':  7, 'simbolo': 'XCD', 'nombre': 'CrossDock Centro Distribucion', 'idsucursal': '08'},
            {'id': 27, 'simbolo': 'GCD', 'nombre': 'Gestion CD',                    'idsucursal': '08'},
            {'id': 73, 'simbolo': 'ICD', 'nombre': 'Ingreso Centro Distribucion',   'idsucursal': '08'},
            {'id': 26, 'simbolo': 'MCD', 'nombre': 'Mermas CD',                     'idsucursal': '08'},
            {'id': 54, 'simbolo': 'RCD', 'nombre': 'Recepcion CD',                  'idsucursal': '08'},
            {'id': 67, 'simbolo': 'TCD', 'nombre': 'Transito CD',                   'idsucursal': '08'},
            {'id': 98, 'simbolo': 'BDP', 'nombre': 'Despacho Proveedor',            'idsucursal': '09'},
            {'id': 84, 'simbolo': 'REM', 'nombre': 'Remate',                        'idsucursal': '01'},
            {'id': 36, 'simbolo': 'MKT', 'nombre': 'Marketing',                     'idsucursal': '01'},
        ],
    },
]

SQL_BODEGA = """
WITH ENTRADAS AS (
    SELECT E.IDBODEGA, E.CODIGO_TECNICO, E.IDSUCURSAL, E.IDDOCUMENTO, E.IDNUMERO,
           E.NUMERO, E.FECHA_EMISION, E.CANTIDAD, MD.DOC
    FROM Foviedo.dbo.M_DOCUMENTOS_DETALLE E
    INNER JOIN Foviedo.dbo.M_DOCUMENTOS MD ON MD.IDDOCUMENTO = E.IDDOCUMENTO
    WHERE E.IDBODEGA = ?
      AND MD.DOC IN ('GRC','GRT','GME','GIB','Gdc','GBR','GRP','GRI','GRN','GIN','GDC','GDV','GII','GTS')
)
SELECT
    D.SIMBOLO_BODEGA,
    N.DOC,
    N.NUMERO,
    A.CODIGO_TECNICO,
    B.DESCRIPCION,
    CAST(ISNULL(A.ST_FISICO, 0) - ISNULL(A.ST_PEDIDO, 0) AS DECIMAL(18,2)),
    CAST(ISNULL(A.ST_FISICO, 0) AS DECIMAL(18,2)),
    CAST(ISNULL(N.CANTIDAD,  0) AS DECIMAL(18,2)),
    N.FECHA_EMISION,
    ISNULL(G.OBSERVACION_IMPRESA, ''),
    CAST(ISNULL(B.COSTO_PROMEDIO, 0) AS DECIMAL(18,2)),
    ISNULL(CONVERT(NVARCHAR(20), ENC.FECHA_REGISTRO, 120), ''),
    ISNULL(ENC.IDRESPONZABLE, ISNULL(ENC.AUTORIZADO_FIRMA, ISNULL(ENC.IDVENDEDOR, ''))),
    ISNULL(ENC.ESTACION, ''),
    ISNULL(HF.HIPERFAMILIA, ''),
    ISNULL(FA.FAMILIA, ''),
    ISNULL(SF.SUBFAMILIA, ''),
    ISNULL(MA.MARCA, '')
FROM Foviedo.dbo.R_STOCK_PRODUCTOS A
INNER JOIN Foviedo.dbo.M_PRODUCTOS B ON B.CODIGO_TECNICO = A.CODIGO_TECNICO
INNER JOIN Foviedo.dbo.P_BODEGAS D ON A.IDBODEGA = D.IDBODEGA
LEFT JOIN Foviedo.dbo.P_HIPERFAMILIAS HF ON HF.IDHIPERFAMILIA = B.IDHIPERFAMILIA
LEFT JOIN Foviedo.dbo.P_FAMILIAS FA
    ON FA.IDFAMILIA = B.IDFAMILIA AND FA.IDHIPERFAMILIA = B.IDHIPERFAMILIA
LEFT JOIN Foviedo.dbo.P_SUBFAMILIAS SF
    ON SF.IDSUBFAMILIA = B.IDSUBFAMILIA AND SF.IDFAMILIA = B.IDFAMILIA AND SF.IDHIPERFAMILIA = B.IDHIPERFAMILIA
LEFT JOIN Foviedo.dbo.P_MARCAS MA ON MA.IDMARCA = B.IDMARCA
INNER JOIN ENTRADAS N
    ON N.IDBODEGA = A.IDBODEGA AND N.CODIGO_TECNICO = A.CODIGO_TECNICO
OUTER APPLY (
    SELECT TOP 1 G2.OBSERVACION_IMPRESA
    FROM Foviedo.dbo.M_Documentos_Encabezado_Observacion G2
    WHERE G2.IDDOCUMENTO = N.IDDOCUMENTO AND G2.IDNUMERO = N.IDNUMERO
    ORDER BY CASE WHEN G2.IDSUCURSAL = A.IDSUCURSAL THEN 0 ELSE 1 END
) G
OUTER APPLY (
    SELECT TOP 1 ENC2.FECHA_REGISTRO, ENC2.IDRESPONZABLE, ENC2.AUTORIZADO_FIRMA,
                 ENC2.IDVENDEDOR, ENC2.ESTACION
    FROM Foviedo.dbo.M_DOCUMENTOS_ENCABEZADO ENC2
    WHERE ENC2.IDDOCUMENTO = N.IDDOCUMENTO AND ENC2.IDNUMERO = N.IDNUMERO
    ORDER BY CASE WHEN ENC2.IDSUCURSAL = A.IDSUCURSAL THEN 0 ELSE 1 END
) ENC
WHERE A.IDBODEGA = ?
  AND A.IDSUCURSAL = ?
  AND ISNULL(A.ST_FISICO, 0) <> 0
ORDER BY N.FECHA_EMISION DESC
"""


# ─── CREDENCIALES ──────────────────────────────────────────────────────────────

def leer_credenciales():
    """Lee credenciales SQL. Primero DPAPI enc, fallback ini."""
    if CRED_ENC.exists():
        try:
            class _BLOB(ctypes.Structure):
                _fields_ = [('cbData', ctypes.wintypes.DWORD),
                             ('pbData', ctypes.POINTER(ctypes.c_char))]
            raw = CRED_ENC.read_bytes()
            buf = ctypes.create_string_buffer(raw)
            blob_in = _BLOB(len(raw), buf)
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
            print(f'[WARN] credenciales_db.enc: {e} — usando .ini')

    if CRED_INI.exists():
        import configparser
        cfg = configparser.ConfigParser()
        cfg.read(str(CRED_INI), encoding='utf-8')
        return (cfg['DB']['server'], cfg['DB']['database'],
                cfg['DB']['user'],   cfg['DB']['password'])

    print('[ERROR] No se encontro credenciales_db.enc ni credenciales_db.ini')
    sys.exit(1)


def conectar():
    server, database, user, password = leer_credenciales()
    conn_str = (
        f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};'
        f'UID={user};PWD={password};TrustServerCertificate=yes;'
    )
    return pyodbc.connect(conn_str, timeout=30)


# ─── DEDUPLICAR Y ACUMULAR ────────────────────────────────────────────────────

def _deduplicar_y_acumular(registros):
    """
    Paso 1 — Dedup: GRT manda; GME/GIB mismo dia que GRT → excluir;
              GIB con GRT anterior → excluir.
    Paso 2 — Acumular de mas nuevo a mas antiguo hasta cubrir ST_FISICO.
    Paso 3 — Conservar solo el mas reciente por codigoTecnico (min diasAntiguedad).
    """
    grupos = defaultdict(list)
    for r in registros:
        grupos[r['codigoTecnico']].append(r)

    resultado = []
    for cod, docs in grupos.items():
        total_fisico = docs[0].get('fisico', 0) if docs else 0
        if total_fisico == 0:
            continue

        grt_fechas   = {d['_fechaRaw'] for d in docs if d['tipoDoc'] == 'GRT'}
        earliest_grt = min(grt_fechas) if grt_fechas else None

        dedup = []
        for doc in docs:
            tipo  = doc['tipoDoc']
            fecha = doc['_fechaRaw']
            if tipo == 'GRT':
                dedup.append(doc)
            elif tipo in ('GME', 'GIB'):
                if fecha in grt_fechas:
                    continue
                if tipo == 'GIB' and earliest_grt is not None and earliest_grt <= fecha:
                    continue
                dedup.append(doc)
            else:
                dedup.append(doc)

        if total_fisico > 0:
            acum = 0
            for doc in dedup:
                if acum >= total_fisico:
                    break
                acum += doc.get('cantidad', 0)
                resultado.append(doc)
        else:
            if dedup:
                resultado.append(dedup[0])

    visto = {}
    for doc in resultado:
        cod  = doc['codigoTecnico']
        dias = doc.get('diasAntiguedad') if doc.get('diasAntiguedad') is not None else 999999
        prev = visto[cod].get('diasAntiguedad') if cod in visto and visto[cod].get('diasAntiguedad') is not None else 999999
        if cod not in visto or dias < prev:
            visto[cod] = doc

    for r in visto.values():
        r.pop('_fechaRaw', None)

    return list(visto.values())


# ─── ANTI-RETROCESO ───────────────────────────────────────────────────────────

def anti_retroceso(out_path, nuevo_total, etiqueta, nombre_sucursal=None):
    """Compara nuevo_total contra el total de esa sucursal en el JSON anterior."""
    if out_path.exists():
        try:
            ant = json.loads(out_path.read_text(encoding='utf-8'))
            if nombre_sucursal:
                # Buscar el total de esa sucursal especifica en el JSON anterior
                sucs = ant.get('sucursales', [])
                match = next((s for s in sucs if s.get('nombre') == nombre_sucursal), None)
                ant_total = match.get('total', 0) if match else 0
            else:
                ant_total = ant.get('total', 0)
            if ant_total > 0 and nuevo_total < ant_total * 0.5:
                print(f'[ABORTADO] {etiqueta}: {nuevo_total} vs {ant_total} anteriores '
                      f'(caida >50%). Se conserva JSON anterior.')
                return False
        except Exception:
            pass
    return True


# ─── DESCARGA UNA BODEGA ─────────────────────────────────────────────────────

def descargar_bodega(cursor, bod):
    idbodega   = bod['id']
    idsucursal = bod['idsucursal']
    simbolo    = bod['simbolo']
    nombre     = bod['nombre']

    print(f'  [{simbolo:5s}] {nombre} (id={idbodega}, suc={idsucursal})... ', end='', flush=True)
    cursor.execute(SQL_BODEGA, idbodega, idbodega, idsucursal)

    hoy = datetime.date.today()
    registros = []

    for row in cursor.fetchall():
        tipo_doc  = str(row[1] or '').strip()
        folio     = str(row[2] or '').strip()
        cod_tec   = str(row[3] or '').strip()
        desc      = str(row[4] or '').strip()
        disp      = float(row[5] or 0)
        fisico    = float(row[6] or 0)
        cantidad  = float(row[7] or 0)
        fecha_em  = row[8]
        obs       = str(row[9] or '').strip()
        costo     = round(float(row[10] or 0))
        fecha_sis = str(row[11] or '').strip()
        usuario   = str(row[12] or '').strip()
        estacion  = str(row[13] or '').strip()
        hiper     = str(row[14] or '').strip()
        fam       = str(row[15] or '').strip()
        sub       = str(row[16] or '').strip()
        marca     = str(row[17] or '').strip()

        if fecha_em and hasattr(fecha_em, 'date'):
            fecha_date = fecha_em.date()
            dias       = (hoy - fecha_date).days
            fecha_raw  = fecha_date.isoformat()
            fecha_str  = fecha_date.strftime('%d/%m/%Y')
        elif isinstance(fecha_em, datetime.date):
            dias       = (hoy - fecha_em).days
            fecha_raw  = fecha_em.isoformat()
            fecha_str  = fecha_em.strftime('%d/%m/%Y')
        else:
            dias = None; fecha_raw = ''; fecha_str = ''

        registros.append({
            'bodega':               simbolo,
            'bodegaNombre':         nombre,
            'tipoDoc':              tipo_doc,
            'tipoDocNombre':        DOC_NOMBRES.get(tipo_doc, tipo_doc),
            'folio':                folio,
            'codigoTecnico':        cod_tec,
            'descripcion':          desc,
            'disp':                 disp,
            'fisico':               fisico,
            'cantidad':             cantidad,
            'costo':                costo,
            'fechaRegistro':        fecha_str,
            'fechaRegistroIso':     fecha_raw,
            'diasAntiguedad':       dias,
            'observacion':          obs,
            'usuario':              usuario,
            'estacionPc':           estacion,
            'fechaRegistroSistema': fecha_sis,
            'hiperfamilia':         hiper,
            'familia':              fam,
            'subfamilia':           sub,
            'marca':                marca,
            '_fechaRaw':            fecha_raw,
        })

    dedup = _deduplicar_y_acumular(registros)
    print(f'{len(dedup)} codigos (de {len(registros)} docs)')
    return dedup


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    # Filtro de sucursales por argumento (ej. python script.py SV EM)
    filtro = [a.upper() for a in sys.argv[1:]] if len(sys.argv) > 1 else []
    grupos_activos = [g for g in GRUPOS if not filtro or g['clave'] in filtro]

    if not grupos_activos:
        print(f'[ERROR] Claves invalidas: {filtro}')
        print(f'Validas: {[g["clave"] for g in GRUPOS]}')
        sys.exit(1)

    print('[descargar_bodegas_sql] Conectando a SQL Server...')
    try:
        conn = conectar()
        print('[DB] Conexion OK')
    except Exception as e:
        print(f'[ERROR] Conexion: {e}')
        sys.exit(1)

    cursor = conn.cursor()
    cursor.execute('SET NOCOUNT ON')

    hoy = datetime.date.today().isoformat()

    # Estructuras de salida
    sucursales_gestion = []
    compartidas_registros = []
    total_gestion = 0
    bodegas_ir = []
    total_ir = 0

    for grupo in grupos_activos:
        print(f'\n=== {grupo["clave"]} — {grupo["nombre"]} ===')
        registros_grupo = []

        for bod in grupo['bodegas']:
            recs = descargar_bodega(cursor, bod)
            registros_grupo.extend(recs)

        n = len(registros_grupo)

        if grupo['destino'] == 'ir':
            if not anti_retroceso(OUT_IR, n, grupo['nombre'], grupo['nombre']):
                continue
            bodegas_ir.extend(registros_grupo)
            total_ir += n
            print(f'  IR total: {n} codigos')

        elif grupo['idSucursal'] == 'COMPARTIDAS':
            compartidas_registros = registros_grupo
            total_gestion += n
            print(f'  CD total: {n} codigos')

        else:
            if not anti_retroceso(OUT_GESTION, n, grupo['nombre'], grupo['nombre']):
                continue
            registros_grupo.sort(
                key=lambda r: r.get('diasAntiguedad') if r.get('diasAntiguedad') is not None else -1,
                reverse=True,
            )
            sucursales_gestion.append({
                'idSucursal':      grupo['idSucursal'],
                'nombre':          grupo['nombre'],
                'bodegasIncluidas': grupo['bodegas'],
                'total':           n,
                'registros':       registros_grupo,
            })
            total_gestion += n
            print(f'  {grupo["clave"]} total: {n} codigos')

    cursor.close()
    conn.close()

    # ── Guardar bodegas_gestion.json ────────────────────────────────────────
    if sucursales_gestion or compartidas_registros:
        compartidas_registros.sort(
            key=lambda r: r.get('diasAntiguedad') if r.get('diasAntiguedad') is not None else -1,
            reverse=True,
        )
        compartidas_meta = GRUPOS[-1]['bodegas']  # BOD_CD
        payload_g = {
            'generado':    hoy,
            'fuente':      'SQL Server directo (descargar_bodegas_sql.py)',
            'total':       total_gestion,
            'compartidas': {
                'bodegasIncluidas': compartidas_meta,
                'total':            len(compartidas_registros),
                'registros':        compartidas_registros,
            },
            'sucursales': sucursales_gestion,
        }
        OUT_GESTION.write_text(json.dumps(payload_g, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'\n[OK] {OUT_GESTION.name}: {total_gestion} codigos totales')

    # ── Guardar bodegas_ir_otras.json ───────────────────────────────────────
    if bodegas_ir:
        payload_ir = {
            'generado':    hoy,
            'fuente':      'SQL Server directo (descargar_bodegas_sql.py)',
            'nombre':      'Isabel Riquelme',
            'total':       total_ir,
            'bodegasIncluidas': [g['bodegas'] for g in GRUPOS if g['clave'] == 'IR'][0],
            'registros':   bodegas_ir,
        }
        OUT_IR.write_text(json.dumps(payload_ir, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'[OK] {OUT_IR.name}: {total_ir} codigos')

    print('\n[FINALIZADO]')


if __name__ == '__main__':
    main()
