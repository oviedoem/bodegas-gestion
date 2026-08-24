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
      -- GEI (egreso inventario) y GST (solicitud traslado) excluidos: son egresos/no entradas
      -- igual que panel admin descargar_bod.py y los otros scripts de este proyecto
      AND MD.DOC IN ('GRC','GRT','GME','GIB','Gdc','GBR','GRP','GRI','GRN','GIN','GDC','GDV','GII','GTS')
)
SELECT DISTINCT
    D.SIMBOLO_BODEGA                                       AS BODEGA,
    N.DOC                                                  AS TIPO_DOC,
    N.NUMERO                                               AS FOLIO,
    A.CODIGO_TECNICO,
    B.DESCRIPCION,
    CAST(ISNULL(A.ST_DISPONIBLE,0)                    AS DECIMAL(18,2))  AS STOCK_DISPONIBLE,
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
    ON N.IDBODEGA = A.IDBODEGA AND N.CODIGO_TECNICO = A.CODIGO_TECNICO
    -- OJO: NO filtrar por N.IDSUCURSAL = A.IDSUCURSAL. El documento puede quedar
    -- grabado con el IDSUCURSAL de origen del traslado (confirmado en ref. descargar_bod.py).
LEFT JOIN Foviedo.dbo.M_Documentos_Encabezado_Observacion G
    ON G.IDDOCUMENTO = N.IDDOCUMENTO AND G.IDNUMERO = N.IDNUMERO
LEFT JOIN Foviedo.dbo.M_DOCUMENTOS_ENCABEZADO ENC
    ON ENC.IDDOCUMENTO = N.IDDOCUMENTO AND ENC.IDNUMERO = N.IDNUMERO
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


# Vistas nuevas del proyecto BODEGAS GESTION (id_js, emoji+label boton tab, label largo).
# Datos vienen de bodegas_gestion.json / coleccion Firestore 'bodegas_gestion' (ver
# generar_bodegas_gestion.py e IDS_REFERENCIA_BODEGAS_GESTION.md).
VISTAS_GESTION_DEF = [
    ("elmanzano",  "🏭 El Manzano",            "El Manzano"),
    ("sanvicente", "🏬 San Vicente",           "San Vicente"),
    ("lascabras",  "🏬 Las Cabras",            "Las Cabras"),
    ("litueche",   "🏬 Litueche",              "Litueche"),
    ("cd",         "📦 Compartidas",           "Bodegas Compartidas (CD/Desp.Prov./Remate/Marketing)"),
]

PANEL_GESTION_TEMPLATE = """
<div class="card tab-panel" id="panel___VID__">
  <div class="sub" id="meta___VID__"></div>
  <div class="chk-row" id="__VID___chkBodegas"></div>
  <div class="bar">
    <input type="text" id="__VID___qBuscar" placeholder="Código o descripción" oninput="render('__VID__')" style="width:200px">
    <select id="__VID___qTipoDoc" onchange="render('__VID__')"><option value="">Todos los tipos de documento</option></select>
    <select id="__VID___qUsuario" onchange="render('__VID__')"><option value="">Todos los usuarios</option></select>
    <select id="__VID___qFamilia" onchange="render('__VID__')"><option value="">Todas las familias</option></select>
    <select id="__VID___qMarca" onchange="render('__VID__')"><option value="">Todas las marcas</option></select>
    <label>Días ≥ <input type="number" id="__VID___qDiasMin" style="width:55px" oninput="render('__VID__')"></label>
    <label>Días ≤ <input type="number" id="__VID___qDiasMax" style="width:55px" oninput="render('__VID__')"></label>
    <label>Desde <input type="date" id="__VID___qFechaDesde" oninput="render('__VID__')"></label>
    <label>Hasta <input type="date" id="__VID___qFechaHasta" oninput="render('__VID__')"></label>
  </div>
  <div class="bar">
    <button class="btn btn-excel" onclick="exportarExcel('__VID__')">📊 Descargar Excel</button>
    <button class="btn btn-html" onclick="exportarHtml('__VID__')">🌐 Descargar HTML</button>
    <button class="btn btn-mail" onclick="enviarCorreo('__VID__')">✉️ Enviar por correo</button>
    <span id="__VID___count"></span>
  </div>
  <div class="kpis" id="__VID___kpis"></div>
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
    <tbody id="__VID___tbody"></tbody>
  </table>
  </div>
  <div class="footer-note">Ferretería Oviedo · Reporte generado desde sistema interno — no contiene credenciales</div>
</div>
"""


