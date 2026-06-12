import zipfile
import xml.etree.ElementTree as ET
import re

# Extraer contenido del DOCX
with zipfile.ZipFile("docs/AnexoH_Especificacion_APIs_v2_2_FINAL.docx", "r") as zip_ref:
    with zip_ref.open("word/document.xml") as xml_file:
        content = xml_file.read().decode("utf-8")
        root = ET.fromstring(content)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        text_elements = root.findall(".//w:t", ns)
        full_text = "".join([elem.text for elem in text_elements if elem.text])
        
        # Buscar cada endpoint y extraer la sección de Request body (JSON schema)
        endpoints = [
            "POST /api/Komands/v1/unsuscription",
            "POST /api/Komands/v1/activation",
            "POST /api/Komands/v1/modification",
            "POST /api/Komands/v1/device-modification",
            "POST /api/Komands/v1/fiber-change",
            "reset-ont"
        ]
        
        # Buscar "Request body (JSON schema)" seguido de una tabla con los campos
        for ep in endpoints:
            if ep in full_text:
                idx = full_text.find(ep)
                # Extraer siguiente 3000 caracteres que probablemente contengan el esquema
                section = full_text[idx:idx+5000]
                print(f"\n{'='*70}")
                print(f"ENDPOINT: {ep}")
                print('='*70)
                print(section)
