import os
import requests
import uuid
import json
from msal import ConfidentialClientApplication

# === Variables de entorno ===
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SITE_ID = os.getenv("SITE_ID")
DRIVE_ID = os.getenv("DRIVE_ID")

SEARCH_ENDPOINT = os.getenv("SEARCH_ENDPOINT")  # Ej: https://<name>.search.windows.net
SEARCH_KEY = os.getenv("SEARCH_KEY")
SEARCH_INDEX = os.getenv("SEARCH_INDEX")

# === Autenticación Azure AD ===
def get_access_token():
    app = ConfidentialClientApplication(
        client_id=CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        client_credential=CLIENT_SECRET
    )
    token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    return token["access_token"]

# === Rol inferido por carpeta SharePoint ===
def infer_rol_from_path(path):
    path = path.upper()
    if "AEROPUERTOS" in path:
        return "aeropuertos"
    elif "CCO" in path:
        return "cco"
    elif "PILOTOS" in path:
        return "pilotos"
    elif "SOBRECARGOS" in path:
        return "sobrecargos"
    else:
        return "general"

# === Listar documentos de carpeta específica ===
def list_documents(token):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/drives/{DRIVE_ID}/root:/Volaris - Flightbot/Documentos Flightbot:/children"
    
    all_docs = []
    while url:
        resp = requests.get(url, headers=headers)
        data = resp.json()
        all_docs.extend(data.get("value", []))
        url = data.get("@odata.nextLink", None)
    return all_docs

# === Descarga de archivo ===
def download_document(file_id, file_name, token):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/drives/{DRIVE_ID}/items/{file_id}/content"
    response = requests.get(url, headers=headers)

    os.makedirs("data", exist_ok=True)
    file_path = f"./data/{file_name}"
    with open(file_path, "wb") as f:
        f.write(response.content)
    return file_path

# === Chunking simplificado ===
def chunkify(file_path, rol):
    with open(file_path, "rb") as f:
        content = f.read().decode(errors="ignore")
    return [{
        "text": content,
        "metadata": {
            "rol": rol,
            "origen": "sharepoint",
            "archivo": os.path.basename(file_path)
        }
    }]

# === Envío a Cognitive Search ===
def push_to_search(chunk):
    headers = {
        "Content-Type": "application/json",
        "api-key": SEARCH_KEY
    }
    doc = {
        "value": [{
            "@search.action": "mergeOrUpload",
            "id": str(uuid.uuid4()),
            "content": chunk["text"],
            "rol": chunk["metadata"]["rol"],
            "archivo": chunk["metadata"]["archivo"],
            "origen": chunk["metadata"]["origen"]
        }]
    }
    url = f"{SEARCH_ENDPOINT}/indexes/{SEARCH_INDEX}/docs/index?api-version=2021-04-30-Preview"
    response = requests.post(url, headers=headers, data=json.dumps(doc))
    if response.status_code == 200:
        print(f"📥 Indexado: {chunk['metadata']['archivo']} ({chunk['metadata']['rol']})")
    else:
        print(f"⚠️ Error en indexación: {response.status_code} → {response.text}")

# === MAIN ===
def main():
    token = get_access_token()
    documentos = list_documents(token)

    for doc in documentos:
        file_id = doc["id"]
        file_name = doc["name"]
        path = doc.get("parentReference", {}).get("path", "")
        rol = infer_rol_from_path(path)

        local_path = download_document(file_id, file_name, token)
        chunks = chunkify(local_path, rol)

        for chunk in chunks:
            push_to_search(chunk)

if __name__ == "__main__":
    main()