def generar_html(data):
    # IMPORTANTE: el HTML publicado en GitHub Pages ya NO embebe los datos crudos.
    # Los datos viven en Firestore (proyecto isabel-riquelme-merma) y se cargan en el
    # navegador SOLO despues de iniciar sesion (ver firestore.rules: auth != null).
    # generar_bodegas_ir.py / generar_merma_ir.py / generar_bodegas_gestion.py siguen
    # escribiendo los JSON locales que luego sube _subir_datos_firestore.py — ese paso
    # es manual/script aparte, no parte del HTML.
    logo_b64 = LOGO_B64.read_text(encoding="utf-8").strip() if LOGO_B64.exists() else ""

    tabs_gestion = "\n".join(
        f'  <button class="tab-btn" id="tabBtn_{vid}" onclick="cambiarTab(\'{vid}\')">{tab_label}</button>'
        for vid, tab_label, _ in VISTAS_GESTION_DEF
    )
    panels_gestion = "\n".join(
        PANEL_GESTION_TEMPLATE.replace("__VID__", vid) for vid, _, _ in VISTAS_GESTION_DEF
    )
    vistas_gestion_ids = json.dumps([vid for vid, _, _ in VISTAS_GESTION_DEF])
    vistas_gestion_js = ",\n  ".join(
        f"{vid}: {{ DATA: {{registros:[]}}, conBodega:true, label:{json.dumps(label)} }}"
        for vid, _, label in VISTAS_GESTION_DEF
    )

    html = (HTML_TEMPLATE
            .replace("__LOGO_B64__", logo_b64)
            .replace("__TABS_GESTION__", tabs_gestion)
            .replace("__PANELS_GESTION__", panels_gestion)
            .replace("__VISTAS_GESTION_IDS__", vistas_gestion_ids)
            .replace("__VISTAS_GESTION_JS__", vistas_gestion_js))
    OUT_HTML.write_text(html, encoding="utf-8")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<meta name="theme-color" content="#1d4ed8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="manifest" href="manifest.json">
