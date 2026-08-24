"""
generar_bodegas_all_api.py
Genera bodegas_gestion.json y bodegas_ir_otras.json usando la API
EstadisticasStock de wsapi.justtime.cl — SIN conexion SQL.

Fuente: EstadisticasStock/Lista/{token}/{idbodega}
Output: bodegas_gestion_api.json (misma estructura que bodegas_gestion.json)
        bodegas_ir_api.json

diasAntiguedad: null (requiere SQL o VisorRS SSRS por bodega — pendiente)
"""

import json, urllib.request, urllib.parse, configparser, datetime, sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
OUT_GESTION = BASE_DIR / "bodegas_gestion_api.json"
OUT_IR      = BASE_DIR / "bodegas_ir_api.json"

# ── Credenciales ──────────────────────────────────────────────────────────────
CAND = [
    Path(r"E:\ferreteria-oviedo\credenciales_erp.ini"),
    Path(r"E:\ferreteria-oviedo\CATALOGO PRODUCTOS\scripts\credenciales_erp.ini"),
    Path(r"E:\ferreteria-oviedo\VENTAS EL MANZANO\credenciales_erp.ini"),
]
cfg = configparser.ConfigParser()
creds = None
for p in CAND:
    if p.exists():
        cfg.read(str(p), encoding="utf-8-sig")
        if cfg.has_section("ERP"):
            creds = cfg["ERP"]
            break
if not creds:
    sys.exit("ERROR: No se encontró credenciales_erp.ini")

TOKEN = creds.get("XTOKEN", "") or creds.get("TOKEN_RECEPCION", "")
if not TOKEN:
    sys.exit("ERROR: TOKEN vacio en credenciales_erp.ini")
print(f"Token: {TOKEN[:8]}...")

# ── Definicion de bodegas por sucursal (IDS_REFERENCIA_BODEGAS_GESTION.md) ──
# Formato: (idbodega, simbolo, nombre, idsucursal)

SUCURSALES = [
    {
        "idSucursal": "04",
        "nombre": "El Manzano",
        "bodegas": [
            (28, "GEM", "Gestion El Manzano",   "04"),
            (29, "MEM", "Mermas El Manzano",     "04"),
            (55, "RCE", "Recepcion El Manzano",  "04"),
            (72, "IEM", "Ingreso El Manzano",    "04"),
            (46, "TEM", "Transito El Manzano",   "04"),
        ],
    },
    {
        "idSucursal": "05",
        "nombre": "San Vicente",
        "bodegas": [
            (41, "GSV", "Gestion San Vicente",      "05"),
            (42, "MSV", "Mermas San Vicente",        "05"),
            (56, "RSV", "Recepcion San Vicente",     "05"),
            (70, "ISV", "Ingreso San Vicente",       "05"),
            (45, "TSV", "Transito San Vicente",      "05"),
            (44, "CSV", "Calzada San Vicente",       "05"),
            (88, "DSV", "Distribucion San Vicente",  "14"),  # IDSUCURSAL real = 14
        ],
    },
    {
        "idSucursal": "06",
        "nombre": "Las Cabras",
        "bodegas": [
            (37, "GLC", "Gestion Las Cabras",   "06"),
            (38, "MLC", "Mermas Las Cabras",     "06"),
            (57, "RLC", "Recepcion Las Cabras",  "06"),
            (71, "ILC", "Ingreso Las Cabras",    "06"),
            (16, "TLC", "Transito Las Cabras",   "06"),
            (35, "CLC", "Calzada Las Cabras",    "06"),
        ],
    },
    {
        "idSucursal": "11",
        "nombre": "Litueche",
        "bodegas": [
            (63, "GLE", "Gestion Litueche",      "11"),
            (76, "MLE", "Mermas Litueche",        "11"),
            (74, "ILE", "Ingreso Litueche",       "11"),
            (59, "TLE", "Transito Litueche",      "11"),
            (78, "CLT", "Calzada Litueche",       "11"),
            (79, "DLT", "Distribucion Litueche",  "09"),  # IDSUCURSAL real = 09
        ],
    },
]

COMPARTIDAS = [
    {
        "idSucursal": "08",
        "nombre": "Compartidas",
        "bodegas": [
            (23, "CD", "Centro de Distribucion", "08"),
        ],
    },
]

# Isabel Riquelme — genera archivo separado
IR = {
    "idSucursal": "02",
    "nombre": "Isabel Riquelme",
    "bodegas": [
        (30, "GO",  "Gestion Isabel Riquelme",     "02"),
        (75, "MIR", "Mermas Isabel Riquelme",       "02"),
        (92, "RST", "Recepcion Santiago",           "02"),
        (69, "IIR", "Ingreso Isabel Riquelme",      "02"),
        ( 5, "CAL", "Calzada",                      "02"),
        (87, "DIR", "Distribucion Isabel Riquelme", "14"),  # IDSUCURSAL real = 14
    ],
}

# ── API helper ────────────────────────────────────────────────────────────────
WS_BASE = "https://wsapi.justtime.cl/api/v1"

def api_post(path, body, timeout=90):
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        WS_BASE + path, data=data,
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, str(e)

def api_get(path, timeout=30):
    req = urllib.request.Request(WS_BASE + path, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()), None
    except Exception as e:
        return None, str(e)

