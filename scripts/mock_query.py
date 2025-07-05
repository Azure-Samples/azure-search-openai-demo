import os
import requests

# === Variables de entorno ===
SEARCH_ENDPOINT = os.getenv("SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("SEARCH_KEY")
SEARCH_INDEX = os.getenv("SEARCH_INDEX")

def search_chunks_by_rol_and_text(rol, query, top=5):
    headers = {
        "api-key": SEARCH_KEY,
        "Content-Type": "application/json"
    }

    params = {
        "search": query,
        "$filter": f"rol eq '{rol}'",
        "$top": top,
        "$orderby": "archivo"
    }

    url = f"{SEARCH_ENDPOINT}/indexes/{SEARCH_INDEX}/docs?api-version=2021-04-30-Preview"
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        results = response.json().get("value", [])
        print(f"\n🔍 Resultados para rol: '{rol}' con palabra clave: '{query}'\n")
        if not results:
            print("🚫 No se encontraron documentos que cumplan los filtros.")
        for r in results:
            print(f"📁 Archivo: {r.get('archivo')}")
            print(f"🏷️ Rol: {r.get('rol')} | Origen: {r.get('origen')}")
            print("🧠 Contenido:")
            print(f"{r.get('content')[:400]}...\n")
    else:
        print(f"⚠️ Error en la consulta → {response.status_code}: {response.text}")

if __name__ == "__main__":
    # Puedes cambiar estos valores para probar otros casos
    search_chunks_by_rol_and_text(rol="pilotos", query="turbulencia", top=3)