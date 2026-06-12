"""
Compara los casos del Excel (Casos de Pruebas PosVenta.xlsx) contra los tests
pytest existentes, agrupando por módulo cuántos casos tienen cobertura.

Estrategia de detección: escanea el contenido de cada test_*.py buscando
referencias explícitas al ID del caso Excel en formato "PV-XXX-NNN"
(en comentarios, docstrings, strings de parametrize, etc.).
"""
import os
import re
import openpyxl
import sys

sys.stdout.reconfigure(encoding='utf-8')

# ─── 1. Leer casos del Excel ──────────────────────────────────────────────────
wb = openpyxl.load_workbook('Casos de Pruebas PosVenta.xlsx', read_only=True)
ws = wb['Hoja1']
rows = list(ws.iter_rows(values_only=True))

excel_cases = {}
for row in rows[2:]:
    case_id = row[0]
    if not case_id or not str(case_id).startswith('PV-'):
        continue
    parts = str(case_id).split('-')
    if len(parts) >= 3:
        modulo = f"PV-{parts[1]}"
        try:
            num = int(parts[2])
        except ValueError:
            continue
        excel_cases.setdefault(modulo, []).append((case_id, row[3]))

# ─── 2. Leer cobertura de tests ───────────────────────────────────────────────
TEST_DIR = 'tests'
covered_by_module = {}  # module -> set of covered case numbers

for root, dirs, files in os.walk(TEST_DIR):
    for fname in files:
        if not fname.startswith('test_') or not fname.endswith('.py'):
            continue
        fpath = os.path.join(root, fname)
        content = open(fpath, encoding='utf-8').read()

        # Busca cualquier patrón PV-XXX-NNN en el archivo (comentarios, strings, docstrings)
        for m in re.finditer(r'PV-([A-Z]+)-(\d+)', content):
            module = f"PV-{m.group(1)}"
            num = int(m.group(2))
            covered_by_module.setdefault(module, set()).add(num)

# ─── 3. Comparar ─────────────────────────────────────────────────────────────
print(f"{'MÓDULO':<20} {'Excel':>6} {'Con test':>9} {'Sin test':>9} {'Cobertura':>10}")
print("-" * 60)

total_excel = 0
total_covered = 0
missing_all = []

for modulo, cases in sorted(excel_cases.items()):
    covered_nums = covered_by_module.get(modulo, set())
    covered = []
    missing = []
    for case_id, nombre in cases:
        parts = str(case_id).split('-')
        num = int(parts[2])
        if num in covered_nums:
            covered.append(case_id)
        else:
            missing.append((case_id, nombre))

    pct = len(covered) / len(cases) * 100 if cases else 0
    print(f"{modulo:<20} {len(cases):>6} {len(covered):>9} {len(missing):>9} {pct:>9.0f}%")
    total_excel += len(cases)
    total_covered += len(covered)
    if missing:
        missing_all.append((modulo, missing))

print("-" * 60)
total_pct = total_covered / total_excel * 100 if total_excel else 0
print(f"{'TOTAL':<20} {total_excel:>6} {total_covered:>9} {total_excel-total_covered:>9} {total_pct:>9.0f}%")

if missing_all:
    print(f"\n\n{'='*60}")
    print("CASOS SIN COBERTURA DE TEST:")
    print('='*60)
    for modulo, cases in missing_all:
        print(f"\n{modulo} ({len(cases)} sin test):")
        for case_id, nombre in cases:
            print(f"  {case_id}: {nombre}")
