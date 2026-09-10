# -*- coding: utf-8 -*-
"""
descargar_consumo_interno.py — v1.0  2026-09-11

Descarga TODOS los eventos de "Guia de Consumo" (IDDOCUMENTO=218, simbolo ERP
GEI) — productos que la tienda consume para si misma (empleados, insumos de
uso interno: guantes, film, cinta de embalaje, etc.), NO ventas a clientes.

Verificado contra SQL en vivo (10/11-09-2026): 13.143 registros historicos
(2022-08-26 a hoy), CANTIDAD siempre positiva (magnitud consumida, no hay
que invertir signo). Confirmado por M_DOCUMENTOS (IDDOCUMENTO=218):
TIPOOPERACION='I', ESTRANSITORIO=0, ESDESPACHO=0, AFECTA_CAMBIOBODEGA=1,
TIPOSTOCK='St_Contable' — coincide con flujo-stock-justime.html.

IMPORTANTE — por que se agrupa por bodega y no por el IDSUCURSAL del
documento: se verifico que D.IDSUCURSAL (el que trae el propio detalle de
consumo) NO es confiable para clasificar la sucursal — la MISMA bodega
fisica (ej. IDBODEGA=39 "Sala San Vicente") aparece grabada bajo
IDSUCURSAL='05' (correcto) pero tambien bajo '01'/'04'/'06' (incorrecto),
probablemente porque estas guias se registran de forma centralizada. En
cambio P_BODEGAS.IDSUCURSAL (la sucursal PROPIA de la bodega en la tabla
maestra) es estable y correcta por diseno — confirmado por el usuario:
"el consumo se hace por id bodega segun la tienda". Por eso el consumo se
agrupa por la sucursal de P_BODEGAS, nunca por la del documento.

(D.IDSUCURSAL SI se sigue usando, por separado, como parte de la clave de
join hacia observacion/encabezado — ese uso es tecnicamente correcto porque
identifica el registro exacto de ese documento, no la sucursal de negocio;
mismo criterio que el fix de cruce de sucursal del 10-09-2026.)

SOLO LECTURA de SQL Server. Output:
  E:\\BODEGAS GESTION\\data\\consumo-interno.json

Anti-retroceso: aborta si nuevo total < 50% del anterior.
"""
import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from descargar_bodegas_sql import conectar  # reusa credenciales/conexion ya probadas

BASE_DIR = Path(__file__).parent.parent
OUT_JSON = BASE_DIR / 'data' / 'consumo-interno.json'

IDDOCUMENTO_CONSUMO = 218  # GEI 218 — "Guia de Consumo" (verificado SQL 11-09-2026)

NOMBRES_SUCURSAL = {
    '01': 'Casa Matriz / Otras',
    '02': 'Isabel Riquelme',
    '04': 'El Manzano',
    '05': 'San Vicente',
    '06': 'Las Cabras',
    '08': 'Centro de Distribución',
    '09': 'Ventas Empresas',
    '11': 'Litueche',
}

SQL = """
SELECT
    D.IDBODEGA,
    PB.SIMBOLO_BODEGA,
    PB.BODEGA,
    PB.IDSUCURSAL AS IDSUCURSAL_BODEGA,
    D.CODIGO_TECNICO,
    B.DESCRIPCION,
    CAST(ISNULL(D.CANTIDAD, 0) AS DECIMAL(18,2)) AS CANTIDAD,
    CAST(ISNULL(B.COSTO_PROMEDIO, 0) AS DECIMAL(18,2)) AS COSTO_PROMEDIO,
    D.NUMERO,
    D.FECHA_EMISION,
    D.IDDOCUMENTO,
    D.IDNUMERO,
    D.IDSUCURSAL,
    ISNULL(G.OBSERVACION_IMPRESA, '') AS OBSERVACION,
    ISNULL(CONVERT(NVARCHAR(20), ENC.FECHA_REGISTRO, 120), '') AS FECHA_REGISTRO_SISTEMA,
    ISNULL(ENC.IDRESPONZABLE, ISNULL(ENC.AUTORIZADO_FIRMA, ISNULL(ENC.IDVENDEDOR, ''))) AS USUARIO,
    ISNULL(ENC.ESTACION, '') AS ESTACION_PC,
    ISNULL(HF.HIPERFAMILIA, '') AS HIPERFAMILIA,
    ISNULL(FA.FAMILIA, '') AS FAMILIA,
    ISNULL(MA.MARCA, '') AS MARCA
FROM Foviedo.dbo.M_DOCUMENTOS_DETALLE D
INNER JOIN Foviedo.dbo.M_PRODUCTOS B ON B.CODIGO_TECNICO = D.CODIGO_TECNICO
INNER JOIN Foviedo.dbo.P_BODEGAS PB ON PB.IDBODEGA = D.IDBODEGA
LEFT JOIN Foviedo.dbo.P_HIPERFAMILIAS HF ON HF.IDHIPERFAMILIA = B.IDHIPERFAMILIA
LEFT JOIN Foviedo.dbo.P_FAMILIAS FA
    ON FA.IDFAMILIA = B.IDFAMILIA AND FA.IDHIPERFAMILIA = B.IDHIPERFAMILIA
LEFT JOIN Foviedo.dbo.P_MARCAS MA ON MA.IDMARCA = B.IDMARCA
OUTER APPLY (
    -- Filtro por D.IDSUCURSAL (sucursal propia del DOCUMENTO), no la de la
    -- bodega — es la clave correcta para traer la observacion de ESTE
    -- documento puntual (mismo criterio que el fix 10-09-2026).
    SELECT TOP 1 G2.OBSERVACION_IMPRESA
    FROM Foviedo.dbo.M_Documentos_Encabezado_Observacion G2
    WHERE G2.IDDOCUMENTO = D.IDDOCUMENTO AND G2.IDNUMERO = D.IDNUMERO
      AND G2.IDSUCURSAL = D.IDSUCURSAL
) G
OUTER APPLY (
    SELECT TOP 1 ENC2.FECHA_REGISTRO, ENC2.IDRESPONZABLE, ENC2.AUTORIZADO_FIRMA,
                 ENC2.IDVENDEDOR, ENC2.ESTACION
    FROM Foviedo.dbo.M_DOCUMENTOS_ENCABEZADO ENC2
    WHERE ENC2.IDDOCUMENTO = D.IDDOCUMENTO AND ENC2.IDNUMERO = D.IDNUMERO
      AND ENC2.IDSUCURSAL = D.IDSUCURSAL
) ENC
WHERE D.IDDOCUMENTO = ?
ORDER BY D.FECHA_EMISION DESC
"""


