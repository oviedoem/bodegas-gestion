"""
generar_bodegas_sv_ssrs.py
Genera bodegas_sv_ssrs_test.json con stock + diasAntiguedad de bodegas San Vicente
SIN usar SQL ni pyodbc. Fuentes de datos:

  Paso 2 — Stock actual:
    GET Reporte_Bodegas_Detalle.asp (sesion WebForms: login con USER+CLAVE)

  Paso 3 — diasAntiguedad (ultima entrada GRT por codigo):
    GET VisorRS.aspx?xToken=...&xInforme=...&rs:Format=CSV  (SSRS CSV export)
    Candidatos de nombre de informe probados en orden hasta el primero que devuelva CSV.

Credenciales: busca credenciales_erp.ini en rutas candidatas (sección [ERP]).
Clave TOKEN_RECEPCION leida como token alternativo si XTOKEN no está disponible.

Bodegas San Vicente: IDs verificados via P_BODEGAS (generar_bodegas_gestion.py 2026-07-21).

Salida: E:\ISABEL RIQUELME\bodegas_sv_ssrs_test.json
"""
import configparser
import csv
import datetime
import io
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar
from pathlib import Path

# ── Constantes ─────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent          # E:\ISABEL RIQUELME\
OUT_JSON  = BASE_DIR / "bodegas_sv_ssrs_test.json"
FECHA_INI = "2026-01-01"

# Rutas candidatas para credenciales_erp.ini — la tarea pide la primera ruta
# pero el archivo real (con TOKEN_RECEPCION) vive en la ruta alternativa.
_CRED_PATHS = [
    Path(r"E:\ferreteria-oviedo\credenciales_erp.ini"),
    Path(r"E:\ferreteria-oviedo\CATALOGO PRODUCTOS\scripts\credenciales_erp.ini"),
    Path(r"E:\ferreteria-oviedo\VENTAS EL MANZANO\credenciales_erp.ini"),
]

# Bodegas San Vicente — IDs verificados SQL 2026-07-21 en generar_bodegas_gestion.py.
# Nota: el ERP tiene dos bodegas con SIMBOLO_BODEGA='CSV' (id=44 Calzada, id=43 Consumo).
# En este script usamos el nombre expandido para evitar colisiones de clave.
BODEGAS_SV = [
    # (idbodega, simbolo, nombre_largo, idsucursal_erp)
    # IDs verificados via API /parametros/generales/bodegas/items 13-08-2026
    (39, "SSV", "Sala San Vicente",           "05"),  # bodega de venta principal
    (40, "PSV", "Patio San Vicente",          "05"),  # bodega patio
    (41, "GSV", "Gestion San Vicente",        "05"),  # bodega de gestion
    (45, "TSV", "Transito San Vicente",       "05"),  # transito (en camino)
    (88, "DSV", "Distribucion San Vicente",   "05"),
    (95, "ESV", "Exhibicion San Vicente",     "05"),
]

DOC_NOMBRES = {
    "GRT": "Guia Recepcion Traslado",
    "GRC": "Guia Recepcion Compra",
    "GIB": "Guia Ingreso Entre Bodegas",
    "GII": "Guia Ingreso Inventario",
    "GME": "Guia Elect. Despacho Factura",
    "Gdc": "Guia Devolucion Cliente",
    "GTS": "Guia Traslados Entre Sucursales",
    "GDV": "Guia Despacho Venta",
}

# Candidatos de nombre de informe SSRS GRT — probados en orden.
# El primero de la lista es el más probable según la convención del proyecto.
# Detalle=True / parámetros de fecha y bodega son nombres hipotéticos hasta
# que se inspeccione el HTML del form en VisorRS.aspx.
GRT_REPORT_NAMES = [
    "RS_Existencias/productos_traslado_productos",
    "RS_Bodegas/traslados_bodegas",
    "RS_Documentos/traslados_entre_bodegas",
    "RS_Bodegas/grt_informe",
    "RS_Documentos/grt_detalle",
    "RS_Bodegas/movimientos_bodega",
]

# Bases URL donde puede estar el proxy VisorRS.aspx
_VISOR_BASES = [
    "",              # relativo a BASE (ej. https://erp.justtime.cl/justweb_foviedo)
    "",              # relativo a BLAZOR_ROOT (ej. https://erp.justtime.cl)
    "/visor",        # sufijo alternativo bajo BLAZOR_ROOT
]

# Nombres de parámetro de fecha y bodega que acepta el report — se prueban combinaciones
_PARAM_COMBOS = [
    {"Fecha_Inicio": None, "Fecha_Fin": None, "Id_Bodega": None},
    {"FechaDesde":   None, "FechaHasta": None, "IdBodega":  None},
    {"Desde":        None, "Hasta":      None, "Bodega":    None},
]


