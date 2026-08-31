"""
Monitor inventario San Vicente — corre independiente, sin Claude.
Revisa R_STOCK_PRODUCTOS cada 5 minutos.
Objetivo: PSV(40) <= 2 productos con stock, SSV(39) <= 3 productos con stock.
Log en: E:\BODEGAS GESTION\monitor_sv.log
"""
import importlib.util, pyodbc, time, sys, urllib.request, json
from pathlib import Path
from datetime import datetime

NTFY_TOPIC = 'oviedo-sv-inventario-2908'

def ntfy(titulo, mensaje, prioridad='high'):
    try:
        data = json.dumps({'topic': NTFY_TOPIC, 'title': titulo, 'message': mensaje, 'priority': 4 if prioridad=='high' else 3}).encode()
        req = urllib.request.Request('https://ntfy.sh', data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
        log(f'[ntfy] Notificacion enviada: {titulo}')
    except Exception as e:
        log(f'[ntfy ERROR] {e}')

LOG = Path(r'E:\BODEGAS GESTION\monitor_sv.log')
INTERVALO = 1800  # 30 minutos

def log(msg):
    linea = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(linea, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(linea + '\n')

def get_conn():
    spec = importlib.util.spec_from_file_location('dif', r'E:\BODEGAS GESTION\scripts\descargar_dif_sv.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    server, database, user, password = mod.leer_credenciales()
    conn_str = 'DRIVER={SQL Server};SERVER='+server+';DATABASE='+database+';UID='+user+';PWD='+password+';TrustServerCertificate=yes;'
    return pyodbc.connect(conn_str, timeout=15)

def check():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT IDBODEGA,
               SUM(CASE WHEN ST_FISICO != 0 THEN 1 ELSE 0 END) as con_stock,
               SUM(ST_FISICO) as fisico_total
        FROM Foviedo.dbo.R_STOCK_PRODUCTOS
        WHERE IDBODEGA IN (40, 39)
        GROUP BY IDBODEGA
    """)
    rows = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    conn.close()
    psv = rows.get(40, (0, 0))
    ssv = rows.get(39, (0, 0))
    return psv, ssv

def alertar():
    """Alerta visual y sonora en pantalla."""
    print('\n' + '='*60, flush=True)
    print('  >>>  INVENTARIO SV PROPAGADO AL SQL  <<<', flush=True)
    print('='*60, flush=True)
    print('  Correr ahora:', flush=True)
    print('  python scripts/descargar_dif_sv.py', flush=True)
    print('='*60 + '\n', flush=True)
    # Beep 5 veces
    for _ in range(5):
        print('\a', end='', flush=True)
        time.sleep(0.5)

log('=== Monitor iniciado. Objetivo: PSV<=2, SSV<=3 con stock ===')
log(f'Revisando cada {INTERVALO//60} minutos. Ctrl+C para detener.')

while True:
    try:
        psv, ssv = check()
        psv_ok = psv[0] <= 2
        ssv_ok = ssv[0] <= 3
        estado = 'LISTO' if (psv_ok and ssv_ok) else 'esperando'
        log(f'PSV={psv[0]} cod (sum={int(psv[1])}) | SSV={ssv[0]} cod (sum={int(ssv[1])}) | {estado}')

        if psv_ok and ssv_ok:
            log('>>> INVENTARIO PROPAGADO - EJECUTAR descargar_dif_sv.py <<<')
            ntfy('✅ INVENTARIO SV PROPAGADO', f'PSV={psv[0]} cod | SSV={ssv[0]} cod — Correr descargar_dif_sv.py ahora')
            alertar()
            break
        else:
            ntfy('🔄 Monitor SV — sin cambios', f'PSV={psv[0]} cod (sum={int(psv[1])}) | SSV={ssv[0]} cod (sum={int(ssv[1])}) | esperando...', prioridad='low')

        time.sleep(INTERVALO)

    except KeyboardInterrupt:
        log('Monitor detenido por el usuario.')
        break
    except Exception as e:
        log(f'[VPN/SQL ERROR] {e}')
        # Beep de alerta — posible VPN caida
        for _ in range(10):
            print('\a', end='', flush=True)
            time.sleep(0.3)
        ntfy('⚠️ VPN/SQL caido', 'Monitor no puede conectar a SQL. Reconectar FortiClient.', prioridad='high')
        log('Reintentando en 60s... Si VPN cayo, reconectar FortiClient.')
        time.sleep(60)
