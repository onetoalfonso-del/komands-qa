import zipfile
import xml.etree.ElementTree as ET

# Extraer contenido del DOCX
with zipfile.ZipFile("docs/AnexoH_Especificacion_APIs_v2_2_FINAL.docx", "r") as zip_ref:
    with zip_ref.open("word/document.xml") as xml_file:
        content = xml_file.read().decode("utf-8")
        # Extraer todo el texto
        root = ET.fromstring(content)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        text_elements = root.findall(".//w:t", ns)
        full_text = "".join([elem.text for elem in text_elements if elem.text])
        
        # Buscar los endpoints
        endpoints = [
            "unsuscription",
            "activation",
            "modification",
            "device-modification",
            "fiber-change",
            "reset-ont"
        ]
        
        for ep in endpoints:
            if ep in full_text.lower():
                idx = full_text.lower().find(ep)
                print(f"\n{'='*60}")
                print(f"ENDPOINT: {ep}")
                print("="*60)
                print(full_text[max(0, idx-100):idx+2000])