def descargar_stock(idbodega, simbolo):
    """Llama EstadisticasStock/Lista. Fallback: lista_stock_disponible."""
    body = {
        "IdBodega": idbodega, "IdMarca": 0, "IdHiperFamilia": 0,
        "IdFamilia": 0, "IdSubFamilia": 0,
        "SoloConStock": True, "SoloStockCritico": False,
    }
    d, err = api_post(f"/productos/EstadisticasStock/Lista/{TOKEN}", body)
    if err:
        print(f"    [API ERROR] {simbolo}: {err}")
        return []
    if not d or not d.get("resultado_operacion"):
        msg = d.get("resultado_error", "") if d else ""
        if "permiso" in msg.lower() or "229" in msg or "execute" in msg.lower():
            print(f"    [sin permiso] {simbolo} → intentando lista_stock_disponible...")
            d2, err2 = api_get(f"/productos/lista_stock_disponible/{TOKEN}/{idbodega}")
            if err2 or not d2 or not d2.get("resultado_operacion"):
                print(f"    [sin datos] {simbolo}")
                return []
            d = d2
        else:
            print(f"    [API False] {simbolo}: {msg[:80]}")
            return []

    res = d.get("resultado")
    if isinstance(res, str):
        try: res = json.loads(res)
        except: return []
    if not isinstance(res, list):
        return []

    out = []
    for item in res:
        disp   = float(item.get("St_Disponible") or 0)
        fisico = float(item.get("St_Fisico") or 0)
        if fisico == 0 and disp == 0:
            continue
        out.append({
            "codigoTecnico": str(item.get("Codigo_Tecnico") or item.get("CodigoTecnico") or "").strip(),
            "descripcion":   str(item.get("Descripcion") or "").strip(),
            "disp":          disp,
            "fisico":        fisico,
            "costo":         round(float(item.get("Costo_Promedio") or item.get("CostoPromedio") or 0)),
        })
    return out

# ── Construir registros para una bodega ───────────────────────────────────────
def registros_bodega(idbodega, simbolo, nombre):
    print(f"  {simbolo} (id={idbodega}): ", end="", flush=True)
    items = descargar_stock(idbodega, simbolo)
    print(f"{len(items)} items")
    regs = []
    for it in items:
        regs.append({
            "bodega":              simbolo,
            "bodegaNombre":        nombre,
            "tipoDoc":             "GRT",
            "tipoDocNombre":       "Guia Recepcion Traslado",
            "folio":               "",
            "codigoTecnico":       it["codigoTecnico"],
            "descripcion":         it["descripcion"],
            "disp":                it["disp"],
            "fisico":              it["fisico"],
            "cantidad":            it["fisico"],
            "costo":               it["costo"],
            "fechaRegistro":       "",
            "fechaRegistroIso":    "",
            "diasAntiguedad":      None,
            "observacion":         "",
            "usuario":             "",
            "estacionPc":          "",
            "fechaRegistroSistema": "",
            "hiperfamilia":        "",
            "familia":             "",
            "subfamilia":          "",
            "marca":               "",
        })
    return regs

# ── Procesar un grupo de sucursales ──────────────────────────────────────────
def procesar_sucursales(grupos):
    """Devuelve lista de dicts sucursal con registros."""
    resultado = []
    for grp in grupos:
        print(f"\nSucursal {grp['idSucursal']} — {grp['nombre']}")
        all_regs = []
        bodegas_inc = []
        for idbod, simb, nom, _idsuc in grp["bodegas"]:
            regs = registros_bodega(idbod, simb, nom)
            all_regs.extend(regs)
            bodegas_inc.append(simb)
        resultado.append({
            "idSucursal":      grp["idSucursal"],
            "nombre":          grp["nombre"],
            "bodegasIncluidas": bodegas_inc,
            "total":           len(all_regs),
            "registros":       all_regs,
        })
    return resultado

# ── Main ──────────────────────────────────────────────────────────────────────
hoy = datetime.date.today().isoformat()

# 1. bodegas_gestion_api.json (El Manzano, SV, Las Cabras, Litueche + Compartidas)
print("\n=== GESTION (El Manzano, SV, Las Cabras, Litueche) ===")
suc_data = procesar_sucursales(SUCURSALES)

print("\n=== COMPARTIDAS ===")
comp_data = procesar_sucursales(COMPARTIDAS)
comp_regs = [r for g in comp_data for r in g["registros"]]
comp_out  = {
    "bodegasIncluidas": [b for g in comp_data for b, *_ in [(r["bodega"],) for r in g["registros"]]],
    "total":            len(comp_regs),
    "registros":        comp_regs,
}
# simplificar bodegasIncluidas
comp_bodegas_unicas = list({r["bodega"] for r in comp_regs})
comp_out["bodegasIncluidas"] = comp_bodegas_unicas

total_gestion = sum(g["total"] for g in suc_data) + len(comp_regs)
gestion_json = {
    "generado": hoy,
    "fuente": "EstadisticasStock API wsapi.justtime.cl — sin SQL",
    "sucursales": suc_data,
    "compartidas": comp_out,
    "total": total_gestion,
}
OUT_GESTION.write_text(json.dumps(gestion_json, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nbodegas_gestion_api.json: {total_gestion} registros → {OUT_GESTION}")

# 2. bodegas_ir_api.json (Isabel Riquelme)
print("\n=== ISABEL RIQUELME ===")
ir_regs = []
ir_bodegas_inc = []
for idbod, simb, nom, _idsuc in IR["bodegas"]:
    regs = registros_bodega(idbod, simb, nom)
    ir_regs.extend(regs)
    ir_bodegas_inc.append(simb)

ir_json = {
    "generado": hoy,
    "fuente": "EstadisticasStock API wsapi.justtime.cl — sin SQL",
    "idSucursal": IR["idSucursal"],
    "nombre": IR["nombre"],
    "bodegasIncluidas": ir_bodegas_inc,
    "total": len(ir_regs),
    "registros": ir_regs,
}
OUT_IR.write_text(json.dumps(ir_json, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nbodegas_ir_api.json: {len(ir_regs)} registros → {OUT_IR}")

print("\nListo.")