def log(msg):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(str(msg).encode("ascii", errors="replace").decode("ascii"), flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# PASO 1 — Credenciales
# ─────────────────────────────────────────────────────────────────────────────
def leer_credenciales():
    """
    Lee credenciales de la primera ruta candidata que contenga sección [ERP].
    Devuelve dict con: base, blazor, user, clave, xtoken, token_rec, ws.
    """
    cfg = configparser.ConfigParser()
    encontrado = None
    for p in _CRED_PATHS:
        if p.exists():
            cfg.read(str(p), encoding="utf-8")
            if "ERP" in cfg:
                encontrado = p
                break

    if encontrado is None:
        raise FileNotFoundError(
            "No se encontro credenciales_erp.ini con seccion [ERP] en ninguna ruta:\n"
            + "\n".join(f"  {p}" for p in _CRED_PATHS)
        )

    erp = cfg["ERP"]
    return {
        "base":      erp.get("BASE",             "https://erp.justtime.cl/justweb_foviedo"),
        "blazor":    erp.get("BLAZOR_ROOT",      "https://erp.justtime.cl"),
        "user":      erp.get("USER",             ""),
        "clave":     erp.get("CLAVE",            ""),
        "xtoken":    erp.get("XTOKEN",           ""),
        "token_rec": erp.get("TOKEN_RECEPCION",  ""),
        "ws":        erp.get("WS_IP_FALLBACK",   "wsapi.justtime.cl"),
        "_path":     str(encontrado),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades HTTP con soporte de cookies (urllib puro)
# ─────────────────────────────────────────────────────────────────────────────
def _new_opener():
    jar     = http.cookiejar.CookieJar()
    handler = urllib.request.HTTPCookieProcessor(jar)
    opener  = urllib.request.build_opener(handler)
    opener.addheaders = [
        ("User-Agent",      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"),
        ("Accept",          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        ("Accept-Language", "es-CL,es;q=0.9,en;q=0.8"),
    ]
    return opener


def _http_get(opener, url, timeout=30):
    """GET → (html_str, final_url) o (None, mensaje_error)."""
    try:
        with opener.open(url, timeout=timeout) as resp:
            raw = resp.read()
            # El ERP WebForms devuelve iso-8859-1; VisorRS/API devuelven utf-8
            for enc in ("utf-8", "iso-8859-1", "latin-1"):
                try:
                    return raw.decode(enc), resp.geturl()
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", errors="replace"), resp.geturl()
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code} en {url}"
    except urllib.error.URLError as e:
        return None, f"URLError: {e.reason} — {url}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e} — {url}"


def _http_post(opener, url, data_dict, timeout=30):
    """POST urlencoded → (html_str, final_url) o (None, mensaje_error)."""
    body = urllib.parse.urlencode(data_dict).encode("utf-8")
    req  = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace"), resp.geturl()
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code} en {url}"
    except urllib.error.URLError as e:
        return None, f"URLError: {e.reason}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Login WebForms ASP.NET
# ─────────────────────────────────────────────────────────────────────────────
def _extract_input(html, name):
    """Extrae el value de un <input name="..."> con regex."""
    for pat in [
        r'<input[^>]+name=["\']' + re.escape(name) + r'["\'][^>]+value=["\']([^"\']*)["\']',
        r'<input[^>]+value=["\']([^"\']*)["\'][^>]+name=["\']' + re.escape(name) + r'["\']',
    ]:
        m = re.search(pat, html, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1)
    return ""


def login(opener, base, user, clave):
    """
    Login WebForms: GET página de entrada → extraer __VIEWSTATE con regex →
    POST credenciales. Retorna True si la sesión queda activa.
    """
    html, url_final = _http_get(opener, base + "/", timeout=40)
    if html is None:
        log(f"  [login] GET fallido: {url_final}")
        return False

    # Si no hay form de login, quizá ya hay sesión o no necesita auth para este endpoint
    if not re.search(r'__VIEWSTATE', html, re.IGNORECASE):
        log("  [login] Página sin __VIEWSTATE — asumiendo sesión no requerida o ya activa")
        return True

    viewstate = _extract_input(html, "__VIEWSTATE")
    vsg       = _extract_input(html, "__VIEWSTATEGENERATOR")
    evval     = _extract_input(html, "__EVENTVALIDATION")

    if not viewstate:
        log("  [login] __VIEWSTATE no encontrado en la página — login no posible")
        return False

    data = {
        "__EVENTTARGET":        "",
        "__EVENTARGUMENT":      "",
        "__VIEWSTATE":          viewstate,
        "__VIEWSTATEGENERATOR": vsg,
        "__EVENTVALIDATION":    evval,
        "Login1$txtUsuario":    user,
        "Login1$txtClave":      clave,
        "Login1$CmdAceptar":    "Ingresar",
    }
    html2, url2 = _http_post(opener, url_final or (base + "/"), data, timeout=40)
    if html2 is None:
        log(f"  [login] POST fallido: {url2}")
        return False

    if re.search(r'(login|ingresar)', url2, re.IGNORECASE) and re.search(
        r'(Login1\$txtUsuario|CmdAceptar)', html2, re.IGNORECASE
    ):
        log("  [login] Login fallido — credenciales incorrectas o URL inesperada")
        return False

    log(f"  [login] OK → {url2[:80]}")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# PASO 2 — Stock actual via API wsapi.justtime.cl (EstadisticasStock/Lista)
# ─────────────────────────────────────────────────────────────────────────────
_WS_BASE = "https://wsapi.justtime.cl/api/v1"

def _api_post(path, body, timeout=60):
    data = json.dumps(body).encode()
    req  = urllib.request.Request(_WS_BASE + path, data=data,
           headers={"Accept": "application/json", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, str(e)

def _api_get(path, timeout=30):
    req = urllib.request.Request(_WS_BASE + path, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, str(e)

def descargar_stock_api(token, idbodega):
    """
    Descarga lista de productos con stock en una bodega via API EstadisticasStock/Lista.
    Devuelve lista de dicts: {codigoTecnico, descripcion, disp, fisico, costo}.
    """
    body = {
        "IdBodega": idbodega, "IdMarca": 0, "IdHiperFamilia": 0,
        "IdFamilia": 0, "IdSubFamilia": 0,
        "SoloConStock": True, "SoloStockCritico": False,
    }
    d, err = _api_post(f"/productos/EstadisticasStock/Lista/{token}", body, timeout=120)
    if err:
        log(f"    [API ERROR] {err}")
        return []
    if not d or not d.get("resultado_operacion"):
        msg = d.get("resultado_error", "") if d else ""
        # Si EstadisticasStock falla (permiso denegado), intentar ConsultaStock por bodega
        if "permiso" in msg.lower() or "229" in msg or "execute" in msg.lower():
            log(f"    [EstadisticasStock] sin permiso — intentando lista_stock_disponible...")
            d2, err2 = _api_get(f"/productos/lista_stock_disponible/{token}/{idbodega}")
            if err2 or not d2 or not d2.get("resultado_operacion"):
                log(f"    [API] sin datos para bodega {idbodega}")
                return []
            d = d2
        else:
            log(f"    [API] resultado_operacion=False: {msg[:100]}")
            return []

    res = d.get("resultado")
    if isinstance(res, str):
        try:
            res = json.loads(res)
        except Exception:
            return []
    if not isinstance(res, list):
        return []

    resultado = []
    for item in res:
        disp   = float(item.get("St_Disponible") or 0)
        fisico = float(item.get("St_Fisico") or 0)
        if fisico == 0 and disp == 0:
            continue
        resultado.append({
            "codigoTecnico": str(item.get("Codigo_Tecnico") or item.get("CodigoTecnico") or "").strip(),
            "descripcion":   str(item.get("Descripcion") or "").strip(),
            "disp":          disp,
            "fisico":        fisico,
            "costo":         round(float(item.get("Costo_Promedio") or item.get("CostoPromedio") or 0)),
        })
    return resultado


# ─────────────────────────────────────────────────────────────────────────────
# PASO 2b — Stock fallback via Reporte_Bodegas_Detalle.asp (WebForms)
# ─────────────────────────────────────────────────────────────────────────────
def _url_reporte_bodega(base, idbodega, simbolo):
    """Construye la URL de Reporte_Bodegas_Detalle.asp (mismo patrón que descargar_erp.py)."""
    nombre_enc = urllib.parse.quote(simbolo)
    return (
        base + "/Reporte_Bodegas_Detalle.asp"
        f"?Bodega={nombre_enc}"
        "&Clasificacion=Por%20Marca,%20HiperFamilia,%20Familia,%20SubFamilia"
        "&Filtro=Todos%20los%20Productos"
        f"&IdBodega={idbodega}"
        "&IdClasificacion=3&IdFiltro=1"
        "&IdH=0&IdF=0&IdS=0"
        "&HiperFamilia=Todas%20las%20Hiper&Familia=Todas%20Las%20Fam"
        "&SubFamilia=Todas%20las%20Sub&IdMarca=0&Marca=Todas%20las%20marcas"
        "&EsFecha=1&Fecha=&IdTemp=&Temp="
    )


def _extraer_tabla_html(html):
    """
    Extrae la tabla de datos de mayor relevancia del HTML con regex.
    Devuelve (headers_list, data_rows_list) o ([], []).
    Busca la tabla cuya fila de cabecera contenga palabras clave de stock.
    """
    # Headers reales: Bodega|Marca|HiperFamilia|Familia|SubFamilia|Codigo_Tecnico|Descripcion|Serie|Disp|Cont|Bod|Ubicacion|Costo Promedio|...
    STOCK_KWS = ("cod", "codig", "desc", "disp", "fisic", "stock", "exist", "saldo", "costo", "cprom", "marc", "bod", "cont")

    # Extraer todas las tablas del HTML
    tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL | re.IGNORECASE)

    def celdas(row_html):
        cells = re.findall(r'<(?:td|th)[^>]*>(.*?)</(?:td|th)>', row_html, re.DOTALL | re.IGNORECASE)
        return [re.sub(r'<[^>]+>', '', c).replace('&nbsp;', ' ').replace('&amp;', '&').strip()
                for c in cells]

    best = (0, [], [])
    for tbl in tables:
        filas_raw = re.findall(r'<tr[^>]*>(.*?)</tr>', tbl, re.DOTALL | re.IGNORECASE)
        parsed = [celdas(f) for f in filas_raw]
        parsed = [r for r in parsed if any(c for c in r)]  # quitar filas vacías

        for i, fila in enumerate(parsed):
            texto = " ".join(fila).lower()
            score = sum(1 for kw in STOCK_KWS if kw in texto)
            if score < 2:
                continue
            datos = [r for r in parsed[i + 1:] if len(r) >= 2 and any(c for c in r)]
            if len(datos) < 2:
                continue
            if score > best[0]:
                best = (score, fila, datos)
            break

    return best[1], best[2]


def _limpiar_num(v):
    """Convierte string numérico (formato CLP con puntos de miles) a float."""
    if v is None:
        return 0.0
    s = str(v).replace(" ", "").strip()
    # Eliminar símbolos de moneda
    s = re.sub(r'[$€]', '', s)
    # Formato CLP: 1.234.567 (puntos como miles, sin decimales) o 1.234,56
    if re.match(r'^-?[\d.]+,\d+$', s):
        # Coma como decimal, punto como miles
        s = s.replace(".", "").replace(",", ".")
    elif re.match(r'^-?[\d.]+$', s) and s.count(".") > 1:
        # Múltiples puntos = separadores de miles
        s = s.replace(".", "")
    elif re.match(r'^-?[\d,]+$', s):
        # Comas como separadores de miles
        s = s.replace(",", "")
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def _idx_col(headers, *keywords):
    """Índice de la columna cuyo nombre incluye alguno de los keywords (case-insensitive).
    Prefiere coincidencia exacta sobre substring para evitar falsos positivos
    (ej: "bod" matchea "Bodega" antes que "Bod" si no se verifica exactitud)."""
    hl = [h.lower().replace(" ", "").replace("_", "").replace(".", "") for h in headers]
    for kw in keywords:
        kw_l = kw.lower().replace(" ", "").replace("_", "")
        # Primero: coincidencia exacta
        for i, h in enumerate(hl):
            if h == kw_l:
                return i
    for kw in keywords:
        kw_l = kw.lower().replace(" ", "").replace("_", "")
        # Segundo: substring (excluyendo columna "bodega" cuando se busca "bod")
        for i, h in enumerate(hl):
            if kw_l in h and not (kw_l == "bod" and h == "bodega"):
                return i
    return None


def descargar_stock_bodega(opener, base, idbodega, simbolo, nombre):
    """
    Descarga stock de una bodega vía Reporte_Bodegas_Detalle.asp (requiere sesión).
    Devuelve lista de dicts: {codigoTecnico, descripcion, disp, fisico, costo}.
    """
    url  = _url_reporte_bodega(base, idbodega, simbolo)
    html, err = _http_get(opener, url, timeout=60)
    if html is None:
        log(f"    [ERROR GET] {simbolo} ({idbodega}): {err}")
        return []

    headers, rows = _extraer_tabla_html(html)
    if not headers:
        # Log primeras líneas del HTML para diagnóstico
        preview = html.strip()[:300].replace("\n", " ")
        log(f"    [WARN] {simbolo}: tabla no encontrada. HTML preview: {preview[:150]}")
        return []

    # Headers reales del Reporte_Bodegas_Detalle.asp:
    # Bodega|Marca|HiperFamilia|Familia|SubFamilia|Codigo_Tecnico|Descripcion|Serie|Disp|Cont|Bod|...
    i_cod  = _idx_col(headers, "codigo_tecnico", "codigotecnico", "cod", "codigo")
    i_desc = _idx_col(headers, "descripcion", "desc", "nombre", "product")
    i_disp = _idx_col(headers, "disp", "disponible")
    i_fis  = _idx_col(headers, "bod", "fisic", "fisico", "stock", "exist", "saldo")
    i_cos  = _idx_col(headers, "costo promedio", "costo_promedio", "cprom", "promedio", "cost")

    if i_cod is None:
        log(f"    [WARN] {simbolo}: columna COD no identificada. Headers: {headers[:8]}")
        return []

    resultado = []
    for row in rows:
        def cell(idx):
            return row[idx].strip() if idx is not None and idx < len(row) else ""

        cod = cell(i_cod)
        # Filtrar filas de totales/separadores: el código debe ser alfanumérico >=3 chars
        if not re.match(r'^[A-Za-z0-9]{3,}', cod):
            continue

        disp   = _limpiar_num(cell(i_disp))
        fisico = _limpiar_num(cell(i_fis))

        # Excluir productos sin stock físico (igual que SQL WHERE ST_FISICO <> 0)
        # Nota: mantenemos negativos (bodegas como CSV/GSV pueden tenerlos por diseño ERP)
        if fisico == 0:
            continue

        resultado.append({
            "codigoTecnico": cod,
            "descripcion":   cell(i_desc),
            "disp":          disp,
            "fisico":        fisico,
            "costo":         round(_limpiar_num(cell(i_cos))),
        })

    return resultado


# ─────────────────────────────────────────────────────────────────────────────
# PASO 3 — GRT via VisorRS.aspx (WebForms POST) para diasAntiguedad
#
# Parámetros confirmados 13-08-2026 por inspección del HTML del form:
#   RV$ctl08$ctl06$ddValue  = Sucursal Destino (6=San Vicente)
#   RV$ctl08$ctl08$txtValue = Fecha Desde (DD/MM/YYYY)
#   RV$ctl08$ctl10$txtValue = Fecha Hasta (DD/MM/YYYY)
#   RV$ctl08$ctl16$...      = Detalle (rbTrue/rbFalse)
#   RV$ctl08$ctl20$ddValue  = Bodega Destino (ver SSRS_BODEGA_ID)
#   RV$ctl08$ctl26$ddValue  = Tipo Documento (21=GRT)
#
# Mapeo Bodega Destino (SSRS value → nombre) confirmado 13-08-2026:
#   37=Sala San Vicente, 38=Patio San Vicente, 43=Transito San Vicente
#   85=Distribucion San Vicente, 91=Exhibicion San Vicente
# ─────────────────────────────────────────────────────────────────────────────

# Mapeo IdBodega → valor SSRS del dropdown Bodega Destino
SSRS_BODEGA_ID = {
    39: 37,   # Sala San Vicente (SSV)
    40: 38,   # Patio San Vicente (PSV)
    41: 39,   # Gestion San Vicente (GSV)
    45: 43,   # Transito San Vicente (TSV)
    88: 85,   # Distribucion San Vicente (DSV)
    95: 91,   # Exhibicion San Vicente (ESV)
}

_VISOR_URL_TMPL = (
    "https://erp.justtime.cl/visor/VisorRS.aspx"
    "?xToken={token}&xInforme={informe}&xTituloInforme=Productos+enviados+a+Sucursal"
)


def _visor_get_form(opener, token):
    """GET VisorRS.aspx → devuelve (html, viewstate, vsg, evval) o (None,…) si falla."""
    informe = urllib.parse.quote("RS_Existencias/productos_traslado_productos")
    url = _VISOR_URL_TMPL.format(token=token, informe=informe)
    html, err = _http_get(opener, url, timeout=40)
    if html is None:
        return None, "", "", ""
    viewstate = _extract_input(html, "__VIEWSTATE")
    vsg       = _extract_input(html, "__VIEWSTATEGENERATOR")
    evval     = _extract_input(html, "__EVENTVALIDATION")
    return html, viewstate, vsg, evval


def _visor_post_report(opener, token, viewstate, vsg, evval,
                        desde_str, hasta_str, bodega_ssrs, tipo_doc="21"):
    """
    POST "Ver informe" en VisorRS.aspx.
    bodega_ssrs: valor del dropdown Bodega Destino (ej. 37 para SSV).
    tipo_doc: 21=GRT, 1=Todos.
    Retorna (html_respuesta, error_str).
    """
    informe = urllib.parse.quote("RS_Existencias/productos_traslado_productos")
    url = _VISOR_URL_TMPL.format(token=token, informe=informe)
    data = {
        "__EVENTTARGET": "", "__EVENTARGUMENT": "",
        "__VIEWSTATE": viewstate, "__VIEWSTATEGENERATOR": vsg,
        "__EVENTVALIDATION": evval,
        "RV$ctl08$ctl04$ddValue": "1",             # Sucursal Origen = Todas
        "RV$ctl08$ctl06$ddValue": "6",             # Sucursal Destino = San Vicente
        "RV$ctl08$ctl08$txtValue": desde_str,       # Fecha Desde DD/MM/YYYY
        "RV$ctl08$ctl10$txtValue": hasta_str,       # Fecha Hasta DD/MM/YYYY
        "RV$ctl08$ctl12$ddValue": "1",             # Marca = Todas
        "RV$ctl08$ctl14$txtValue": "",
        "RV$ctl08$ctl16$RV_ctl08_ctl16": "rbTrue", # Detalle = True (por documento)
        "RV$ctl08$ctl18$ddValue": "1",             # Bodega Origen = Todas
        "RV$ctl08$ctl20$ddValue": str(bodega_ssrs),# Bodega Destino
        "RV$ctl08$ctl22$txtValue": "",
        "RV$ctl08$ctl24$ddValue": "1",             # Temporada = Todas
        "RV$ctl08$ctl26$ddValue": str(tipo_doc),   # Tipo Documento (21=GRT)
        "RV$ctl03$ctl00": "", "RV$ctl03$ctl01": "",
        "RV$isReportViewerInVs": "", "RV$ctl14": "", "RV$ctl15": "",
        "RV$AsyncWait$HiddenCancelField": "False",
        "RV$ToggleParam$store": "", "RV$ToggleParam$collapse": "false",
        "RV$ctl12$ClientClickedId": "", "RV$ctl11$store": "",
        "RV$ctl11$collapse": "false",
        "RV$ctl13$VisibilityState$ctl00": "None",
        "RV$ctl13$ScrollPosition": "",
        "RV$ctl13$ReportControl$ctl02": "", "RV$ctl13$ReportControl$ctl03": "",
        "RV$ctl13$ReportControl$ctl04": "100",
        "RV$ctl08$ctl00": "Ver informe",
    }
    return _http_post(opener, url, data, timeout=180)


def _parsear_tabla_grt(html):
    """
    Extrae filas de datos de la tabla de GRT del HTML del ReportViewer.
    Retorna lista de dicts: {codigoTecnico, bodegaOrigen, bodegaDestino, numeroDoc,
                             fechaEmision_str, cant}.
    """
    HDRS_KW = ("codigo", "descrip", "fecha", "emis")
    tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL | re.IGNORECASE)

    def celdas(row_html):
        cells = re.findall(r'<(?:td|th)[^>]*>(.*?)</(?:td|th)>', row_html, re.DOTALL | re.IGNORECASE)
        return [re.sub(r'<[^>]+>', '', c)
                .replace('&nbsp;', ' ').replace('&amp;', '&')
                .replace('&#243;', 'o').replace('&#233;', 'e')
                .replace('&#237;', 'i').strip()
                for c in cells]

    for tbl in tables:
        filas_raw = re.findall(r'<tr[^>]*>(.*?)</tr>', tbl, re.DOTALL | re.IGNORECASE)
        parsed = [celdas(f) for f in filas_raw]
        parsed = [r for r in parsed if any(c.strip() for c in r)]
        for i, fila in enumerate(parsed):
            txt = ' '.join(fila).lower()
            if sum(1 for kw in HDRS_KW if kw in txt) >= 2:
                headers = fila
                hl = [h.lower().replace(' ', '').replace('_', '') for h in headers]
                i_cod   = next((j for j, h in enumerate(hl) if 'codig' in h), None)
                i_bod_o = next((j for j, h in enumerate(hl) if 'origen' in h), None)
                i_bod_d = next((j for j, h in enumerate(hl) if 'destino' in h), None)
                i_num   = next((j for j, h in enumerate(hl) if 'numero' in h or 'numdoc' in h), None)
                i_fecha = next((j for j, h in enumerate(hl) if 'fecha' in h or 'emis' in h), None)
                i_cant  = next((j for j, h in enumerate(hl) if 'cant' in h), None)

                if i_cod is None or i_fecha is None:
                    continue

                filas_datos = []
                for row in parsed[i + 1:]:
                    def cell(idx):
                        return row[idx].strip() if idx is not None and idx < len(row) else ''
                    cod = cell(i_cod)
                    if not re.match(r'^[A-Za-z0-9]{3,}', cod):
                        continue  # saltar totales/separadores
                    filas_datos.append({
                        'codigoTecnico':  cod,
                        'bodegaOrigen':   cell(i_bod_o),
                        'bodegaDestino':  cell(i_bod_d),
                        'numeroDoc':      cell(i_num),
                        'fechaEmision_str': cell(i_fecha),
                        'cant':           _limpiar_num(cell(i_cant)),
                    })
                return filas_datos
    return []


def descargar_grt_visor(opener, token, idbodega, fecha_ini, fecha_fin):
    """
    Descarga movimientos GRT para una bodega vía VisorRS.aspx WebForms POST.
    fecha_ini/fecha_fin: formato YYYY-MM-DD (se convierten a DD/MM/YYYY para el form).
    Retorna lista de dicts con codigoTecnico + fechaEmision_str, o [] si falla.
    """
    desde_str = datetime.datetime.strptime(fecha_ini, "%Y-%m-%d").strftime("%d/%m/%Y")
    hasta_str  = datetime.datetime.strptime(fecha_fin, "%Y-%m-%d").strftime("%d/%m/%Y") \
                 if "-" in fecha_fin else fecha_fin

    bodega_ssrs = SSRS_BODEGA_ID.get(idbodega, 1)

    # GET form (obtener __VIEWSTATE fresco)
    _html0, viewstate, vsg, evval = _visor_get_form(opener, token)
    if not viewstate:
        log(f"    [GRT] No se pudo obtener __VIEWSTATE")
        return []

    # POST tipo=21 (GRT específico)
    html2, err = _visor_post_report(opener, token, viewstate, vsg, evval,
                                     desde_str, hasta_str, bodega_ssrs, tipo_doc="21")
    if html2 is None:
        log(f"    [GRT] POST fallido: {err}")
        return []

    filas = _parsear_tabla_grt(html2)
    if filas:
        log(f"    [GRT OK] tipo=21 bodega_ssrs={bodega_ssrs} → {len(filas)} filas")
        return filas

    # Fallback: tipo=Todos (puede incluir otros tipos pero al menos hay datos)
    _html0b, viewstate, vsg, evval = _visor_get_form(opener, token)
    if viewstate:
        html3, err3 = _visor_post_report(opener, token, viewstate, vsg, evval,
                                          desde_str, hasta_str, bodega_ssrs, tipo_doc="1")
        if html3:
            filas = _parsear_tabla_grt(html3)
            if filas:
                log(f"    [GRT OK fallback Todos] bodega_ssrs={bodega_ssrs} → {len(filas)} filas")
    return filas


def _parsear_fecha(s):
    """Parsea fecha en formatos DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY."""
    if not s:
        return None
    s = s.strip()[:19]  # truncar a 19 chars para evitar microsegundos
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.datetime.strptime(s[:len(fmt)], fmt).date()
        except ValueError:
            pass
    return None


def _csv_find_col(filas, *keywords):
    """Nombre de columna CSV que contiene alguno de los keywords."""
    if not filas:
        return None
    cols = list(filas[0].keys())
    cols_lower = [c.lower().replace(" ", "").replace("_", "") for c in cols]
    for kw in keywords:
        kw_l = kw.lower().replace(" ", "").replace("_", "")
        for orig, low in zip(cols, cols_lower):
            if kw_l in low:
                return orig
    return None


def extraer_fechas_grt(filas_csv):
    """
    Desde las filas CSV del informe GRT, extrae {codigoTecnico: fecha_date_mas_reciente}.
    diasAntiguedad = (hoy - max(fecha_emision)) por código.
    """
    if not filas_csv:
        return {}

    c_cod   = _csv_find_col(filas_csv, "codigoTecnico", "codigo", "cod")
    c_fecha = _csv_find_col(filas_csv, "fechaEmision", "emision", "fecha", "date", "emis")

    if not c_cod:
        log(f"    [GRT parse] Columna código no encontrada. Columnas: {list(filas_csv[0].keys())[:8]}")
        return {}

    por_cod = {}  # codigoTecnico -> max(fecha)
    for fila in filas_csv:
        cod = str(fila.get(c_cod, "") or "").strip()
        if not cod or not re.match(r'^[A-Za-z0-9]{3,}', cod):
            continue
        fecha_str = str(fila.get(c_fecha, "") or "").strip() if c_fecha else ""
        fecha     = _parsear_fecha(fecha_str)
        if fecha:
            if cod not in por_cod or fecha > por_cod[cod]:
                por_cod[cod] = fecha

    return por_cod


# ─────────────────────────────────────────────────────────────────────────────
# PASO 4 — Combinar stock + fechas GRT
# ─────────────────────────────────────────────────────────────────────────────
def combinar_registros(stock_items, grt_fechas, simbolo, nombre, hoy):
    """
    Combina items de stock con fechas GRT. Un registro por producto.
    diasAntiguedad = (hoy - max_fecha_grt).days. None si no hay GRT.

    Campos compatibles con bodegas_gestion.json (mismo esquema).
    Campos sin fuente disponible (hiperfamilia, familia, subfamilia, marca,
    folio, usuario, estacion, fechaRegistroSistema) quedan en "".
    """
    registros = []
    for item in stock_items:
        cod    = item["codigoTecnico"]
        fisico = item.get("fisico", 0.0)

        fecha_grt = grt_fechas.get(cod)
        if fecha_grt:
            dias          = (hoy - fecha_grt).days
            fecha_reg_str = fecha_grt.strftime("%d/%m/%Y")
            fecha_iso_str = fecha_grt.isoformat()
        else:
            dias          = None
            fecha_reg_str = ""
            fecha_iso_str = ""

        registros.append({
            "bodega":               simbolo,
            "bodegaNombre":         nombre,
            "tipoDoc":              "GRT",
            "tipoDocNombre":        DOC_NOMBRES["GRT"],
            "folio":                "",       # no disponible sin SQL
            "codigoTecnico":        cod,
            "descripcion":          item.get("descripcion", ""),
            "disp":                 item.get("disp", 0.0),
            "fisico":               fisico,
            "cantidad":             fisico,   # aproximación: sin SQL no hay cantidad_doc
            "costo":                item.get("costo", 0),
            "fechaRegistro":        fecha_reg_str,
            "fechaRegistroIso":     fecha_iso_str,
            "diasAntiguedad":       dias,
            "observacion":          "",
            "usuario":              "",
            "estacionPc":           "",
            "fechaRegistroSistema": "",
            "hiperfamilia":         "",       # requiere SQL join P_HIPERFAMILIAS
            "familia":              "",       # requiere SQL join P_FAMILIAS
            "subfamilia":           "",       # requiere SQL join P_SUBFAMILIAS
            "marca":                "",       # requiere SQL join P_MARCAS
        })

    return registros


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    hoy       = datetime.date.today()
    fecha_fin = hoy.isoformat()

    log("=" * 60)
    log("generar_bodegas_sv_ssrs.py — Bodegas San Vicente (sin SQL)")
    log(f"Fecha hoy : {hoy}")
    log(f"Periodo GRT: {FECHA_INI} -> {fecha_fin}")
    log("=" * 60)

    # ── Paso 1/4: Credenciales ─────────────────────────────────────────────
    log("\nPaso 1/4: leyendo credenciales...")
    try:
        creds = leer_credenciales()
    except FileNotFoundError as e:
        log(f"[ERROR FATAL] {e}")
        sys.exit(1)

    log(f"  Archivo : {creds['_path']}")
    log(f"  BASE    : {creds['base']}")
    log(f"  BLAZOR  : {creds['blazor']}")
    log(f"  USER    : {creds['user']}")
    log(f"  XTOKEN  : {creds['xtoken'][:8]}..." if creds['xtoken']    else "  XTOKEN  : (vacio)")
    log(f"  TOKEN_R : {creds['token_rec'][:8]}..." if creds['token_rec'] else "  TOKEN_R : (vacio)")

    opener = _new_opener()

    # ── Paso 2/4: Stock por bodega via Reporte_Bodegas_Detalle.asp (WebForms) ─
    log(f"\nPaso 2/4: obteniendo stock actual via WebForms ({len(BODEGAS_SV)} bodegas SV)...")
    log("  Haciendo login en el ERP...")
    ok_login = login(opener, creds["base"], creds["user"], creds["clave"])
    if not ok_login:
        log("  [WARN] Login fallido — el reporte puede requerir autenticacion; se intentara de igual modo")

    stock_por_bodega = {}
    for idbodega, simbolo, nombre, _idsuc in BODEGAS_SV:
        log(f"  [{simbolo}] {nombre} (idbodega={idbodega})...")
        items = descargar_stock_bodega(opener, creds["base"], idbodega, simbolo, nombre)
        stock_por_bodega[idbodega] = items
        log(f"    -> {len(items)} productos con stock fisico != 0")

    total_stock = sum(len(v) for v in stock_por_bodega.values())
    log(f"\n  Total productos con stock (todas bodegas SV): {total_stock}")

    # ── Paso 3/4: GRT via VisorRS.aspx ────────────────────────────────────
    # NOTA 13-08-2026: el reporte RS_Existencias/productos_traslado_productos está
    # scoped al usuario agonzalez (El Manzano). Los filtros de Sucursal/Bodega Destino=SV
    # devuelven 0 filas — el reporte muestra traspasos DESDE El Manzano, no hacia SV.
    # diasAntiguedad quedará null para todas las bodegas SV hasta contar con:
    #   a) credenciales de usuario San Vicente, o
    #   b) acceso SQL (server sql.justtime.cl,1493 con permisos EXECUTE).
    TOKEN_ACTIVO = "71b7a611-aecf-45f6-bacd-c8df1c2fc287"  # inventario.sv 13-08-2026
    log(f"\nPaso 3/4: descargando GRT via VisorRS.aspx ({len(BODEGAS_SV)} bodegas)...")
    log(f"  Token activo: {TOKEN_ACTIVO[:8]}...")
    log("  AVISO: reporte scoped a El Manzano — diasAntiguedad sera null para SV")

    grt_por_bodega = {}
    for idbodega, simbolo, nombre, _idsuc in BODEGAS_SV:
        log(f"  [{simbolo}] {nombre}...")
        filas = descargar_grt_visor(opener, TOKEN_ACTIVO, idbodega, FECHA_INI, fecha_fin)
        if filas:
            # filas = [{codigoTecnico, fechaEmision_str, ...}] del parser HTML
            por_cod = {}
            for f in filas:
                cod   = f.get("codigoTecnico", "")
                fecha = _parsear_fecha(f.get("fechaEmision_str", ""))
                if cod and fecha:
                    if cod not in por_cod or fecha > por_cod[cod]:
                        por_cod[cod] = fecha
            fechas = por_cod
            log(f"    -> {len(fechas)} codigos con fecha GRT (de {len(filas)} filas)")
        else:
            log(f"    -> Sin datos GRT — diasAntiguedad quedara null")
            fechas = {}
        grt_por_bodega[idbodega] = fechas

    total_con_grt = sum(len(v) for v in grt_por_bodega.values())
    log(f"\n  Total codigos con fecha GRT (todas bodegas): {total_con_grt}")

    # ── Paso 4/4: Combinar y guardar ───────────────────────────────────────
    log("\nPaso 4/4: combinando stock + GRT y generando JSON...")
    todos_registros = []
    resumen         = []

    for idbodega, simbolo, nombre, _idsuc in BODEGAS_SV:
        stock_items = stock_por_bodega.get(idbodega, [])
        grt_fechas  = grt_por_bodega.get(idbodega, {})
        registros   = combinar_registros(stock_items, grt_fechas, simbolo, nombre, hoy)
        todos_registros.extend(registros)
        resumen.append((simbolo, nombre, len(registros)))
        log(f"  [{simbolo}] {nombre}: {len(registros)} registros")

    # Ordenar por diasAntiguedad descendente (mayor antigüedad primero),
    # None al final (mismo criterio que bodegas_gestion.json).
    todos_registros.sort(
        key=lambda r: r.get("diasAntiguedad") if r.get("diasAntiguedad") is not None else -1,
        reverse=True,
    )

    data = {
        "generado":         hoy.isoformat(),
        "fuente":           "VisorRS.aspx (GRT) + Reporte_Bodegas_Detalle.asp (stock) — sin SQL",
        "nota":             (
            "Campos sin fuente disponible sin SQL: folio, usuario, estacionPc, "
            "fechaRegistroSistema, hiperfamilia, familia, subfamilia, marca. "
            "Campo cantidad = ST_FISICO (aproximacion). diasAntiguedad null "
            "si el informe GRT no estuvo disponible via VisorRS.aspx."
        ),
        "idSucursal":       "05",
        "periodoGrtDesde":  FECHA_INI,
        "periodoGrtHasta":  fecha_fin,
        "bodegasIncluidas": [
            {"id": b[0], "simbolo": b[1], "nombre": b[2], "idsucursal": b[3]}
            for b in BODEGAS_SV
        ],
        "total":     len(todos_registros),
        "registros": todos_registros,
    }

    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── Resumen final ──────────────────────────────────────────────────────
    log("")
    log("=== RESUMEN ===")
    for sim, nom, n in resumen:
        log(f"  {sim:5s}  {nom:32s}  {n:4d} registros")
    log(f"  TOTAL : {len(todos_registros)} registros")

    if todos_registros:
        dias_vals = [r["diasAntiguedad"] for r in todos_registros
                     if r.get("diasAntiguedad") is not None]
        if dias_vals:
            log(f"  diasAntiguedad: min={min(dias_vals)}, max={max(dias_vals)}")
            con_grt = len(dias_vals)
            sin_grt = len(todos_registros) - con_grt
            log(f"  Con fecha GRT: {con_grt}  Sin fecha GRT (null): {sin_grt}")
        else:
            log("  diasAntiguedad: todos null — informe GRT no disponible via VisorRS.aspx")
            log("  (Solución: ejecutar descargar_grt_sv.py con SQL directo)")

        log("\n  Primeras 3 entradas:")
        for i, r in enumerate(todos_registros[:3]):
            log(
                f"  [{i+1}] cod={r['codigoTecnico']}  bod={r['bodega']}"
                f"  disp={r['disp']}  fisico={r['fisico']}"
                f"  dias={r['diasAntiguedad']}"
            )

    log(f"\n[OK] {OUT_JSON}")


if __name__ == "__main__":
    main()
