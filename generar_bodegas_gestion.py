"""
generar_bodegas_gestion.py
Descarga stock + movimientos de las bodegas de gestion interna (Gestion, Merma,
Recepcion, Ingreso, Transito, Calzada, Distribucion) para las sucursales nuevas del
proyecto BODEGAS GESTION: El Manzano(04), San Vicente(05), Las Cabras(06), Litueche(11).

Isabel Riquelme (02) NO se toca aqui — sigue cubierta por generar_merma_ir.py
(bodega MIR) y generar_bodegas_ir.py (CAL/SER/WEB/GO/GAR/IIR/BMC/RST/HEL). IDs de
este script verificados via P_BODEGAS en vivo — ver IDS_REFERENCIA_BODEGAS_GESTION.md.

SOLO LECTURA de SQL Server. Misma logica/columnas que generar_bodegas_ir.py.

Regla pedida por el usuario: bajar de a 2 bodegas por lote (con pausa entre lotes).

REGLA ANTI-RETROCESO: igual que los otros generadores — si la nueva descarga trae
menos del 50% de los registros del JSON anterior, se aborta y se conserva el reporte
anterior.
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
OUT_JSON  = BASE_DIR / "bodegas_gestion.json"
LOTE_SIZE = 2  # bajar de a 2 bodegas para evitar conflictos/timeouts en SQL

# (idbodega, simbolo, nombre) por sucursal — ver IDS_REFERENCIA_BODEGAS_GESTION.md
# (verificado SQL 2026-07-21). Calzada El Manzano excluida a pedido del usuario.
SUCURSALES = [
    {
        "idSucursal": "04", "nombre": "El Manzano",
        "bodegas": [
            (28, "GEM", "Gestion El Manzano"),
            (29, "MEM", "Mermas El Manzano"),
            (55, "RCE", "Recepcion El Manzano"),
            (72, "IEM", "Ingreso El Manzano"),
            (46, "TEM", "Transito El Manzano"),
            (83, "EEM", "Exhibicion El Manzano"),
        ],
    },
    {
        "idSucursal": "05", "nombre": "San Vicente",
        "bodegas": [
            (41, "GSV", "Gestion San Vicente"),
            (42, "MSV", "Mermas San Vicente"),
            (56, "RSV", "Recepcion San Vicente"),
            (70, "ISV", "Ingreso San Vicente"),
            (45, "TSV", "Transito San Vicente"),
            (44, "CSV", "Calzada San Vicente"),
            (88, "DSV", "Distribucion San Vicente"),
            (95, "ESV", "Exhibicion San Vicente"),
            (43, "CSV", "Consumo San Vicente"),  # OJO: mismo SIMBOLO_BODEGA que Calzada (44) en el ERP
        ],
    },
    {
        "idSucursal": "06", "nombre": "Las Cabras",
        "bodegas": [
            (37, "GLC", "Gestion Las Cabras"),
            (38, "MLC", "Mermas Las Cabras"),
            (57, "RLC", "Recepcion Las Cabras"),
            (71, "ILC", "Ingreso Las Cabras"),
            (16, "TLC", "Transito Las Cabras"),
            (35, "CLC", "Calzada Las Cabras"),
            (91, "GFL", "Garantia Las Cabras"),
            (96, "ELC", "Exhibicion Las Cabras"),
            (97, "VLC", "Volumen Las Cabras"),
        ],
    },
    {
        "idSucursal": "11", "nombre": "Litueche",
        "bodegas": [
            (63, "GLE", "Gestion Litueche"),
            (76, "MLE", "Mermas Litueche"),
            (74, "ILE", "Ingreso Litueche"),
            (59, "TLE", "Transito Litueche"),
            (78, "CLT", "Calzada Litueche"),
            (79, "DLT", "Distribucion Litueche"),
            (64, "ELE", "Exhibicion Litueche"),
        ],
    },
]

# Bodegas compartidas/globales (viven bajo un IDSUCURSAL administrativo distinto —
# 08/01/09 — no repetidas por sucursal, se agrupan en un solo tab "Compartidas").
# Centro de Distribucion (SUC=08) tiene su propio set Gestion/Merma/Recepcion/
# Ingreso/Transito/Crossdock — verificado SQL 2026-07-21. Se excluye Ferrocenter
# (FCM=12, marca/tienda distinta, no es bodega de gestion interna).
COMPARTIDAS = [
    (23, "CD",  "Centro de Distribucion"),
    (7,  "XCD", "CrossDock Centro Distribucion"),
    (27, "GCD", "Gestion CD"),
    (73, "ICD", "Ingreso Centro Distribucion"),
    (26, "MCD", "Mermas CD"),
    (54, "RCD", "Recepcion Centro Distribucion"),
    (67, "TCD", "Transito Centro Distribucion"),
    (98, "BDP", "Despacho Proveedor"),
    (84, "REM", "Remate"),
    (36, "MKT", "Marketing"),
]

DOC_NOMBRES = {
    "GRT": "Guía Recepción Traslado", "GIB": "Guía Ingreso Entre Bodegas",
    "GII": "Guía Ingreso Inventario", "GME": "Guía Elect. Despacho Factura",
    "Gdc": "Guía Devolución Cliente", "GRC": "Guía Recepción Compra",
    "GTS": "Guía Traslados Entre Sucursales", "GST": "Solicitud de Traslado",
    "GEI": "Guía Egreso Inventario / Merma-Gestión", "GDV": "Guía Despacho Venta",
}

# Misma query que generar_bodegas_ir.py, pero IDSUCURSAL es parametro (cada bodega
# se consulta con SU PROPIO IDSUCURSAL real del ERP — ver nota Distribucion en
# IDS_REFERENCIA_BODEGAS_GESTION.md, no siempre coincide con el de la sucursal del tab).
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
    ISNULL(SF.SUBFAMILIA,'')                                AS SUBFAMILIA,
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
WHERE A.IDBODEGA = ?
  AND ISNULL(A.ST_FISICO,0) <> 0
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
    cursor.execute(SQL, idbodega, idbodega)
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

    todas_bodegas = []  # (idbodega, simbolo, nombre, idSucursalTab)
    for suc in SUCURSALES:
        for idbod, simbolo, nombre in suc["bodegas"]:
            todas_bodegas.append((idbod, simbolo, nombre, suc["idSucursal"]))
    for idbod, simbolo, nombre in COMPARTIDAS:
        todas_bodegas.append((idbod, simbolo, nombre, "COMPARTIDAS"))

    log(f"[2/3] Descargando {len(todas_bodegas)} bodegas en lotes de {LOTE_SIZE} "
        f"(evita timeouts/conflictos en la bajada)...")

    # Clave = IDBODEGA (no simbolo): el ERP repite SIMBOLO_BODEGA "CSV" para dos
    # bodegas distintas de San Vicente (Calzada=44 y Consumo=43) — usar el simbolo
    # como clave pisaria una descarga con la otra.
    resultados_por_bodega = {}
    resumen = []
    lotes = [todas_bodegas[i:i + LOTE_SIZE] for i in range(0, len(todas_bodegas), LOTE_SIZE)]
    for n, lote in enumerate(lotes, 1):
        log(f"      Lote {n}/{len(lotes)}: {', '.join(s for _, s, _, _ in lote)}")
        for idbod, simbolo, nombre, idsuc_tab in lote:
            try:
                registros, total_crudo = descargar_bodega(cur, idbod, simbolo, nombre)
                resultados_por_bodega[idbod] = registros
                resumen.append((idsuc_tab, simbolo, nombre, len(registros), total_crudo))
                log(f"        [OK] {simbolo} ({nombre}): {len(registros)} codigos "
                    f"({total_crudo} filas crudas antes de deduplicar)")
            except Exception as e:
                log(f"        [ERROR] {simbolo} ({nombre}): {e} — se omite, resto del lote continua")
                resultados_por_bodega[idbod] = []
                resumen.append((idsuc_tab, simbolo, nombre, 0, 0))
        if n < len(lotes):
            time.sleep(1.5)

    cur.close()
    conn.close()

    # ── Armar estructura final: una entrada por sucursal + una para Compartidas ──
    sucursales_out = []
    total_general = 0
    for suc in SUCURSALES:
        registros = []
        for idbod, simbolo, nombre in suc["bodegas"]:
            registros.extend(resultados_por_bodega.get(idbod, []))
        registros.sort(key=lambda r: r.get("diasAntiguedad") if r.get("diasAntiguedad") is not None else -1, reverse=True)
        sucursales_out.append({
            "idSucursal": suc["idSucursal"], "nombre": suc["nombre"],
            "bodegasIncluidas": [{"id": b[0], "simbolo": b[1], "nombre": b[2]} for b in suc["bodegas"]],
            "total": len(registros), "registros": registros,
        })
        total_general += len(registros)

    compartidas_registros = []
    for idbod, simbolo, nombre in COMPARTIDAS:
        compartidas_registros.extend(resultados_por_bodega.get(idbod, []))
    compartidas_registros.sort(key=lambda r: r.get("diasAntiguedad") if r.get("diasAntiguedad") is not None else -1, reverse=True)
    total_general += len(compartidas_registros)

    data = {
        "generado": datetime.date.today().isoformat(),
        "fuente": "Sistema interno",
        "sucursales": sucursales_out,
        "compartidas": {
            "bodegasIncluidas": [{"id": b[0], "simbolo": b[1], "nombre": b[2]} for b in COMPARTIDAS],
            "total": len(compartidas_registros), "registros": compartidas_registros,
        },
        "total": total_general,
    }

    # ── REGLA ANTI-RETROCESO ────────────────────────────────────────────────
    if OUT_JSON.exists():
        try:
            anterior = json.loads(OUT_JSON.read_text(encoding="utf-8"))
            total_ant = anterior.get("total", 0)
            if total_ant > 0 and total_general < total_ant * 0.5:
                log(f"[ABORTADO] Nueva descarga trae {total_general} registros vs {total_ant} anteriores "
                    f"(caida >50%). Se conserva el reporte anterior por seguridad.")
                sys.exit(1)
        except Exception as e:
            log(f"[AVISO] No se pudo leer JSON anterior para chequeo anti-retroceso: {e}")

    log("[3/3] Generando JSON y verificando consistencia...")
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    log("")
    log("=== RESUMEN / CONSISTENCIA POR BODEGA ===")
    for idsuc_tab, simbolo, nombre, n, crudo in resumen:
        log(f"  [{idsuc_tab}] {simbolo:5s} {nombre:28s} codigos={n:4d}  filas_crudas={crudo:4d}")
    log(f"  TOTAL codigos (todas las sucursales + CD): {total_general}")
    log(f"[OK] {OUT_JSON.name}")


if __name__ == "__main__":
    main()
