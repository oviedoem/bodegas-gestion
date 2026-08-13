"""
descargar_stock_erp.py
Descarga stock de bodegas desde ERP via Reporte_Bodegas_Detalle.asp (sin SQL).
Uso: python descargar_stock_erp.py <SUC_CODE>
     python descargar_stock_erp.py ALL    # todas en secuencia

SUC_CODE: IR | EM | SV | LC | LT
Output:   data/bodegas_<SUC>.json
"""
import configparser
import datetime
import http.cookiejar
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR   = Path(__file__).parent.parent   # E:\ISABEL RIQUELME\
DATA_DIR   = BASE_DIR / "data"
CRED_PATHS = [
    Path(r"E:\ferreteria-oviedo\credenciales_erp.ini"),
    Path(r"E:\ferreteria-oviedo\CATALOGO PRODUCTOS\scripts\credenciales_erp.ini"),
    Path(r"E:\ferreteria-oviedo\VENTAS EL MANZANO\credenciales_erp.ini"),
]
PAUSA_ENTRE_BODEGAS = 6   # segundos entre descargas para no saturar el ERP

# ─── MAPA DE SUCURSALES ────────────────────────────────────────────────────────
# (IDBODEGA, simbolo_unico, nombre_largo, simbolo_bodega_erp)
# simbolo_unico: clave interna única (evita colisión CSV=44 vs CSV=43 en SV)
SUCURSALES = {
    "IR": {
        "idSucursal": "02",
        "nombre": "Isabel Riquelme",
        "bodegas": [
            (5,  "CAL", "Calzada",                     "CAL"),
            (6,  "SER", "Servicio Tecnico",             "SER"),
            (25, "WEB", "Retiro Web Santiago",          "WEB"),
            (30, "GO",  "Gestion Isabel Riquelme",      "GO"),
            (53, "GAR", "Garantia Santiago",            "GAR"),
            (69, "IIR", "Ingreso Isabel Riquelme",      "IIR"),
            (75, "MIR", "Mermas Isabel Riquelme",       "MIR"),
            (77, "BMC", "Marticorena Stgo",             "BMC"),
            (85, "EIR", "Exhibicion Isabel Riquelme",   "EIR"),
            (92, "RST", "Recepcion Santiago",           "RST"),
            (99, "HEL", "Herramientas Electricas",      "HEL"),
        ],
    },
    "EM": {
        "idSucursal": "04",
        "nombre": "El Manzano",
        "bodegas": [
            (28, "GEM", "Gestion El Manzano",           "GEM"),
            (29, "MEM", "Mermas El Manzano",            "MEM"),
            (46, "TEM", "Transito El Manzano",          "TEM"),
            (55, "RCE", "Recepcion El Manzano",         "RCE"),
            (72, "IEM", "Ingreso El Manzano",           "IEM"),
            (83, "EEM", "Exhibicion El Manzano",        "EEM"),
        ],
    },
    "SV": {
        "idSucursal": "05",
        "nombre": "San Vicente",
        "bodegas": [
            (41, "GSV",  "Gestion San Vicente",         "GSV"),
            (42, "MSV",  "Mermas San Vicente",          "MSV"),
            (43, "CONSV","Consumo San Vicente",         "CSV"),  # CSV=43, simbolo interno CONSV
            (44, "CSV",  "Calzada San Vicente",         "CSV"),  # CSV=44, el "real"
            (45, "TSV",  "Transito San Vicente",        "TSV"),
            (56, "RSV",  "Recepcion San Vicente",       "RSV"),
            (70, "ISV",  "Ingreso San Vicente",         "ISV"),
            (88, "DSV",  "Distribucion San Vicente",    "DSV"),
            (95, "ESV",  "Exhibicion San Vicente",      "ESV"),
        ],
    },
    "LC": {
        "idSucursal": "06",
        "nombre": "Las Cabras",
        "bodegas": [
            (16, "TLC", "Transito Las Cabras",          "TLC"),
            (35, "CLC", "Calzada Las Cabras",           "CLC"),
            (37, "GLC", "Gestion Las Cabras",           "GLC"),
            (38, "MLC", "Mermas Las Cabras",            "MLC"),
            (57, "RLC", "Recepcion Las Cabras",         "RLC"),
            (71, "ILC", "Ingreso Las Cabras",           "ILC"),
            (91, "GFL", "Garantia Las Cabras",          "GFL"),
            (96, "ELC", "Exhibicion Las Cabras",        "ELC"),
            (97, "VLC", "Volumen Las Cabras",           "VLC"),
        ],
    },
    "LT": {
        "idSucursal": "11",
        "nombre": "Litueche",
        "bodegas": [
            (59, "TLE", "Transito Litueche",            "TLE"),
            (63, "GLE", "Gestion Litueche",             "GLE"),
            (64, "ELE", "Exhibicion Litueche",          "ELE"),
            (74, "ILE", "Ingreso Litueche",             "ILE"),
            (76, "MLE", "Mermas Litueche",              "MLE"),
            (78, "CLT", "Calzada Litueche",             "CLT"),
            (79, "DLT", "Distribucion Litueche",        "DLT"),
        ],
    },
}


