import openpyxl, sys
sys.stdout.reconfigure(encoding='utf-8')

wb = openpyxl.load_workbook('Casos de Pruebas PosVenta.xlsx', read_only=True)
ws = wb['Hoja1']
rows = list(ws.iter_rows(values_only=True))

olt_real = []
for row in rows[2:]:
    if row[0] is None:
        continue
    tipo = str(row[11]) if row[11] else ''
    if 'OLT REAL' in tipo:
        olt_real.append({
            'id':      row[0],
            'modulo':  row[2],
            'nombre':  row[3],
            'vno':     row[4],
            'vendor':  row[5],
            'modelo':  row[6],
            'ambiente': row[14],
        })

print(f'Total casos OLT REAL (E2E reales): {len(olt_real)}\n')

vno_actual = None
for c in olt_real:
    if c['vno'] != vno_actual:
        vno_actual = c['vno']
        print(f'\n=== VNO: {vno_actual} ===')
    print(f"  {c['id']} | {c['vendor']} {c['modelo']} | {c['nombre']}")
