"""
generar_merma_ir.py
Genera reporte HTML standalone de MERMA — Sucursal Isabel Riquelme (IDSUCURSAL='02',
bodega MIR/IDBODEGA=75), replicando la logica de "Analisis de Bodegas" del panel admin
de El Manzano (ver E:\\ferreteria-oviedo\\BODEGAS\\descargar_bod.py, solo lectura/referencia).

SOLO LECTURA de SQL Server. NO escribe nada fuera de esta carpeta (E:\\ISABEL RIQUELME).
Credenciales: se leen desde E:\\ferreteria-oviedo\\credenciales_db.ini (solo lectura,
no se copia el valor a ningun archivo de salida).

REGLA ANTI-RETROCESO: si la nueva descarga trae menos del 50% de los registros del
JSON anterior, se ABORTA el sobrescrito y se conserva el reporte anterior intacto
(evita que una falla SQL/Excel vacio borre el reporte bueno ya generado).
"""
import json
import datetime
import configparser
import sys
from pathlib import Path

import openpyxl
import pyodbc

BASE_DIR     = Path(__file__).parent
CRED_FILE    = Path(r"E:\ferreteria-oviedo\credenciales_db.ini")
MERMA_XLSX   = BASE_DIR / "MERMA.xlsx"
OUT_JSON     = BASE_DIR / "merma_isabel_riquelme.json"
OUT_HTML     = BASE_DIR / "MERMA_ISABEL_RIQUELME.html"
LOGO_B64     = BASE_DIR / "_logo_oviedo_b64.txt"
BODEGAS_JSON = BASE_DIR / "bodegas_ir_otras.json"  # generado por generar_bodegas_ir.py (menu "Otras Bodegas")

IDBODEGA   = 75     # MIR — Mermas Isabel Riquelme
IDSUCURSAL = '02'   # Isabel Riquelme