# ─── CREDENCIALES ─────────────────────────────────────────────────────────────
def leer_credenciales():
    cfg = configparser.ConfigParser()
    for p in CRED_PATHS:
        if p.exists():
            cfg.read(str(p), encoding="utf-8")
            if "ERP" in cfg:
                erp = cfg["ERP"]
                return {
                    "base":  erp.get("BASE",  "https://erp.justtime.cl/justweb_foviedo"),
                    "user":  erp.get("USER",  ""),
                    "clave": erp.get("CLAVE", ""),
                }
    raise FileNotFoundError("credenciales_erp.ini con [ERP] no encontrado")


# ─── HTTP ─────────────────────────────────────────────────────────────────────
def nuevo_opener():
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [
        ("User-Agent",      "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"),
        ("Accept",          "text/html,application/xhtml+xml,*/*;q=0.8"),
        ("Accept-Language", "es-CL,es;q=0.9"),
    ]
    return opener


def http_get(opener, url, timeout=60):
    try:
        with opener.open(url, timeout=timeout) as r:
            raw = r.read()
            for enc in ("utf-8", "iso-8859-1", "latin-1"):
                try:
                    return raw.decode(enc), None
                except UnicodeDecodeError:
                    pass
            return raw.decode("utf-8", errors="replace"), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, str(e)


def http_post(opener, url, data, timeout=40):
    """Devuelve (html, url_final) o (None, error_str)."""
    body = urllib.parse.urlencode(data).encode("utf-8")
    req  = urllib.request.Request(url, data=body)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace"), r.geturl()
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, str(e)


# ─── LOGIN ────────────────────────────────────────────────────────────────────
def extraer_input(html, name):
    for pat in [
        r'<input[^>]+name=["\']' + re.escape(name) + r'["\'][^>]+value=["\']([^"\']*)["\']',
        r'<input[^>]+value=["\']([^"\']*)["\'][^>]+name=["\']' + re.escape(name) + r'["\']',
    ]:
        m = re.search(pat, html, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1)
    return ""


def login(opener, base, user, clave):
    html, err = http_get(opener, base + "/", timeout=40)
    if html is None:
        print(f"  [login] GET fallido: {err}")
        return False
    if "__VIEWSTATE" not in html:
        print("  [login] Sin VIEWSTATE — asumiendo sesion activa")
        return True

    data = {
        "__EVENTTARGET":        "",
        "__EVENTARGUMENT":      "",
        "__VIEWSTATE":          extraer_input(html, "__VIEWSTATE"),
        "__VIEWSTATEGENERATOR": extraer_input(html, "__VIEWSTATEGENERATOR"),
        "__EVENTVALIDATION":    extraer_input(html, "__EVENTVALIDATION"),
        "Login1$txtUsuario":    user,
        "Login1$txtClave":      clave,
        "Login1$CmdAceptar":    "Ingresar",
    }
    html2, url2 = http_post(opener, base + "/", data)
    if html2 is None:
        print(f"  [login] POST fallido: {url2}")
        return False

    # Login fallido solo si URL dice "login/ingresar" Y el form de login volvio a aparecer
    if (re.search(r'(login|ingresar)', url2 or "", re.IGNORECASE) and
            re.search(r'(Login1\$txtUsuario|CmdAceptar)', html2, re.IGNORECASE)):
        print(f"  [login] Fallido — formulario volvio ({url2[:60]})")
        return False

    print(f"  [login] OK → {(url2 or '')[:60]}")
    return True


