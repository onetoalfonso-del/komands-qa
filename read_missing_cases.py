import openpyxl, sys
sys.stdout.reconfigure(encoding='utf-8')

wb = openpyxl.load_workbook('Casos de Pruebas PosVenta.xlsx', read_only=True)
ws = wb['Hoja1']
rows = list(ws.iter_rows(values_only=True))

MODULOS = ['PV-RBK Rollback', 'PV-IDP Idempotencia', 'PV-DB Base de Datos']

for modulo in MODULOS:
    casos = [r for r in rows[2:] if r[0] and r[2] == modulo]
    print(f'\n{"="*60}')
    print(f'MÓDULO: {modulo} ({len(casos)} casos)')
    print(f'{"="*60}')
    for c in casos:
        print(f'\nID: {c[0]}')
        print(f'Nombre: {c[3]}')
        print(f'VNO: {c[4]} | Vendor: {c[5]}')
        print(f'Descripción: {c[8]}')
        print(f'Tipo: {str(c[11])[:80]}')
        print(f'Resultado esperado: {c[13]}')
