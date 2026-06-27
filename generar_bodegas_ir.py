"""
generar_bodegas_ir.py
Descarga stock + movimientos de las bodegas comerciales/auxiliares de Isabel Riquelme
(distintas de MIR/merma, ya cubierta por generar_merma_ir.py):

  5=CAL, 6=SER, 25=WEB, 30=GO, 53=GAR, 69=IIR, 77=BMC, 92=RST, 99=HEL

SOLO LECTURA de SQL Server. Misma logica/columnas que generar_merma_ir.py (ver ese
script y IDS_REFERENCIA_IR.md como referencia, no se duplica documentacion aqui).

Regla pedida por el usuario: bajar de a 2 bodegas por lote (con pausa entre lotes) para
evitar sobrecargar la conexion SQL y reducir riesgo de error/timeout en la bajada.

REGLA ANTI-RETROCESO: igual que generar_merma_ir.py — si la nueva descarga trae menos
del 50% de los registros del JSON anterior, se aborta y se conserva el reporte anterior.
"""
import json
import time
import datetime
import configparser
import sys
from pathlib import Path

import pyodbc

BASE_DIR  = Path(__file__).parent
CRED_FILE = Path(r"E:\ferreteria-oviedo\credenciales_db.ini")
OUT_JSON  = BASE_DIR / "bodegas_ir_otras.json"
IDSUCURSAL = '02'

BODEGAS = [
    (5,  'CAL', 'Calzada'),
    (6,  'SER', 'Servicio Tecnico'),
    (25, 'WEB', 'Retiro Web Santiago'),
    (30, 'GO',  'Gestion Isabel Riquelme'),
    (53, 'GAR', 'Garantia Santiago'),
    (69, 'IIR', 'Ingreso Isabel Riquelme'),
    (77, 'BMC', 'Marticorena Stgo'),
    (92, 'RST', 'Recepcion Santiago'),
    (99, 'HEL', 'Herramientas Electricas'),
]
LOTE_SIZE = 2  # bajar de a 2 bodegas para evitar conflictos/timeouts en SQL

DOC_NOMBRES = {
    "GRT": "Guía Recepción Traslado", "GIB": "Guía Ingreso Entre Bodegas",
    "GII": "Guía Ingreso Inventario", "GME": "Guía Elect. Despacho Factura",
    "Gdc": "Guía Devolución Cliente", "GRC": "Guía Recepción Compra",
    "GTS": "Guía Traslados Entre Sucursales", "GST": "Solicitud de Traslado",
    "GEI": "Guía Egreso Inventario / Merma-Gestión", "GDV": "Guía Despacho Venta",
}