# ─── PARSEAR HTML DEL REPORTE_BODEGAS_DETALLE ─────────────────────────────────
STOCK_KWS = ("cod", "codig", "desc", "disp", "fisic", "stock", "exist", "saldo", "costo", "cprom", "marc", "bod", "cont")


def celdas(row_html):
    cells = re.findall(r'<(?:td|th)[^>]*>(.*?)</(?:td|th)>', row_html, re.DOTALL | re.IGNORECASE)
    return [re.sub(r'<[^>]+>', '', c).replace('&nbsp;', ' ').replace('&amp;', '&').strip() for c in cells]


def extraer_tabla(html):
    tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL | re.IGNORECASE)
    best = (0, [], [])
    for tbl in tables:
        filas_raw = re.findall(r'<tr[^>]*>(.*?)</tr>', tbl, re.DOTALL | re.IGNORECASE)
        parsed = [celdas(f) for f in filas_raw]
        parsed = [r for r in parsed if any(c for c in r)]
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


def limpiar_num(v):
    if v is None:
        return 0.0
    s = re.sub(r'[$€\s]', '', str(v))
    if re.match(r'^-?[\d.]+,\d+$', s):
        s = s.replace(".", "").replace(",", ".")
    elif re.match(r'^-?[\d.]+$', s) and s.count(".") > 1:
        s = s.replace(".", "")
    elif re.match(r'^-?[\d,]+$', s):
        s = s.replace(",", "")
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def idx_col(headers, *keywords):
    hl = [h.lower().replace(" ", "").replace("_", "").replace(".", "") for h in headers]
    for kw in keywords:
        kw_l = kw.lower().replace(" ", "").replace("_", "")
        for i, h in enumerate(hl):
            if h == kw_l:
                return i
    for kw in keywords:
        kw_l = kw.lower().replace(" ", "").replace("_", "")
        for i, h in enumerate(hl):
            if kw_l in h and not (kw_l == "bod" and h == "bodega"):
                return i
    return None


def url_reporte(base, idbodega, simbolo_erp):
    nombre_enc = urllib.parse.quote(simbolo_erp)
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


# ─── DESCARGAR UNA BODEGA ─────────────────────────────────────────────────────
def descargar_bodega(opener, base, idbodega, simbolo_unico, nombre, simbolo_erp):
    """Devuelve lista de registros con stock de la bodega. [] si falla."""
    url = url_reporte(base, idbodega, simbolo_erp)
    html, err = http_get(opener, url, timeout=90)
    if html is None:
        print(f"    [ERROR] {simbolo_unico} ({idbodega}): {err}")
        return []

    headers, rows = extraer_tabla(html)
    if not headers:
        preview = html.strip()[:200].replace("\n", " ")
        print(f"    [WARN] {simbolo_unico}: tabla no encontrada. Preview: {preview[:150]}")
        return []

    i_cod    = idx_col(headers, "codigo_tecnico", "codigotecnico", "cod", "codigo")
    i_desc   = idx_col(headers, "descripcion", "desc", "nombre", "product")
    i_disp   = idx_col(headers, "disp", "disponible")
    i_cont   = idx_col(headers, "cont", "contable")
    i_bod    = idx_col(headers, "bod", "bodega_stock", "stock_bod")
    i_costo  = idx_col(headers, "costo_promedio", "costopromedio", "cprom", "costo")
    i_marc   = idx_col(headers, "marca")
    i_hiper  = idx_col(headers, "hiperfamilia", "hiper")
    i_fam    = idx_col(headers, "familia")
    i_sub    = idx_col(headers, "subfamilia", "sub")

    def cel(row, idx):
        if idx is None or idx >= len(row):
            return ""
        return row[idx]

    registros = []
    for row in rows:
        cod  = cel(row, i_cod).strip()
        desc = cel(row, i_desc).strip()
        if not cod or not re.search(r'\d', cod):
            continue
        disp   = limpiar_num(cel(row, i_disp))
        cont   = limpiar_num(cel(row, i_cont))
        bod    = limpiar_num(cel(row, i_bod))
        fisico = cont + bod if (cont or bod) else disp
        costo  = round(limpiar_num(cel(row, i_costo)))
        if disp == 0 and fisico == 0:
            continue
        registros.append({
            "bodega":               simbolo_unico,
            "bodegaNombre":         nombre,
            "tipoDoc":              None,
            "tipoDocNombre":        None,
            "folio":                None,
            "codigoTecnico":        cod,
            "descripcion":          desc,
            "disp":                 disp,
            "fisico":               fisico,
            "cantidad":             disp,
            "costo":                costo,
            "fechaRegistro":        None,
            "fechaRegistroIso":     None,
            "diasAntiguedad":       None,
            "observacion":          None,
            "usuario":              None,
            "estacionPc":           None,
            "fechaRegistroSistema": None,
            "hiperfamilia":         cel(row, i_hiper),
            "familia":              cel(row, i_fam),
            "subfamilia":           cel(row, i_sub),
            "marca":                cel(row, i_marc),
        })

    print(f"    {simbolo_unico} ({idbodega}): {len(registros)} registros")
    return registros


