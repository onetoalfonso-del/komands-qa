import openpyxl, sys
sys.stdout.reconfigure(encoding='utf-8')

wb = openpyxl.load_workbook('Casos de Pruebas PosVenta.xlsx', read_only=True)
ws = wb['Hoja1']
rows = list(ws.iter_rows(values_only=True))

cases = [r for r in rows[2:] if r[0] and str(r[0]).startswith('PV-')]

modulos = {}
tipos = {}
for r in cases:
    mod = str(r[2]) if r[2] else 'Sin módulo'
    tipo = str(r[11]) if r[11] else 'Sin tipo'
    tipo_simple = tipo.split('—')[0].split('\n')[0].strip()
    modulos[mod] = modulos.get(mod, 0) + 1
    tipos[tipo_simple] = tipos.get(tipo_simple, 0) + 1

print(f'TOTAL casos post-venta: {len(cases)}\n')
print('--- Por módulo ---')
for m, n in sorted(modulos.items()):
    print(f'  {m}: {n}')
print()
print('--- Por tipo de dato ---')
for t, n in sorted(tipos.items(), key=lambda x: -x[1]):
    print(f'  {t}: {n}')