# Nombres completos de tipo de documento (Foviedo.dbo.M_DOCUMENTOS, verificado SQL 2026-06-27)
DOC_NOMBRES = {
    "GRT": "Guía Recepción Traslado",
    "GIB": "Guía Ingreso Entre Bodegas",
    "GII": "Guía Ingreso Inventario",
    "GME": "Guía Elect. Despacho Factura",
    "Gdc": "Guía Devolución Cliente",
    "GRC": "Guía Recepción Compra",
    "GTS": "Guía Traslados Entre Sucursales",
    "GST": "Solicitud de Traslado",
    "GEI": "Guía Egreso Inventario / Merma-Gestión",
    "GDV": "Guía Despacho Venta",
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
    ENC.ESTACION                                           AS ESTACION_PC
FROM Foviedo.dbo.R_STOCK_PRODUCTOS A
INNER JOIN Foviedo.dbo.M_PRODUCTOS B ON B.CODIGO_TECNICO = A.CODIGO_TECNICO
INNER JOIN Foviedo.dbo.P_BODEGAS D ON A.IDBODEGA = D.IDBODEGA
INNER JOIN ENTRADAS N
    ON N.IDBODEGA = A.IDBODEGA AND N.CODIGO_TECNICO = A.CODIGO_TECNICO AND N.IDSUCURSAL = A.IDSUCURSAL
LEFT JOIN Foviedo.dbo.M_Documentos_Encabezado_Observacion G
    ON G.IDDOCUMENTO = N.IDDOCUMENTO AND G.IDNUMERO = N.IDNUMERO AND G.IDSUCURSAL = A.IDSUCURSAL
LEFT JOIN Foviedo.dbo.M_DOCUMENTOS_ENCABEZADO ENC
    ON ENC.IDDOCUMENTO = N.IDDOCUMENTO AND ENC.IDNUMERO = N.IDNUMERO AND ENC.IDSUCURSAL = A.IDSUCURSAL
WHERE A.IDBODEGA = ? AND A.IDSUCURSAL = ?
  AND A.CODIGO_TECNICO IN ({codigos})
ORDER BY N.FECHA_EMISION DESC
"""


def log(msg):
    print(msg, flush=True)


def leer_codigos_merma():
    wb = openpyxl.load_workbook(MERMA_XLSX)
    ws = wb["Sheet 1"]
    rows = list(ws.iter_rows(values_only=True))
    codigos, meta = [], {}
    for r in rows[1:]:
        cod = r[4]
        if not cod:
            continue
        cod = str(cod).strip()
        codigos.append(cod)
        meta[cod] = {
            "stockDisponibleXls": r[10],
            "stockUnidadesXls":   r[11],
            "stockValorizadoXls": r[12],
            "hiperfamilia": (r[6] or "").strip() if r[6] else "",
            "familia":      (r[7] or "").strip() if r[7] else "",
            "subfamilia":   (r[8] or "").strip() if r[8] else "",
            "marca":        (r[9] or "").strip() if r[9] else "",
        }
    return sorted(set(codigos)), meta


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


def main():
    if not CRED_FILE.exists():
        log(f"[ERROR] No existe {CRED_FILE}")
        sys.exit(1)

    log("[1/5] Leyendo codigos desde MERMA.xlsx...")
    codigos, meta_xls = leer_codigos_merma()
    log(f"      {len(codigos)} codigos unicos encontrados")

    log("[2/5] Conectando a SQL Server (solo lectura)...")
    conn = conectar()
    cur = conn.cursor()
    log("      Conexion OK")

    log("[3/5] Consultando movimientos bodega MIR (IDBODEGA=75, SUC=02)...")
    placeholders = ",".join("?" for _ in codigos)
    sql = SQL.format(codigos=placeholders)
    cur.execute(sql, IDBODEGA, IDBODEGA, IDSUCURSAL, *codigos)

    hoy = datetime.date.today()
    registros = []
    for row in cur.fetchall():
        bodega, tipo_doc, folio, cod_tec, descripcion = (str(row[i] or "").strip() for i in range(5))
        disp     = float(row[5] or 0)
        fisico   = float(row[6] or 0)
        cantidad = float(row[7] or 0)
        fecha_reg = row[8]
        obs       = str(row[9] or "").strip().replace("_x000D_", "").strip()
        costo     = round(float(row[10] or 0))
        fecha_sis = row[11]
        usuario   = str(row[12] or row[13] or row[14] or "").strip()
        estacion  = str(row[15] or "").strip()

        dias = (hoy - fecha_reg.date()).days if fecha_reg and hasattr(fecha_reg, "date") else None

        registros.append({
            "bodega": bodega, "tipoDoc": tipo_doc,
            "tipoDocNombre": DOC_NOMBRES.get(tipo_doc, tipo_doc),
            "folio": folio, "codigoTecnico": cod_tec, "descripcion": descripcion,
            "disp": disp, "fisico": fisico, "cantidad": cantidad, "costo": costo,
            "fechaRegistro": fecha_str(fecha_reg), "fechaRegistroIso": fecha_iso(fecha_reg),
            "diasAntiguedad": dias, "observacion": obs,
            "usuario": usuario, "estacionPc": estacion,
            "fechaRegistroSistema": fecha_hora_str(fecha_sis),
        })
    cur.close()
    conn.close()
    log(f"      {len(registros)} movimientos encontrados")

    mas_reciente = {}
    for r in registros:
        cod = r["codigoTecnico"]
        d = r["diasAntiguedad"] if r["diasAntiguedad"] is not None else 999999
        prev = mas_reciente.get(cod)
        if prev is None or d < (prev["diasAntiguedad"] if prev["diasAntiguedad"] is not None else 999999):
            mas_reciente[cod] = r

    final = []
    for cod in codigos:
        m = meta_xls.get(cod, {})
        r = mas_reciente.get(cod)
        if r:
            r = dict(r)
            r.update({k: v for k, v in m.items()})
            final.append(r)
        else:
            final.append({
                "bodega": "MIR", "tipoDoc": "", "tipoDocNombre": "", "folio": "",
                "codigoTecnico": cod, "descripcion": "",
                "disp": m.get("stockDisponibleXls") or 0, "fisico": m.get("stockUnidadesXls") or 0,
                "cantidad": 0, "costo": 0, "fechaRegistro": "", "fechaRegistroIso": "",
                "diasAntiguedad": None, "observacion": "(sin movimiento SQL encontrado)",
                "usuario": "", "estacionPc": "", "fechaRegistroSistema": "", **m,
            })

    final.sort(key=lambda r: r.get("diasAntiguedad") if r.get("diasAntiguedad") is not None else -1, reverse=True)

    # ── REGLA ANTI-RETROCESO ────────────────────────────────────────────────
    if OUT_JSON.exists():
        try:
            anterior = json.loads(OUT_JSON.read_text(encoding="utf-8"))
            total_ant = anterior.get("total", 0)
            if total_ant > 0 and len(final) < total_ant * 0.5:
                log(f"[ABORTADO] Nueva descarga trae {len(final)} registros vs {total_ant} anteriores "
                    f"(caida >50%). Se conserva el reporte anterior por seguridad.")
                sys.exit(1)
        except Exception as e:
            log(f"[AVISO] No se pudo leer JSON anterior para chequeo anti-retroceso: {e}")

    log("[4/5] Generando JSON...")
    data = {
        "generado": hoy.isoformat(),
        "fuente": "Sistema interno + MERMA.xlsx",
        "bodega": "MIR", "idBodega": IDBODEGA, "idSucursal": IDSUCURSAL,
        "total": len(final), "registros": final,
    }
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    log("[5/5] Generando HTML...")
    generar_html(data)
    log(f"[OK] {OUT_JSON.name}")
    log(f"[OK] {OUT_HTML.name}")


def generar_html(data):
    # IMPORTANTE: el HTML publicado en GitHub Pages ya NO embebe los datos crudos.
    # Los datos viven en Firestore (proyecto isabel-riquelme-merma) y se cargan en el
    # navegador SOLO despues de iniciar sesion (ver firestore.rules: auth != null).
    # generar_bodegas_ir.py / generar_merma_ir.py siguen escribiendo los JSON locales
    # (merma_isabel_riquelme.json, bodegas_ir_otras.json) que luego sube
    # _subir_datos_firestore.py — ese paso es manual/script aparte, no parte del HTML.
    logo_b64 = LOGO_B64.read_text(encoding="utf-8").strip() if LOGO_B64.exists() else ""
    html = HTML_TEMPLATE.replace("__LOGO_B64__", logo_b64)
    OUT_HTML.write_text(html, encoding="utf-8")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Merma — Sucursal Isabel Riquelme — Ferretería Oviedo</title>
<script src="https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.22.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.22.0/firebase-auth-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.22.0/firebase-firestore-compat.js"></script>
<style>
  #loginScreen{position:fixed;inset:0;background:linear-gradient(135deg,#111827,#DA0000);
               display:flex;align-items:center;justify-content:center;z-index:9999}
  .login-box{background:#fff;border-radius:16px;padding:32px 30px;width:320px;box-shadow:0 20px 60px rgba(0,0,0,.3);text-align:center}
  .login-box img{height:50px;margin-bottom:14px}
  .login-box h2{font-size:16px;margin:0 0 18px;color:#111827}
  .login-box input{width:100%;padding:10px 12px;border:1.5px solid #e5e7eb;border-radius:8px;font-size:14px;
                    margin-bottom:10px;font-family:inherit;box-sizing:border-box}
  .login-box button{width:100%;padding:11px;background:#DA0000;color:#fff;border:none;border-radius:8px;
                     font-size:14px;font-weight:700;cursor:pointer;font-family:inherit}
  .login-box button:hover{background:#c93a08}
  .login-err{color:#dc2626;font-size:12px;margin-top:8px;min-height:16px}
  #appRoot{display:none}
  .btn-logout{background:#374151;color:#fff;border:none;border-radius:6px;padding:6px 12px;font-size:12px;
              font-weight:700;cursor:pointer;font-family:inherit;margin-left:auto}
  :root{--naranja:#DA0000;--naranja2:#c93a08;--dark:#111827;--border:#e5e7eb;--gris:#6b7280;
        --verde:#059669;--rojo:#dc2626;--amarillo:#d97706}
  *{box-sizing:border-box}
  body{font-family:'Segoe UI',Arial,sans-serif;background:#f0f2f5;margin:0;padding:0;color:#1a1a1a}
  .topbar{background:var(--dark);color:#fff;padding:14px 22px;display:flex;align-items:center;gap:14px;
          box-shadow:0 2px 8px rgba(0,0,0,.35)}
  .topbar img{height:42px;width:auto;flex-shrink:0;border-radius:4px;background:#fff;padding:3px}
  .topbar h1{font-size:16px;margin:0;font-weight:700}
  .topbar .sub{font-size:11px;color:#cbd5e1;margin-top:2px}
  .wrap{padding:18px 22px}
  .card{background:#fff;border-radius:10px;padding:16px 18px;box-shadow:0 1px 3px rgba(0,0,0,.1);margin-bottom:14px}
  .sub{font-size:12px;color:var(--gris);margin-bottom:12px}
  .bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
  .bar input,.bar select{font-size:12px;padding:6px 9px;border:1px solid var(--border);border-radius:6px;font-family:inherit}
  .bar label{font-size:11px;font-weight:600;color:#374151;display:flex;align-items:center;gap:4px}
  .btn{font-size:12px;font-weight:700;padding:7px 14px;border-radius:6px;border:none;cursor:pointer;
       color:#fff;font-family:inherit;display:inline-flex;align-items:center;gap:6px}
  .btn-excel{background:var(--verde)}.btn-excel:hover{background:#047857}
  .btn-html{background:#2563eb}.btn-html:hover{background:#1d4ed8}
  .btn-mail{background:var(--naranja)}.btn-mail:hover{background:var(--naranja2)}
  .kpis{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
  .kpi{background:#fef3c7;color:#92400e;border-radius:8px;padding:8px 14px;border:1px solid rgba(0,0,0,.08);min-width:110px}
  .kpi.red{background:#fee2e2;color:#991b1b}
  .kpi .n{font-size:19px;font-weight:800}
  .kpi .l{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}
  table{border-collapse:collapse;font-size:12px;table-layout:fixed;width:1620px}
  .tablewrap::-webkit-scrollbar{height:16px;width:16px}
  .tablewrap::-webkit-scrollbar-track{background:#e5e7eb}
  .tablewrap::-webkit-scrollbar-thumb{background:var(--naranja);border-radius:8px;border:3px solid #e5e7eb}
  .scroll-hint{font-size:11px;color:#92400e;background:#fef3c7;border:1px solid #fde68a;border-radius:6px;
               padding:5px 10px;margin-bottom:8px;display:inline-block}
  th,td{border:1px solid #c7ccd4}
  th{background:var(--dark);color:#fff;padding:8px 9px;text-align:left;position:sticky;top:0;white-space:nowrap;z-index:1}
  td{padding:6px 9px;vertical-align:top;overflow-wrap:break-word}
  tr:nth-child(even){background:#f9fafb}
  .right{text-align:right}.center{text-align:center}
  .obs{color:#6b7280;font-size:11px;white-space:normal;word-break:break-word}
  .desc{white-space:normal;word-break:break-word}
  .mono{font-family:Consolas,monospace;white-space:nowrap}
  #count{font-size:12px;color:#6b7280;margin-left:auto}
  .d90{color:var(--rojo);font-weight:700}.d30{color:var(--amarillo);font-weight:600}
  .neg{color:#fff;background:var(--rojo);font-weight:700;border-radius:4px;padding:2px 6px;display:inline-block}
  .tablewrap{overflow:auto;max-height:72vh;border:1px solid var(--border);border-radius:8px}
  .badge-na{color:#9ca3af;font-style:italic}
  .footer-note{font-size:11px;color:#9ca3af;text-align:center;padding:10px}
  .tabs{display:flex;gap:6px;padding:0 22px;background:var(--dark)}
  .tab-btn{font-size:13px;font-weight:700;color:#cbd5e1;background:#1f2937;border:none;border-bottom:3px solid transparent;
           padding:10px 18px;cursor:pointer;font-family:inherit}
  .tab-btn.active{color:#fff;background:#2a3142;border-bottom-color:var(--naranja)}
  .tab-panel{display:none}
  .tab-panel.active{display:block}
  .chk-row{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:10px;background:#f9fafb;border:1px solid var(--border);
           border-radius:8px;padding:9px 12px}
  .chk-row label{font-size:12px;font-weight:600;color:#374151;display:flex;align-items:center;gap:5px;cursor:pointer}
</style>
</head>
<body>

<div id="loginScreen">
  <div class="login-box">
    <img src="data:image/jpeg;base64,__LOGO_B64__" alt="Ferretería Oviedo">
    <h2>Análisis Isabel Riquelme — Acceso restringido</h2>
    <input type="text" id="loginUser" placeholder="Usuario" autocomplete="username">
    <input type="password" id="loginPass" placeholder="Contraseña" autocomplete="current-password">
    <button onclick="doLogin()">Ingresar</button>
    <div class="login-err" id="loginErr"></div>
  </div>
</div>

<div id="appRoot">
<div class="topbar">
  <img src="data:image/jpeg;base64,__LOGO_B64__" alt="Ferretería Oviedo">
  <div>
    <h1>Análisis Sucursal Isabel Riquelme — Ferretería Oviedo</h1>
    <div class="sub">Datos protegidos — requieren inicio de sesión (Firebase Auth + Firestore rules)</div>
  </div>
  <button class="btn-logout" onclick="doLogout()">Cerrar sesión</button>
</div>
<div class="tabs">
  <button class="tab-btn active" id="tabBtn_merma" onclick="cambiarTab('merma')">📦 Merma (Bodega MIR)</button>
  <button class="tab-btn" id="tabBtn_bodegas" onclick="cambiarTab('bodegas')">🏬 Otras Bodegas</button>
</div>
<div class="wrap">

<div class="card tab-panel active" id="panel_merma">
  <div class="sub" id="meta_merma"></div>
  <div class="bar">
    <input type="text" id="merma_qBuscar" placeholder="Código o descripción" oninput="render('merma')" style="width:200px">
    <select id="merma_qTipoDoc" onchange="render('merma')"><option value="">Todos los tipos de documento</option></select>
    <select id="merma_qUsuario" onchange="render('merma')"><option value="">Todos los usuarios</option></select>
    <select id="merma_qFamilia" onchange="render('merma')"><option value="">Todas las familias</option></select>
    <select id="merma_qMarca" onchange="render('merma')"><option value="">Todas las marcas</option></select>
    <label>Días ≥ <input type="number" id="merma_qDiasMin" style="width:55px" oninput="render('merma')"></label>
    <label>Días ≤ <input type="number" id="merma_qDiasMax" style="width:55px" oninput="render('merma')"></label>
    <label>Desde <input type="date" id="merma_qFechaDesde" oninput="render('merma')"></label>
    <label>Hasta <input type="date" id="merma_qFechaHasta" oninput="render('merma')"></label>
  </div>
  <div class="bar">
    <button class="btn btn-excel" onclick="exportarExcel('merma')">📊 Descargar Excel</button>
    <button class="btn btn-html" onclick="exportarHtml('merma')">🌐 Descargar HTML</button>
    <button class="btn btn-mail" onclick="enviarCorreo('merma')">✉️ Enviar por correo</button>
    <span id="merma_count"></span>
  </div>
  <div class="kpis" id="merma_kpis"></div>
  <div class="scroll-hint">👉 Desliza la tabla horizontalmente (barra naranja abajo) para ver Estación/PC, Fecha registro sistema y Observación</div>
  <div class="tablewrap">
  <table>
    <colgroup>
      <col style="width:80px"><col style="width:220px"><col style="width:90px"><col style="width:95px">
      <col style="width:130px"><col style="width:70px">
      <col style="width:55px"><col style="width:55px"><col style="width:80px">
      <col style="width:80px"><col style="width:50px"><col style="width:90px">
      <col style="width:90px"><col style="width:100px"><col style="width:120px"><col style="width:220px">
    </colgroup>
    <thead><tr>
      <th>Código</th><th>Descripción</th><th>Marca</th><th>Familia</th>
      <th>Tipo Doc.</th><th class="right">Folio</th>
      <th class="right">Disp.</th><th class="right">Físico</th><th class="right">Costo unit.</th>
      <th class="center">Fecha Reg.</th><th class="right">Días</th><th class="right">Valorizado</th>
      <th>Usuario</th><th>Estación / PC</th><th class="center">Fecha registro sistema</th><th>Observación</th>
    </tr></thead>
    <tbody id="merma_tbody"></tbody>
  </table>
  </div>
  <div class="footer-note">Ferretería Oviedo El Manzano · Reporte generado desde sistema interno — no contiene credenciales</div>
</div>

<div class="card tab-panel" id="panel_bodegas">
  <div class="sub" id="meta_bodegas"></div>
  <div class="chk-row" id="bodegas_chkBodegas"></div>
  <div class="bar">
    <input type="text" id="bodegas_qBuscar" placeholder="Código o descripción" oninput="render('bodegas')" style="width:200px">
    <select id="bodegas_qTipoDoc" onchange="render('bodegas')"><option value="">Todos los tipos de documento</option></select>
    <select id="bodegas_qUsuario" onchange="render('bodegas')"><option value="">Todos los usuarios</option></select>
    <select id="bodegas_qFamilia" onchange="render('bodegas')"><option value="">Todas las familias</option></select>
    <select id="bodegas_qMarca" onchange="render('bodegas')"><option value="">Todas las marcas</option></select>
    <label>Días ≥ <input type="number" id="bodegas_qDiasMin" style="width:55px" oninput="render('bodegas')"></label>
    <label>Días ≤ <input type="number" id="bodegas_qDiasMax" style="width:55px" oninput="render('bodegas')"></label>
    <label>Desde <input type="date" id="bodegas_qFechaDesde" oninput="render('bodegas')"></label>
    <label>Hasta <input type="date" id="bodegas_qFechaHasta" oninput="render('bodegas')"></label>
  </div>
  <div class="bar">
    <button class="btn btn-excel" onclick="exportarExcel('bodegas')">📊 Descargar Excel</button>
    <button class="btn btn-html" onclick="exportarHtml('bodegas')">🌐 Descargar HTML</button>
    <button class="btn btn-mail" onclick="enviarCorreo('bodegas')">✉️ Enviar por correo</button>
    <span id="bodegas_count"></span>
  </div>
  <div class="kpis" id="bodegas_kpis"></div>
  <div class="scroll-hint">👉 Desliza la tabla horizontalmente (barra naranja abajo) para ver Estación/PC, Fecha registro sistema y Observación</div>
  <div class="tablewrap">
  <table>
    <colgroup>
      <col style="width:60px"><col style="width:80px"><col style="width:220px"><col style="width:90px"><col style="width:95px">
      <col style="width:130px"><col style="width:70px">
      <col style="width:55px"><col style="width:55px"><col style="width:80px">
      <col style="width:80px"><col style="width:50px"><col style="width:90px">
      <col style="width:90px"><col style="width:100px"><col style="width:120px"><col style="width:220px">
    </colgroup>
    <thead><tr>
      <th>Bodega</th><th>Código</th><th>Descripción</th><th>Marca</th><th>Familia</th>
      <th>Tipo Doc.</th><th class="right">Folio</th>
      <th class="right">Disp.</th><th class="right">Físico</th><th class="right">Costo unit.</th>
      <th class="center">Fecha Reg.</th><th class="right">Días</th><th class="right">Valorizado</th>
      <th>Usuario</th><th>Estación / PC</th><th class="center">Fecha registro sistema</th><th>Observación</th>
    </tr></thead>
    <tbody id="bodegas_tbody"></tbody>
  </table>
  </div>
  <div class="footer-note">Ferretería Oviedo El Manzano · Reporte generado desde sistema interno — no contiene credenciales</div>
</div>

</div>
</div><!-- /appRoot -->
<script>
// ── Config Firebase (proyecto isabel-riquelme-merma — independiente de ferreteria-oviedo) ──
// La apiKey es publica por diseño (ver https://firebase.google.com/docs/projects/api-keys);
// la proteccion real de los datos la dan las Firestore rules (auth != null), no esta key.
var firebaseConfig = {
  apiKey: "AIzaSyCCZQahfSz8JtuN-YKHVLzd90ky7wITV2E",
  authDomain: "isabel-riquelme-merma.firebaseapp.com",
  projectId: "isabel-riquelme-merma",
  storageBucket: "isabel-riquelme-merma.firebasestorage.app",
  messagingSenderId: "778981011672",
  appId: "1:778981011672:web:dba69b04169a0ba6cfa7ad"
};
firebase.initializeApp(firebaseConfig);
var auth = firebase.auth();
var db = firebase.firestore();
var LOGIN_DOMAIN = "isabel-riquelme-merma.local"; // usuario "riquelme" -> riquelme@<dominio interno>

function doLogin(){
  var user = (document.getElementById('loginUser').value || '').trim().toLowerCase();
  var pass = document.getElementById('loginPass').value || '';
  var err = document.getElementById('loginErr');
  err.textContent = '';
  if(!user || !pass){ err.textContent = 'Ingresa usuario y contraseña'; return; }
  auth.signInWithEmailAndPassword(user + '@' + LOGIN_DOMAIN, pass)
    .then(function(){ /* onAuthStateChanged hace el resto */ })
    .catch(function(e){
      err.textContent = (e.code === 'auth/wrong-password' || e.code === 'auth/user-not-found' ||
        e.code === 'auth/invalid-credential') ? 'Usuario o contraseña incorrectos' : ('Error: ' + e.code);
    });
}

function doLogout(){
  auth.signOut();
}

auth.onAuthStateChanged(function(user){
  if(user){
    document.getElementById('loginScreen').style.display = 'none';
    document.getElementById('appRoot').style.display = 'block';
    cargarDatosFirestore();
  } else {
    document.getElementById('appRoot').style.display = 'none';
    document.getElementById('loginScreen').style.display = 'flex';
  }
});

function snapshotToRegistros(snap){
  var out = [];
  snap.forEach(function(doc){ out.push(doc.data()); });
  return out;
}

function cargarDatosFirestore(){
  Promise.all([
    db.collection('merma_meta').doc('info').get(),
    db.collection('merma').get(),
    db.collection('bodegas_meta').doc('info').get(),
    db.collection('bodegas').get(),
  ]).then(function(res){
    var metaMerma = res[0].exists ? res[0].data() : {};
    var regMerma = snapshotToRegistros(res[1]);
    var metaBod = res[2].exists ? res[2].data() : {};
    var regBod = snapshotToRegistros(res[3]);

    VISTAS.merma.DATA = Object.assign({registros: regMerma}, metaMerma);
    VISTAS.bodegas.DATA = Object.assign({registros: regBod}, metaBod);
    if(metaBod.bodegasIncluidas) VISTAS.bodegas.DATA.bodegasIncluidas = JSON.parse(metaBod.bodegasIncluidas);

    initVista('merma');
    initVista('bodegas');
    render('merma');
    render('bodegas');
  }).catch(function(e){
    document.getElementById('appRoot').innerHTML =
      '<div style="padding:40px;text-align:center;color:#dc2626">Error cargando datos desde Firestore: '+e.message+'</div>';
  });
}

// ── Datasets (uno por pestaña) — se llenan via Firestore tras login ─────────
var VISTAS = {
  merma:   { DATA: {registros:[]}, conBodega:false, label:'Merma IR' },
  bodegas: { DATA: {registros:[]}, conBodega:true,  label:'Otras Bodegas IR' }
};

function esc(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function fmt(n){ return Math.round(Number(n||0)).toLocaleString('es-CL'); }
function clp(n){ return (Number(n||0)>0)?'$'+fmt(n):'—'; }
// Resalta en rojo cualquier cantidad/valorizado negativo (stock comprometido sin recepcion).
function numCell(n){ return (Number(n||0)<0) ? '<span class="neg">'+fmt(n)+'</span>' : fmt(n); }
function clpCell(n){
  var v=Number(n||0);
  if(v<0) return '<span class="neg">-$'+fmt(Math.abs(v))+'</span>';
  return clp(v);
}
function id(v,base){ return v+'_'+base; }
function $(v,base){ return document.getElementById(id(v,base)); }

function fillSelect(v, base, valores){
  var sel=$(v,base);
  valores.sort().forEach(function(x){
    var o=document.createElement('option'); o.value=x; o.textContent=x;
    sel.appendChild(o);
  });
}

function cambiarTab(v){
  Object.keys(VISTAS).forEach(function(k){
    document.getElementById('panel_'+k).classList.toggle('active', k===v);
    document.getElementById('tabBtn_'+k).classList.toggle('active', k===v);
  });
}

// Se llama una vez por vista, despues de que cargarDatosFirestore() llena VISTAS[v].DATA.
function initVista(v){
  var cfg = VISTAS[v];
  var REG = cfg.DATA.registros || [];
  cfg.REG = REG; cfg.FIL = [];

  document.getElementById('meta_'+v).textContent =
    'Generado: '+(cfg.DATA.generado||'—')+' · Fuente: '+(cfg.DATA.fuente||'—')+' · Total códigos: '+(cfg.DATA.total!=null?cfg.DATA.total:REG.length);

  // limpiar selects por si initVista se llama mas de una vez (recarga de sesion)
  ['qTipoDoc','qUsuario','qFamilia','qMarca'].forEach(function(base){
    var sel=$(v,base); while(sel.options.length>1) sel.remove(1);
  });
  fillSelect(v,'qTipoDoc', Array.from(new Set(REG.filter(r=>r.tipoDocNombre).map(r=>r.tipoDocNombre))));
  fillSelect(v,'qUsuario', Array.from(new Set(REG.filter(r=>r.usuario).map(r=>r.usuario))));
  fillSelect(v,'qFamilia', Array.from(new Set(REG.filter(r=>r.familia).map(r=>r.familia))));
  fillSelect(v,'qMarca',   Array.from(new Set(REG.filter(r=>r.marca).map(r=>r.marca))));

  if(cfg.conBodega){
    var bods = (cfg.DATA.bodegasIncluidas||[]);
    var cont = document.getElementById('bodegas_chkBodegas');
    cont.innerHTML = bods.map(function(b){
      return '<label><input type="checkbox" class="bodegaChk" value="'+esc(b.simbolo)+'" checked onchange="render(&#39;bodegas&#39;)">'+
        esc(b.simbolo)+' — '+esc(b.nombre)+'</label>';
    }).join('');
  }
}

function bodegasSeleccionadas(){
  return Array.from(document.querySelectorAll('.bodegaChk:checked')).map(function(c){return c.value;});
}

function filtrar(v){
  var cfg=VISTAS[v];
  var buscar=($(v,'qBuscar').value||'').toLowerCase();
  var tipoDoc=$(v,'qTipoDoc').value;
  var usuario=$(v,'qUsuario').value;
  var familia=$(v,'qFamilia').value;
  var marca=$(v,'qMarca').value;
  var dMin=parseInt($(v,'qDiasMin').value); if(isNaN(dMin)) dMin=-Infinity;
  var dMax=parseInt($(v,'qDiasMax').value); if(isNaN(dMax)) dMax=Infinity;
  var fDesde=$(v,'qFechaDesde').value;
  var fHasta=$(v,'qFechaHasta').value;
  var bodSel = cfg.conBodega ? bodegasSeleccionadas() : null;

  return cfg.REG.filter(function(r){
    if(bodSel && bodSel.indexOf(r.bodega)<0) return false;
    if(tipoDoc && r.tipoDocNombre!==tipoDoc) return false;
    if(usuario && r.usuario!==usuario) return false;
    if(familia && r.familia!==familia) return false;
    if(marca && r.marca!==marca) return false;
    var d = (r.diasAntiguedad!=null)?r.diasAntiguedad:Infinity;
    if(d<dMin||d>dMax) return false;
    if(fDesde && (!r.fechaRegistroIso || r.fechaRegistroIso<fDesde)) return false;
    if(fHasta && (!r.fechaRegistroIso || r.fechaRegistroIso>fHasta)) return false;
    if(buscar && (r.codigoTecnico||'').toLowerCase().indexOf(buscar)<0 && (r.descripcion||'').toLowerCase().indexOf(buscar)<0) return false;
    return true;
  });
}

function render(v){
  var cfg=VISTAS[v];
  cfg.FIL = filtrar(v);
  var FIL = cfg.FIL;
  $(v,'count').textContent = FIL.length+' / '+cfg.REG.length+' códigos';

  var totalVal=0, sinMov=0, maxDias=0, stockNeg=0;
  FIL.forEach(function(r){
    var qty=(r.fisico!=null?r.fisico:r.disp)||0;
    totalVal += qty*(r.costo||0);
    if(!r.tipoDoc) sinMov++;
    if((r.disp||0)<0 || (r.fisico||0)<0) stockNeg++;
    if((r.diasAntiguedad||0) > maxDias) maxDias = r.diasAntiguedad||0;
  });
  $(v,'kpis').innerHTML =
    '<div class="kpi"><div class="l">Códigos</div><div class="n">'+FIL.length+'</div></div>'+
    '<div class="kpi"><div class="l">Valorizado</div><div class="n">'+clp(totalVal)+'</div></div>'+
    '<div class="kpi red"><div class="l">Sin movimiento SQL</div><div class="n">'+sinMov+'</div></div>'+
    '<div class="kpi red"><div class="l">Stock negativo (s/recepción)</div><div class="n">'+stockNeg+'</div></div>'+
    '<div class="kpi"><div class="l">Máx. días</div><div class="n">'+maxDias+'</div></div>';

  $(v,'tbody').innerHTML = FIL.map(function(r){
    var dias = r.diasAntiguedad!=null? r.diasAntiguedad : '—';
    var dcls = (typeof dias==='number')? (dias>=90?'d90':dias>=30?'d30':'') : '';
    var qty = (r.fisico!=null?r.fisico:r.disp)||0;
    var val = qty*(r.costo||0);
    var sinDatos = !r.tipoDoc;
    var bodCell = cfg.conBodega ? ('<td class="mono">'+esc(r.bodega)+'</td>') : '';
    return '<tr>'+bodCell+
      '<td class="mono">'+esc(r.codigoTecnico)+'</td>'+
      '<td class="desc">'+esc(r.descripcion)+'</td>'+
      '<td>'+esc(r.marca)+'</td>'+
      '<td>'+esc(r.familia)+'</td>'+
      '<td>'+(sinDatos?'<span class="badge-na">s/d</span>':esc(r.tipoDocNombre||r.tipoDoc))+'</td>'+
      '<td class="right mono">'+(r.folio&&r.folio!=='0'?esc(r.folio):'<span class="badge-na">s/nº</span>')+'</td>'+
      '<td class="right">'+numCell(r.disp)+'</td>'+
      '<td class="right">'+numCell(r.fisico)+'</td>'+
      '<td class="right">'+clp(r.costo)+'</td>'+
      '<td class="center">'+esc(r.fechaRegistro)+'</td>'+
      '<td class="right '+dcls+'">'+dias+'</td>'+
      '<td class="right">'+clpCell(val)+'</td>'+
      '<td>'+esc(r.usuario)+'</td>'+
      '<td>'+esc(r.estacionPc)+'</td>'+
      '<td class="center">'+esc(r.fechaRegistroSistema)+'</td>'+
      '<td class="obs">'+esc(r.observacion)+'</td>'+
      '</tr>';
  }).join('');
}

var HEADERS_BASE = ['Código','Descripción','Marca','Familia','Tipo Doc.','Folio','Disp.','Físico',
  'Costo unit.','Fecha Reg.','Días','Valorizado','Usuario','Estación / PC','Fecha registro sistema','Observación'];

function headers(v){
  return VISTAS[v].conBodega ? ['Bodega'].concat(HEADERS_BASE) : HEADERS_BASE;
}

function filaArray(v, r){
  var qty=(r.fisico!=null?r.fisico:r.disp)||0;
  var base = [r.codigoTecnico, r.descripcion, r.marca||'', r.familia||'',
    r.tipoDocNombre||r.tipoDoc||'s/d', r.folio||'', r.disp||0, r.fisico||0,
    Math.round(r.costo||0), r.fechaRegistro||'', r.diasAntiguedad!=null?r.diasAntiguedad:'',
    Math.round(qty*(r.costo||0)), r.usuario||'', r.estacionPc||'', r.fechaRegistroSistema||'', r.observacion||''];
  return VISTAS[v].conBodega ? [r.bodega].concat(base) : base;
}

// Los botones de descarga/correo SIEMPRE usan FIL de la vista activa (lo que el usuario ve filtrado en pantalla).
function exportarExcel(v){
  var FIL=VISTAS[v].FIL;
  if(!FIL.length){ alert('No hay datos para exportar con el filtro actual.'); return; }
  var rows=[headers(v)].concat(FIL.map(function(r){return filaArray(v,r);}));
  var ws=XLSX.utils.aoa_to_sheet(rows);
  var wb=XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb,ws,VISTAS[v].label);
  XLSX.writeFile(wb,'Isabel_Riquelme_'+v+'_'+new Date().toISOString().slice(0,10)+'.xlsx');
}

function exportarHtml(v){
  var FIL=VISTAS[v].FIL;
  if(!FIL.length){ alert('No hay datos para exportar con el filtro actual.'); return; }
  var H=headers(v);
  var thead='<tr>'+H.map(function(h){return '<th style="background:#111827;color:#fff;padding:6px 8px;text-align:left">'+esc(h)+'</th>';}).join('')+'</tr>';
  var tbody=FIL.map(function(r){
    return '<tr>'+filaArray(v,r).map(function(val){return '<td style="padding:5px 8px;border-bottom:1px solid #eee">'+esc(val)+'</td>';}).join('')+'</tr>';
  }).join('');
  var html='<!DOCTYPE html><html><head><meta charset="UTF-8"><title>'+esc(VISTAS[v].label)+' Isabel Riquelme</title></head>'+
    '<body><h2>Análisis '+esc(VISTAS[v].label)+' — Sucursal Isabel Riquelme</h2>'+
    '<p style="font-size:12px;color:#666">Exportado: '+new Date().toLocaleString('es-CL')+' · '+FIL.length+' registros</p>'+
    '<table style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:12px"><thead>'+thead+'</thead><tbody>'+tbody+'</tbody></table></body></html>';
  var blob=new Blob([html],{type:'text/html;charset=utf-8'});
  var a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download='Isabel_Riquelme_'+v+'_'+new Date().toISOString().slice(0,10)+'.html';
  a.click();
}

function enviarCorreo(v){
  var cfg=VISTAS[v], FIL=cfg.FIL;
  if(!FIL.length){ alert('No hay datos para enviar con el filtro actual.'); return; }
  var totalVal=FIL.reduce(function(s,r){var qty=(r.fisico!=null?r.fisico:r.disp)||0; return s+qty*(r.costo||0);},0);
  var asunto=cfg.label+' — Sucursal Isabel Riquelme — '+FIL.length+' códigos';
  var cuerpo='ANÁLISIS '+cfg.label.toUpperCase()+' — SUCURSAL ISABEL RIQUELME\n'+
    'Generado: '+cfg.DATA.generado+'\n'+
    'Códigos filtrados: '+FIL.length+' / '+cfg.REG.length+'\n'+
    'Valorizado total: $'+fmt(totalVal)+'\n\n'+
    'Detalle (primeros 40):\n'+
    FIL.slice(0,40).map(function(r,i){
      return (i+1)+'. '+(cfg.conBodega?r.bodega+' ':'')+r.codigoTecnico+' — '+(r.descripcion||'').substring(0,50)+' | '+
        (r.tipoDocNombre||r.tipoDoc||'s/d')+' | '+r.diasAntiguedad+' dias | $'+fmt((r.fisico||r.disp||0)*(r.costo||0))+
        ' | '+(r.usuario||'-')+' / '+(r.estacionPc||'-');
    }).join('\n')+
    (FIL.length>40?'\n... y '+(FIL.length-40)+' más (ver Excel adjunto descargado aparte).':'')+
    '\n\n--- Generado desde reporte local Ferretería Oviedo ---';
  var mailto='mailto:?subject='+encodeURIComponent(asunto)+'&body='+encodeURIComponent(cuerpo);
  window.open(mailto,'_self');
}
// render('merma')/render('bodegas') ya no se llaman aqui — los dispara
// cargarDatosFirestore() (via onAuthStateChanged) una vez el usuario inicia sesion.
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