# ─── DESCARGAR UNA SUCURSAL ───────────────────────────────────────────────────
def descargar_sucursal(suc_code):
    suc = SUCURSALES[suc_code]
    creds = leer_credenciales()
    print(f"\n=== {suc_code} — {suc['nombre']} (SUC {suc['idSucursal']}) ===")
    print(f"  Base URL: {creds['base']}")

    opener = nuevo_opener()
    ok = login(opener, creds["base"], creds["user"], creds["clave"])
    if not ok:
        print("  [WARN] Login dudoso — intentando descargar igual (el reporte puede funcionar)")

    todos = []
    bodegas = suc["bodegas"]
    for idx, (idbodega, simbolo_unico, nombre, simbolo_erp) in enumerate(bodegas):
        print(f"  [{idx+1}/{len(bodegas)}] Descargando {simbolo_unico} ({idbodega}) {nombre}...")
        regs = descargar_bodega(opener, creds["base"], idbodega, simbolo_unico, nombre, simbolo_erp)
        todos.extend(regs)
        if idx < len(bodegas) - 1:
            print(f"  Pausa {PAUSA_ENTRE_BODEGAS}s...")
            time.sleep(PAUSA_ENTRE_BODEGAS)

    DATA_DIR.mkdir(exist_ok=True)
    out = DATA_DIR / f"bodegas_{suc_code}.json"
    payload = {
        "generado":   datetime.date.today().isoformat(),
        "fuente":     "ERP Reporte_Bodegas_Detalle.asp",
        "sucursal":   suc_code,
        "idSucursal": suc["idSucursal"],
        "nombre":     suc["nombre"],
        "total":      len(todos),
        "registros":  todos,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  Guardado: {out} ({len(todos)} registros)")


# ─── COMBINAR TODOS EN bodegas_gestion.json ──────────────────────────────────
def combinar():
    print("\n=== Combinando en bodegas_gestion.json ===")
    sucursales_out = []
    total_global = 0
    for suc_code in ("IR", "EM", "SV", "LC", "LT"):
        f = DATA_DIR / f"bodegas_{suc_code}.json"
        if not f.exists():
            print(f"  [WARN] Falta: {f.name}")
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        sucursales_out.append({
            "idSucursal": d["idSucursal"],
            "nombre":     d["nombre"],
            "total":      d["total"],
            "registros":  d["registros"],
        })
        total_global += d["total"]
        print(f"  {suc_code}: {d['total']} registros ({d['generado']})")

    payload = {
        "generado":     datetime.date.today().isoformat(),
        "fuente":       "ERP Reporte_Bodegas_Detalle.asp",
        "nota_limpieza":"diasAntiguedad=null (ERP no provee; requiere SQL o SSRS GRT)",
        "total":        total_global,
        "compartidas":  [],
        "sucursales":   sucursales_out,
    }
    out = BASE_DIR / "bodegas_gestion.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  OK → {out} ({total_global} registros totales)")


# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python descargar_stock_erp.py <SUC_CODE>")
        print("     SUC_CODE: IR | EM | SV | LC | LT | ALL | COMBINAR")
        sys.exit(1)

    cmd = sys.argv[1].upper()
    if cmd == "ALL":
        for suc in ("IR", "EM", "SV", "LC", "LT"):
            descargar_sucursal(suc)
            print("\nPausa 10s entre sucursales...")
            time.sleep(10)
        combinar()
    elif cmd == "COMBINAR":
        combinar()
    elif cmd in SUCURSALES:
        descargar_sucursal(cmd)
    else:
        print(f"SUC_CODE desconocido: {cmd}")
        print(f"Validos: {', '.join(SUCURSALES.keys())} | ALL | COMBINAR")
        sys.exit(1)
