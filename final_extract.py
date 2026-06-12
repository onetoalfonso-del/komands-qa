import json

# Leer el archivo Postman
with open("collection Kommand/SN a Kommand.postman_collection.json", "r", encoding="utf-8") as f:
    collection = json.load(f)

# Diccionario para almacenar resultados
results = {}

# Buscar los 6 endpoints
endpoint_mapping = {
    "unsuscription": "01 — Baja de Acceso (Unsuscription)",
    "activation": "02 — Activación (Activation)",
    "modification": "03 — Modificación de Servicio (Modification)",
    "device-modification": "04 — Cambio de Equipo (Device Modification)",
    "fiber-change": "05 — Cambio de Fibra (Fiber Change)",
    "reset-ont": "06 — Reset ONT"
}

# Buscar cada endpoint
for folder in collection["item"]:
    folder_name = folder.get("name", "")
    
    for ep_key, ep_name in endpoint_mapping.items():
        if ep_name in folder_name:
            print(f"\n{'='*70}")
            print(f"ENDPOINT: {ep_key}")
            print('='*70)
            
            # Buscar el primer request con body JSON en ese folder
            found = False
            for item in folder.get("item", []):
                if found:
                    break
                request = item.get("request", {})
                body = request.get("body", {})
                raw = body.get("raw", "")
                
                if raw and "{" in raw:
                    try:
                        # Parsear JSON del body
                        body_json = json.loads(raw)
                        print("Request body fields:")
                        for field in sorted(body_json.keys()):
                            print(f"  {field}")
                        results[ep_key] = sorted(body_json.keys())
                        found = True
                    except Exception as e:
                        pass

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
for ep_key in ["unsuscription", "activation", "modification", "device-modification", "fiber-change", "reset-ont"]:
    if ep_key in results:
        print(f"\n{ep_key}:")
        for field in results[ep_key]:
            print(f"  - {field}")