<title>Bodegas Gestión — Ferretería Oviedo</title>
<script src="https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.22.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.22.0/firebase-auth-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.22.0/firebase-firestore-compat.js"></script>
<style>
  /* ── LOGIN SCREEN (ferresystem design) ─────────────────────────── */
  #loginScreen{position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;overflow:hidden;background:#070b14}
  #particleBg{position:absolute;inset:0;background:linear-gradient(135deg,#070b14 0%,#0b1220 40%,#0d1829 70%,#060a12 100%);z-index:0}
  #particleCanvas{position:absolute;inset:0;z-index:1}
  .lg-card{position:relative;z-index:2;background:rgba(10,18,35,0.78);backdrop-filter:blur(28px);-webkit-backdrop-filter:blur(28px);border:1px solid rgba(99,179,237,0.14);border-radius:22px;padding:40px 36px 36px;width:340px;max-width:92vw;text-align:center;box-shadow:0 24px 80px rgba(0,0,0,.55)}
  .lg-badge{display:inline-flex;align-items:center;gap:6px;background:rgba(37,99,235,0.18);border:1px solid rgba(59,130,246,0.35);border-radius:20px;padding:5px 13px;margin-bottom:20px;font-size:11px;font-weight:700;color:#93c5fd;letter-spacing:.5px;text-transform:uppercase}
  .lg-dot{width:7px;height:7px;border-radius:50%;background:#22d3ee;animation:pulse-dot 1.6s ease-in-out infinite}
  .lg-icon{width:64px;height:64px;border-radius:50%;background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 60%,#3b82f6 100%);display:flex;align-items:center;justify-content:center;margin:0 auto 18px;box-shadow:0 0 0 0 rgba(59,130,246,.5);animation:pulse-icon 2s ease-in-out infinite}
  .lg-icon svg{width:32px;height:32px;fill:none;stroke:#fff;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
  .lg-title{font-size:20px;font-weight:800;color:#e2e8f0;margin:0 0 4px;letter-spacing:-.3px}
  .lg-sub{font-size:12px;color:#64748b;margin:0 0 26px}
  .lg-label{display:block;font-size:11px;font-weight:700;color:#64748b;text-align:left;margin-bottom:4px;text-transform:uppercase;letter-spacing:.5px}
  .lg-input-wrap{position:relative;margin-bottom:14px}
  .lg-input{width:100%;padding:12px 14px;background:rgba(15,23,42,0.7);border:1px solid rgba(99,179,237,0.2);border-radius:10px;font-size:14px;color:#e2e8f0;font-family:inherit;box-sizing:border-box;outline:none;transition:border-color .2s}
  .lg-input:focus{border-color:rgba(59,130,246,.6)}
  .lg-toggle{position:absolute;right:11px;top:50%;transform:translateY(-50%);background:none;border:none;cursor:pointer;color:#64748b;padding:2px;display:flex;align-items:center}
  .lg-btn{width:100%;padding:13px;background:linear-gradient(135deg,#1d4ed8 0%,#3b82f6 100%);color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;font-family:inherit;margin-top:6px;animation:pulse-btn 2.2s ease-in-out infinite;transition:opacity .2s}
  .lg-btn:hover{opacity:.88}
  .lg-err{color:#f87171;font-size:12px;margin-top:10px;min-height:16px}
  @keyframes pulse-dot{0%,100%{opacity:1}50%{opacity:.3}}
  @keyframes pulse-icon{0%,100%{box-shadow:0 0 0 0 rgba(59,130,246,.5)}70%{box-shadow:0 0 0 14px rgba(59,130,246,0)}}
  @keyframes pulse-btn{0%,100%{box-shadow:0 4px 16px rgba(0,0,0,.25),0 0 0 0 rgba(255,255,255,.4)}50%{box-shadow:0 4px 16px rgba(0,0,0,.25),0 0 0 8px rgba(255,255,255,0)}}
  /* ── INSTALL BANNER ────────────────────────────────────────────── */
  #installBanner{position:fixed;bottom:0;left:0;right:0;z-index:8888;display:none;background:linear-gradient(135deg,#1e3a8a,#2563eb);color:#fff;padding:14px 20px;align-items:center;gap:14px;box-shadow:0 -4px 24px rgba(0,0,0,.35);animation:slideUp .4s cubic-bezier(.22,1,.36,1)}
  @keyframes slideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}
  #installBanner .ib-icon{font-size:26px;flex-shrink:0;animation:pulse-icon 2s ease-in-out infinite}
  #installBanner .ib-text{flex:1}
  #installBanner .ib-text b{display:block;font-size:14px;font-weight:800}
  #installBanner .ib-text span{font-size:12px;opacity:.8}
  #installBanner .ib-btn{background:#fff;color:#1d4ed8;border:none;border-radius:8px;padding:10px 18px;font-weight:800;font-size:13px;cursor:pointer;white-space:nowrap;animation:pulse-btn 2.2s ease-in-out infinite}
  #installBanner .ib-close{background:none;border:none;color:#fff;font-size:20px;cursor:pointer;opacity:.7;flex-shrink:0;padding:0 4px}
  /* ── APP ───────────────────────────────────────────────────────── */
  #appRoot{display:none}
  .btn-logout{background:#374151;color:#fff;border:none;border-radius:6px;padding:6px 12px;font-size:12px;
              font-weight:700;cursor:pointer;font-family:inherit;margin-left:auto}
  :root{--naranja:#2563eb;--naranja2:#1d4ed8;--dark:#111827;--border:#e5e7eb;--gris:#6b7280;
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
  <div id="particleBg"></div>
  <canvas id="particleCanvas"></canvas>
  <div class="lg-card">
    <div class="lg-badge"><span class="lg-dot"></span>Sistema Activo</div>
    <div class="lg-icon">
      <svg viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
    </div>
    <div class="lg-title">Bodegas Gestión</div>
    <div class="lg-sub">Ferretería Oviedo — Acceso restringido</div>
    <label class="lg-label">Usuario</label>
    <div class="lg-input-wrap">
      <input class="lg-input" type="text" id="loginUser" placeholder="riquelme" autocomplete="username">
    </div>
    <label class="lg-label">Contraseña</label>
    <div class="lg-input-wrap">
      <input class="lg-input" type="password" id="loginPass" placeholder="••••••••" autocomplete="current-password">
      <button class="lg-toggle" type="button" onclick="lgTogglePass()" title="Mostrar/ocultar">
        <svg id="lgEyeIcon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
      </button>
    </div>
    <button class="lg-btn" onclick="doLogin()">Ingresar</button>
    <div class="lg-err" id="loginErr"></div>
  </div>
</div>

<div id="installBanner">
  <span class="ib-icon">📲</span>
  <div class="ib-text"><b>Instalar aplicación</b><span>Accede más rápido desde tu pantalla de inicio</span></div>
  <button class="ib-btn" id="installBtn">Instalar</button>
  <button class="ib-close" onclick="document.getElementById('installBanner').style.display='none'">✕</button>
</div>

<div id="appRoot">
<div class="topbar">
  <img src="data:image/jpeg;base64,__LOGO_B64__" alt="Ferretería Oviedo">
  <div>
    <h1>Bodegas Gestión — Ferretería Oviedo</h1>
    <div class="sub">Datos protegidos — requieren inicio de sesión (Firebase Auth + Firestore rules)</div>
  </div>
  <button class="btn-logout" onclick="doLogout()">Cerrar sesión</button>
</div>
<div class="tabs">
  <button class="tab-btn active" id="tabBtn_merma" onclick="cambiarTab('merma')">📦 Merma (Bodega MIR)</button>
  <button class="tab-btn" id="tabBtn_bodegas" onclick="cambiarTab('bodegas')">🏬 Otras Bodegas IR</button>
__TABS_GESTION__
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
  <div class="footer-note">Ferretería Oviedo · Reporte generado desde sistema interno — no contiene credenciales</div>
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
  <div class="footer-note">Ferretería Oviedo · Reporte generado desde sistema interno — no contiene credenciales</div>
</div>

__PANELS_GESTION__

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

function lgTogglePass(){
  var p = document.getElementById('loginPass');
  var icon = document.getElementById('lgEyeIcon');
  if(p.type === 'password'){
    p.type = 'text';
    icon.innerHTML = '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>';
  } else {
    p.type = 'password';
    icon.innerHTML = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
  }
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

// TEMPORAL (2026-07-21): Firestore agoto su cuota gratuita de escrituras subiendo
// 'bodegas'/'bodegas_gestion' (esquema 1-doc-por-codigo, ~14000 escrituras). Mientras
// no resetea, esas dos colecciones se leen de los JSON estaticos publicados junto al
// HTML (bodegas_ir_otras.json / bodegas_gestion.json) en vez de Firestore. 'merma'
// sigue viniendo de Firestore normal (no se toco, sigue con cuota disponible).
// Revertir cuando la cuota resetee: volver a leer 'bodegas'/'bodegas_gestion' de
// Firestore (ver historial git de esta funcion) y considerar el esquema chunked
// (1 doc grande por sucursal en vez de 1 por codigo) para no volver a agotarla.
function vistaDeSucursal(idSucursal){
  return {"04":"elmanzano","05":"sanvicente","06":"lascabras","11":"litueche"}[idSucursal];
}

function cargarDatosFirestore(){
  Promise.all([
    db.collection('merma_meta').doc('info').get(),
    db.collection('merma').get(),
    fetch('bodegas_ir_otras.json').then(function(r){ return r.json(); }),
    fetch('bodegas_gestion.json').then(function(r){ return r.json(); }),
  ]).then(function(res){
    var metaMerma = res[0].exists ? res[0].data() : {};
    var regMerma = snapshotToRegistros(res[1]);
    var dataBod = res[2];
    var dataGestion = res[3];

    VISTAS.merma.DATA = Object.assign({registros: regMerma}, metaMerma);
    VISTAS.bodegas.DATA = dataBod;

    dataGestion.sucursales.forEach(function(s){
      var v = vistaDeSucursal(s.idSucursal);
      VISTAS[v].DATA = {
        registros: s.registros, generado: dataGestion.generado, fuente: dataGestion.fuente,
        bodegasIncluidas: s.bodegasIncluidas,
      };
    });
    VISTAS.cd.DATA = {
      registros: dataGestion.compartidas.registros, generado: dataGestion.generado, fuente: dataGestion.fuente,
      bodegasIncluidas: dataGestion.compartidas.bodegasIncluidas,
    };

    Object.keys(VISTAS).forEach(function(v){ initVista(v); render(v); });
  }).catch(function(e){
    document.getElementById('appRoot').innerHTML =
      '<div style="padding:40px;text-align:center;color:#dc2626">Error cargando datos: '+e.message+'</div>';
  });
}

// ── Datasets (uno por pestaña) — se llenan via Firestore tras login ─────────
var VISTAS_GESTION = __VISTAS_GESTION_IDS__;
var VISTAS = {
  merma:   { DATA: {registros:[]}, conBodega:false, label:'Merma IR' },
  bodegas: { DATA: {registros:[]}, conBodega:true,  label:'Otras Bodegas IR' },
  __VISTAS_GESTION_JS__
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
  // Recalcular diasAntiguedad en tiempo real desde fechaRegistroIso
  var _HOY = new Date(); _HOY.setHours(0,0,0,0);
  REG.forEach(function(r){
    if(r.fechaRegistroIso){
      r.diasAntiguedad = Math.floor((_HOY - new Date(r.fechaRegistroIso)) / 86400000);
    }
  });
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
    var cont = document.getElementById(v+'_chkBodegas');
    cont.innerHTML = bods.map(function(b){
      return '<label><input type="checkbox" class="bodegaChk" value="'+esc(b.simbolo)+'" checked onchange="render(&#39;'+v+'&#39;)">'+
        esc(b.simbolo)+' — '+esc(b.nombre)+'</label>';
    }).join('');
  }
}

function bodegasSeleccionadas(v){
  return Array.from(document.querySelectorAll('#'+v+'_chkBodegas .bodegaChk:checked')).map(function(c){return c.value;});
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
  var bodSel = cfg.conBodega ? bodegasSeleccionadas(v) : null;

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
  XLSX.writeFile(wb,'Bodegas_Gestion_'+v+'_'+new Date().toISOString().slice(0,10)+'.xlsx');
}

function exportarHtml(v){
  var FIL=VISTAS[v].FIL;
  if(!FIL.length){ alert('No hay datos para exportar con el filtro actual.'); return; }
  var H=headers(v);
  var thead='<tr>'+H.map(function(h){return '<th style="background:#111827;color:#fff;padding:6px 8px;text-align:left">'+esc(h)+'</th>';}).join('')+'</tr>';
  var tbody=FIL.map(function(r){
    return '<tr>'+filaArray(v,r).map(function(val){return '<td style="padding:5px 8px;border-bottom:1px solid #eee">'+esc(val)+'</td>';}).join('')+'</tr>';
  }).join('');
  var html='<!DOCTYPE html><html><head><meta charset="UTF-8"><title>'+esc(VISTAS[v].label)+' — Bodegas Gestión</title></head>'+
    '<body><h2>'+esc(VISTAS[v].label)+' — Bodegas Gestión</h2>'+
    '<p style="font-size:12px;color:#666">Exportado: '+new Date().toLocaleString('es-CL')+' · '+FIL.length+' registros</p>'+
    '<table style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:12px"><thead>'+thead+'</thead><tbody>'+tbody+'</tbody></table></body></html>';
  var blob=new Blob([html],{type:'text/html;charset=utf-8'});
  var a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download='Bodegas_Gestion_'+v+'_'+new Date().toISOString().slice(0,10)+'.html';
  a.click();
}

function enviarCorreo(v){
  var cfg=VISTAS[v], FIL=cfg.FIL;
  if(!FIL.length){ alert('No hay datos para enviar con el filtro actual.'); return; }
  var totalVal=FIL.reduce(function(s,r){var qty=(r.fisico!=null?r.fisico:r.disp)||0; return s+qty*(r.costo||0);},0);
  var asunto=cfg.label+' — Bodegas Gestión — '+FIL.length+' códigos';
  var cuerpo='ANÁLISIS '+cfg.label.toUpperCase()+' — BODEGAS GESTIÓN\n'+
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

// ── PARTÍCULAS LOGIN (constellation azul) ──────────────────────────
(function(){
  var canvas = document.getElementById('particleCanvas');
  if(!canvas) return;
  var ctx = canvas.getContext('2d');
  var W, H, pts, mouse = {x:-9999,y:-9999};
  var C = {n:80, maxDist:120, ptColor:'rgba(99,179,237,', lineColor:'rgba(99,179,237,', ptR:2, repel:100, speed:.5};
  function resize(){ W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; }
  function init(){
    pts = [];
    for(var i=0;i<C.n;i++) pts.push({x:Math.random()*W,y:Math.random()*H,vx:(Math.random()-.5)*C.speed,vy:(Math.random()-.5)*C.speed});
  }
  function draw(){
    ctx.clearRect(0,0,W,H);
    for(var i=0;i<pts.length;i++){
      var p=pts[i];
      var dx=mouse.x-p.x, dy=mouse.y-p.y, dist2=dx*dx+dy*dy;
      if(dist2<C.repel*C.repel && dist2>0){var f=C.repel/Math.sqrt(dist2);p.vx-=dx/dist2*f*.2;p.vy-=dy/dist2*f*.2;}
      p.x+=p.vx; p.y+=p.vy;
      if(p.x<0||p.x>W) p.vx*=-1; if(p.y<0||p.y>H) p.vy*=-1;
      ctx.beginPath(); ctx.arc(p.x,p.y,C.ptR,0,Math.PI*2);
      ctx.fillStyle=C.ptColor+'0.8)'; ctx.fill();
    }
    for(var i=0;i<pts.length;i++) for(var j=i+1;j<pts.length;j++){
      var dx=pts[i].x-pts[j].x, dy=pts[i].y-pts[j].y, d=Math.sqrt(dx*dx+dy*dy);
      if(d<C.maxDist){
        ctx.beginPath(); ctx.moveTo(pts[i].x,pts[i].y); ctx.lineTo(pts[j].x,pts[j].y);
        ctx.strokeStyle=C.lineColor+(1-d/C.maxDist)*.5+')'; ctx.lineWidth=.8; ctx.stroke();
      }
    }
    requestAnimationFrame(draw);
  }
  window.addEventListener('resize', function(){resize();init();});
  canvas.addEventListener('mousemove', function(e){mouse.x=e.clientX;mouse.y=e.clientY;});
  canvas.addEventListener('mouseleave', function(){mouse.x=-9999;mouse.y=-9999;});
  canvas.addEventListener('touchmove', function(e){var t=e.touches[0];mouse.x=t.clientX;mouse.y=t.clientY;},{passive:true});
  resize(); init(); draw();
})();

// ── PWA: Service Worker + Install Banner ───────────────────────────
if('serviceWorker' in navigator){
  navigator.serviceWorker.register('sw.js',{updateViaCache:'none'}).then(function(reg){
    reg.update();
  });
}
var _deferredInstall = null;
window.addEventListener('beforeinstallprompt', function(e){
  e.preventDefault(); _deferredInstall = e;
  var b = document.getElementById('installBanner');
  if(b){ b.style.display='flex'; }
});
document.getElementById('installBtn') && document.getElementById('installBtn').addEventListener('click', function(){
  if(_deferredInstall){ _deferredInstall.prompt(); _deferredInstall.userChoice.then(function(){ _deferredInstall=null; document.getElementById('installBanner').style.display='none'; }); }
});
window.addEventListener('appinstalled', function(){ document.getElementById('installBanner').style.display='none'; });
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