SQL = """
WITH ENTRADAS AS (
    SELECT
        E.IDBODEGA, E.CODIGO_TECNICO, E.IDSUCURSAL, E.IDDOCUMENTO, E.IDNUMERO,
        E.NUMERO, E.FECHA_EMISION, E.CANTIDAD, MD.DOC
    FROM Foviedo.dbo.M_DOCUMENTOS_DETALLE E
    INNER JOIN Foviedo.dbo.M_DOCUMENTOS MD ON MD.IDDOCUMENTO = E.IDDOCUMENTO
    WHERE E.IDBODEGA = ?
      AND MD.DOC IN ('GRC','GRT','GME','GIB','Gdc','GBR','GRP','GRI','GRN','GIN','GDC','GDV','GII','GTS','GEI','GST')
)
SELECT DISTINCT
    D.SIMBOLO_BODEGA                                       AS BODEGA,
    N.DOC                                                  AS TIPO_DOC,
    N.NUMERO                                               AS FOLIO,
    A.CODIGO_TECNICO,
    B.DESCRIPCION,
    CAST(ISNULL(A.ST_FISICO,0)-ISNULL(A.ST_PEDIDO,0) AS DECIMAL(18,2))  AS STOCK_DISPONIBLE,
    CAST(ISNULL(A.ST_FISICO,0)     AS DECIMAL(18,2))       AS STOCK_FISICO,
    CAST(ISNULL(N.CANTIDAD,0)      AS DECIMAL(18,2))       AS CANTIDAD_DOC,
    N.FECHA_EMISION,
    ISNULL(G.OBSERVACION_IMPRESA,'')                       AS OBSERVACION_IMPRESA,
    CAST(ISNULL(B.COSTO_PROMEDIO,0) AS DECIMAL(18,2))      AS COSTO_PROMEDIO,
    ENC.FECHA_REGISTRO                                     AS FECHA_REGISTRO_SISTEMA,
    ENC.IDRESPONZABLE                                      AS USUARIO_RESPONSABLE,
    ENC.AUTORIZADO_FIRMA                                   AS USUARIO_FIRMA,
    ENC.IDVENDEDOR                                         AS USUARIO_VENDEDOR,
    ENC.ESTACION                                           AS ESTACION_PC,
    ISNULL(HF.HIPERFAMILIA,'')                             AS HIPERFAMILIA,
    ISNULL(FA.FAMILIA,'')                                  AS FAMILIA,
    ISNULL(SF.SUBFAMILIA,'')                               AS SUBFAMILIA,
    ISNULL(MA.MARCA,'')                                    AS MARCA
FROM Foviedo.dbo.R_STOCK_PRODUCTOS A
INNER JOIN Foviedo.dbo.M_PRODUCTOS B ON B.CODIGO_TECNICO = A.CODIGO_TECNICO
INNER JOIN Foviedo.dbo.P_BODEGAS D ON A.IDBODEGA = D.IDBODEGA
LEFT JOIN Foviedo.dbo.P_HIPERFAMILIAS HF ON HF.IDHIPERFAMILIA = B.IDHIPERFAMILIA
LEFT JOIN Foviedo.dbo.P_FAMILIAS FA ON FA.IDFAMILIA = B.IDFAMILIA AND FA.IDHIPERFAMILIA = B.IDHIPERFAMILIA
LEFT JOIN Foviedo.dbo.P_SUBFAMILIAS SF ON SF.IDSUBFAMILIA = B.IDSUBFAMILIA AND SF.IDFAMILIA = B.IDFAMILIA AND SF.IDHIPERFAMILIA = B.IDHIPERFAMILIA
LEFT JOIN Foviedo.dbo.P_MARCAS MA ON MA.IDMARCA = B.IDMARCA
LEFT JOIN ENTRADAS N
    ON N.IDBODEGA = A.IDBODEGA AND N.CODIGO_TECNICO = A.CODIGO_TECNICO AND N.IDSUCURSAL = A.IDSUCURSAL
LEFT JOIN Foviedo.dbo.M_Documentos_Encabezado_Observacion G
    ON G.IDDOCUMENTO = N.IDDOCUMENTO AND G.IDNUMERO = N.IDNUMERO AND G.IDSUCURSAL = A.IDSUCURSAL
LEFT JOIN Foviedo.dbo.M_DOCUMENTOS_ENCABEZADO ENC
    ON ENC.IDDOCUMENTO = N.IDDOCUMENTO AND ENC.IDNUMERO = N.IDNUMERO AND ENC.IDSUCURSAL = A.IDSUCURSAL
WHERE A.IDBODEGA = ? AND A.IDSUCURSAL = ?
  AND ISNULL(A.ST_FISICO,0) >= 1
ORDER BY N.FECHA_EMISION DESC
"""


def log(msg):
    print(msg, flush=True)


def leer_credenciales():
    cfg = configparser.ConfigParser()
    cfg.read(str(CRED_FILE), encoding="utf-8")
    db = cfg["DB"]
    return db["server"], db["database"], db["user"], db["password"]


def conectar():
    server, database, user, password = leer_credenciales()
    return pyodbc.connect(
        f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};"
        f"UID={user};PWD={password};TrustServerCertificate=yes;", timeout=30
    )


def fecha_str(v):
    if v is None:
        return ""
    return v.strftime("%d/%m/%Y") if hasattr(v, "strftime") else str(v)


def fecha_iso(v):
    if v is None or not hasattr(v, "date"):
        return ""
    return v.date().isoformat()


def fecha_hora_str(v):
    if v is None:
        return ""
    return v.strftime("%d/%m/%Y %H:%M:%S") if hasattr(v, "strftime") else str(v)


