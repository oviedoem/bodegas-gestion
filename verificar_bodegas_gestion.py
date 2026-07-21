"""
verificar_bodegas_gestion.py
Verifica via SQL Server Foviedo (SOLO LECTURA) las bodegas de categoria
Gestion/Mermas/Recepcion/Ingreso/Transito para las sucursales objetivo del
proyecto BODEGAS GESTION: El Manzano(04), Isabel Riquelme(02), Las Cabras(06),
San Vicente(05), Litueche(11).

No se guessean IDs: se consulta P_BODEGAS JOIN C_SUCURSALES en vivo y se
filtra por nombre de bodega que empiece con esas 5 categorias, excluyendo
bodegas comerciales/facturacion (Sala, Patio, Calzada, Exhibicion, etc.).

Credenciales: E:\\ferreteria-oviedo\\credenciales_db.ini (solo lectura, no se
copia el valor a ningun archivo de salida).
"""
import configparser
import pathlib
import sys

import pyodbc

CRED_FILE = pathlib.Path(r"E:\ferreteria-oviedo\credenciales_db.ini")

SUCURSALES_OBJETIVO = {
    '02': 'Isabel Riquelme',
    '04': 'El Manzano',
    '05': 'San Vicente',
    '06': 'Las Cabras',
    '11': 'Litueche',
}

CATEGORIAS = ('Gestion', 'Merma', 'Recepcion', 'Ingreso', 'Transito', 'Calzada',
              'Centro de Distribucion', 'Distribucion')

# Calzada se agrega para todas las sucursales objetivo EXCEPTO El Manzano (04) —
# pedido explicito del usuario.
EXCLUIR = {
    ('04', 'Calzada'),
}

SQL = """
SELECT B.IDSUCURSAL, B.IDBODEGA, B.SIMBOLO_BODEGA, B.BODEGA
FROM Foviedo.dbo.P_BODEGAS B
WHERE B.IDSUCURSAL IN ({placeholders})
ORDER BY B.IDSUCURSAL, B.BODEGA
"""


def conectar():
    cfg = configparser.ConfigParser()
    cfg.read(str(CRED_FILE), encoding="utf-8")
    db = cfg["DB"]
    return pyodbc.connect(
        f"DRIVER={{SQL Server}};SERVER={db['server']};DATABASE={db['database']};"
        f"UID={db['user']};PWD={db['password']};TrustServerCertificate=yes;", timeout=30
    )


def main():
    if not CRED_FILE.exists():
        print(f"[ERROR] No existe {CRED_FILE}")
        sys.exit(1)

    print("Conectando a SQL Server (solo lectura)...")
    conn = conectar()
    cur = conn.cursor()

    placeholders = ",".join("?" for _ in SUCURSALES_OBJETIVO)
    cur.execute(SQL.format(placeholders=placeholders), *SUCURSALES_OBJETIVO.keys())

    por_sucursal = {s: [] for s in SUCURSALES_OBJETIVO}
    for idsuc, idbod, simbolo, nombre in cur.fetchall():
        idsuc = str(idsuc).strip()
        if idsuc in por_sucursal:
            por_sucursal[idsuc].append((idbod, str(simbolo or "").strip(), str(nombre or "").strip()))
    cur.close()
    conn.close()

    print()
    for idsuc, nombre_suc in SUCURSALES_OBJETIVO.items():
        print(f"=== {idsuc} — {nombre_suc} ===")
        bodegas = por_sucursal.get(idsuc, [])
        for cat in CATEGORIAS:
            if (idsuc, cat) in EXCLUIR:
                print(f"  [{cat:22s}] (excluida a pedido del usuario)")
                continue
            match = [b for b in bodegas if cat.lower() in b[2].lower()]
            if match:
                for idbod, simbolo, nombre in match:
                    print(f"  [{cat:22s}] IDBODEGA={idbod:>4}  {simbolo:6s}  {nombre}")
            else:
                print(f"  [{cat:22s}] (no encontrada)")
        print()


if __name__ == "__main__":
    main()
