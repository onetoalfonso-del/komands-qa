import zipfile
import xml.etree.ElementTree as ET
import os

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

def extract_docx(path):
    text_parts = []
    with zipfile.ZipFile(path) as z:
        with z.open("word/document.xml") as f:
            content = f.read().decode("utf-8", errors="replace")
    root = ET.fromstring(content)
    for para in root.iter(f"{{{W}}}p"):
        texts = [t.text or "" for t in para.iter(f"{{{W}}}t")]
        line = "".join(texts).strip()
        if line:
            text_parts.append(line)
    return text_parts

base = r"c:\Users\sopor\Desktop\Kommand\docs"

# Leer Anexo E desde línea 1980 hasta el final (checklist certificación)
print("=== ANEXO E — Checklist certificación (líneas 1978 al final) ===\n")
path = os.path.join(base, "Anexo_E_Especificacion_APIs_Komands_COMPLETO (1).docx")
lines = extract_docx(path)
for i, line in enumerate(lines[1978:], start=1978):
    print(f"{i}: {line}")

print("\n\n=== HLD — Sección 19 Pruebas (líneas 5350-5500) ===\n")
path2 = os.path.join(base, "HLD_SunsetBP_CONSOLIDADO_v2_Final.docx")
try:
    lines2 = extract_docx(path2)
    for i, line in enumerate(lines2[5340:5520], start=5340):
        print(f"{i}: {line}")
except Exception as e:
    print(f"ERROR: {e}")
    # Try to get what we can before the error