def descargar_bodega(cursor, idbodega, simbolo, nombre):
    cursor.execute(SQL, idbodega, idbodega, IDSUCURSAL)
    hoy = datetime.date.today()
    crudos = []
    for row in cursor.fetchall():
        bodega, tipo_doc, folio, cod_tec, descripcion = (str(row[i] or "").strip() for i in range(5))
        disp, fisico, cantidad = float(row[5] or 0), float(row[6] or 0), float(row[7] or 0)
        fecha_reg = row[8]
        obs = str(row[9] or "").strip().replace("_x000D_", "").strip()
        costo = round(float(row[10] or 0))
        fecha_sis = row[11]
        usuario = str(row[12] or row[13] or row[14] or "").strip()
        estacion = str(row[15] or "").strip()
        hiper, fam, sub, marca = (str(row[i] or "").strip() for i in range(16, 20))
        dias = (hoy - fecha_reg.date()).days if fecha_reg and hasattr(fecha_reg, "date") else None
        crudos.append({
            "bodega": simbolo, "bodegaNombre": nombre, "tipoDoc": tipo_doc,
            "tipoDocNombre": DOC_NOMBRES.get(tipo_doc, tipo_doc) if tipo_doc else "",
            "folio": folio, "codigoTecnico": cod_tec, "descripcion": descripcion,
            "disp": disp, "fisico": fisico, "cantidad": cantidad, "costo": costo,
            "fechaRegistro": fecha_str(fecha_reg), "fechaRegistroIso": fecha_iso(fecha_reg),
            "diasAntiguedad": dias, "observacion": obs,
            "usuario": usuario, "estacionPc": estacion,
            "fechaRegistroSistema": fecha_hora_str(fecha_sis),
            "hiperfamilia": hiper, "familia": fam, "subfamilia": sub, "marca": marca,
        })

    # quedarse con el movimiento mas reciente por (bodega, codigo) — igual criterio que merma
    mas_reciente = {}
    for r in crudos:
        k = (r["bodega"], r["codigoTecnico"])
        d = r["diasAntiguedad"] if r["diasAntiguedad"] is not None else 999999
        prev = mas_reciente.get(k)
        if prev is None or d < (prev["diasAntiguedad"] if prev["diasAntiguedad"] is not None else 999999):
            mas_reciente[k] = r
    return list(mas_reciente.values()), len(crudos)


def main():
    if not CRED_FILE.exists():
        log(f"[ERROR] No existe {CRED_FILE}")
        sys.exit(1)

    log("[1/3] Conectando a SQL Server (solo lectura)...")
    conn = conectar()
    cur = conn.cursor()
    log("      Conexion OK")

    log(f"[2/3] Descargando {len(BODEGAS)} bodegas en lotes de {LOTE_SIZE} "
        f"(evita timeouts/conflictos en la bajada)...")

    todos = []
    resumen = []
    lotes = [BODEGAS[i:i + LOTE_SIZE] for i in range(0, len(BODEGAS), LOTE_SIZE)]
    for n, lote in enumerate(lotes, 1):
        log(f"      Lote {n}/{len(lotes)}: {', '.join(s for _, s, _ in lote)}")
        for idbodega, simbolo, nombre in lote:
            try:
                registros, total_crudo = descargar_bodega(cur, idbodega, simbolo, nombre)
                todos.extend(registros)
                resumen.append((simbolo, nombre, len(registros), total_crudo))
                log(f"        [OK] {simbolo} ({nombre}): {len(registros)} codigos "
                    f"({total_crudo} filas crudas antes de deduplicar)")
            except Exception as e:
                log(f"        [ERROR] {simbolo} ({nombre}): {e} — se omite, resto del lote continua")
                resumen.append((simbolo, nombre, 0, 0))
        if n < len(lotes):
            time.sleep(1.5)  # pausa entre lotes para no saturar la conexion SQL

    cur.close()
    conn.close()

    todos.sort(key=lambda r: r.get("diasAntiguedad") if r.get("diasAntiguedad") is not None else -1, reverse=True)

    # ── REGLA ANTI-RETROCESO ────────────────────────────────────────────────
    if OUT_JSON.exists():
        try:
            anterior = json.loads(OUT_JSON.read_text(encoding="utf-8"))
            total_ant = anterior.get("total", 0)
            if total_ant > 0 and len(todos) < total_ant * 0.5:
                log(f"[ABORTADO] Nueva descarga trae {len(todos)} registros vs {total_ant} anteriores "
                    f"(caida >50%). Se conserva el reporte anterior por seguridad.")
                sys.exit(1)
        except Exception as e:
            log(f"[AVISO] No se pudo leer JSON anterior para chequeo anti-retroceso: {e}")

    log("[3/3] Generando JSON y verificando consistencia...")
    data = {
        "generado": datetime.date.today().isoformat(),
        "fuente": "Sistema interno",
        "idSucursal": IDSUCURSAL,
        "bodegasIncluidas": [{"id": b[0], "simbolo": b[1], "nombre": b[2]} for b in BODEGAS],
        "total": len(todos), "registros": todos,
    }
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    log("")
    log("=== RESUMEN / CONSISTENCIA POR BODEGA ===")
    for simbolo, nombre, n, crudo in resumen:
        log(f"  {simbolo:5s} {nombre:28s} codigos={n:4d}  filas_crudas={crudo:4d}")
    log(f"  TOTAL codigos (todas las bodegas): {len(todos)}")
    log(f"[OK] {OUT_JSON.name}")


if __name__ == "__main__":
    main()
