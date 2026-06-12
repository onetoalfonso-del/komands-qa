import json

# Leer el archivo Postman
with open("collection Kommand/SN a Kommand.postman_collection.json", "r", encoding="utf-8") as f:
    collection = json.load(f)

# Buscar los endpoints
endpoints_to_find = {
    "unsuscription": "01 — Baja de Acceso (Unsuscription)",
    "activation": "02 — Activación (Activation)",
    "modification": "03 — Modificación de Servicio (Modification)",
    "device-modification": "04 — Cambio de Serie ONT (Device Modification)",
    "fiber-change": "05 — Cambio de Pelo (Fiber Change)",
    "reset-ont": "06 — Reset ONT"
}

# Buscar cada endpoint
for folder in collection["item"]:
    folder_name = folder.get("name", "")
    
    for ep_key, ep_name in endpoints_to_find.items():
        if ep_name in folder_name:
            print("\n" + "="*70)
            print(f"ENDPOINT: {ep_key.upper()}")
            print("="*70)
            
            # Buscar el primer request en ese folder
            for item in folder.get("item", []):
                request = item.get("request", {})
                body = request.get("body", {})
                raw = body.get("raw", "")
                
                if raw and "{" in raw:
                    try:
                        # Parsear JSON del body
                        body_json = json.loads(raw)
                        print("Request body fields:")
                        for field in sorted(body_json.keys()):
                            print(f"  - {field}")
                        break
                    except:
                        pass
            break