def log(msg):
    print(msg, flush=True)


def anti_retroceso(nuevo_total):
    if not OUT_JSON.exists():
        return True
    try:
        ant = json.loads(OUT_JSON.read_text(encoding='utf-8'))
        ant_total = ant.get('total', 0)
    except Exception:
        return True
    if ant_total > 0 and nuevo_total < ant_total * 0.5:
        log(f'[ABORTADO] {nuevo_total} vs {ant_total} anteriores (caida >50%). '
            f'Se conserva JSON anterior.')
        return False
    return True


def main():
    log('[1/3] Conectando a SQL Server (solo lectura)...')
    conn = conectar()
    cur = conn.cursor()
    log('      Conexion OK')

    log(f'[2/3] Consultando IDDOCUMENTO={IDDOCUMENTO_CONSUMO} (Guia de Consumo, todas las bodegas)...')
    cur.execute(SQL, IDDOCUMENTO_CONSUMO)

    por_sucursal = defaultdict(list)
    total = 0
    for row in cur.fetchall():
        (idbodega, simbolo, bodega_nombre, idsuc_bodega, cod_tec, desc,
         cantidad, costo, numero, fecha_em, iddoc, idnumero, idsuc_doc,
         obs, fecha_sis, usuario, estacion, hiper, fam, marca) = row

        cantidad = float(cantidad or 0)
        costo = float(costo or 0)
        fecha_str = fecha_em.strftime('%d/%m/%Y') if fecha_em else ''
        fecha_iso = fecha_em.date().isoformat() if fecha_em and hasattr(fecha_em, 'date') else ''

        idsuc_bodega = (idsuc_bodega or '').strip() or '01'

        por_sucursal[idsuc_bodega].append({
            'bodega': (simbolo or '').strip(),
            'bodegaNombre': (bodega_nombre or '').strip(),
            'codigoTecnico': (cod_tec or '').strip(),
            'descripcion': (desc or '').strip(),
            'marca': (marca or '').strip(),
            'familia': (fam or '').strip(),
            'hiperfamilia': (hiper or '').strip(),
            'cantidad': cantidad,
            'costoUnitario': costo,
            'costoAcumulado': round(cantidad * costo, 2),
            'folio': str(numero or '').strip(),
            'fechaRegistro': fecha_str,
            'fechaRegistroIso': fecha_iso,
            'fechaRegistroSistema': (fecha_sis or '').strip(),
            'usuario': (usuario or '').strip(),
            'estacionPc': (estacion or '').strip(),
            'observacion': (obs or '').strip(),
        })
        total += 1

    cur.close()
    conn.close()
    log(f'      {total} eventos de consumo encontrados')

    if not anti_retroceso(total):
        sys.exit(1)

    sucursales_out = []
    for idsuc in sorted(por_sucursal.keys()):
        sucursales_out.append({
            'idSucursal': idsuc,
            'nombre': NOMBRES_SUCURSAL.get(idsuc, f'Sucursal {idsuc}'),
            'total': len(por_sucursal[idsuc]),
            'registros': por_sucursal[idsuc],
        })

    payload = {
        'generado': __import__('datetime').date.today().isoformat(),
        'fuente': f'M_DOCUMENTOS_DETALLE WHERE IDDOCUMENTO={IDDOCUMENTO_CONSUMO} (Guia de Consumo)',
        'total': total,
        'sucursales': sucursales_out,
    }

    log('[3/3] Generando JSON...')
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    for s in sucursales_out:
        log(f'  {s["idSucursal"]} {s["nombre"]:25s} {s["total"]:6d} eventos')
    log(f'[OK] {OUT_JSON.name}: {total} eventos totales, {len(sucursales_out)} sucursales')


if __name__ == '__main__':
    main()
