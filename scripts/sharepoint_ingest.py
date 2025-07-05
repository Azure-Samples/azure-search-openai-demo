# sharepoint_ingest.py

import os
import requests
from msal import ConfidentialClientApplication

# --- Configuración de credenciales Azure AD ---
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SITE_ID = os.getenv("SITE_ID")
DRIVE_ID = os.getenv("DRIVE_ID")  # Librería de documentos
FOLDER_PATH = "/docs"  # Carpeta SharePoint a escanear

def get_access_token():
    app = ConfidentialClientApplication(
        client_id=CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        client_credential=CLIENT_SECRET
    )
    token_result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    return token_result["access_token"]

def list_documents_in_folder(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/drives/{DRIVE_ID}/root:{FOLDER_PATH}:/children"
    
    docs = []
    while url:
        resp = requests.get(url, headers=headers)
        data = resp.json()
        docs.extend(data.get("value", []))
        url = data.get("@odata.nextLink", None)  # paginación automática
    return docs

def download_document(file_id, file_name, access_token):
    url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/drives/{DRIVE_ID}/items/{file_id}/content"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    with open(f"./data/{file_name}", "wb") as f:
        f.write(response.content)
    print(f"Descargado: {file_name}")

def chunkify_document(file_path, rol="desconocido"):
    # Implementar chunking semántico con metadatos
    chunks = []
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
        # Aquí podrías agregar lógica NLP para dividir por secciones, párrafos, etc.
        chunks.append({
            "text": text,
            "metadata": {
                "rol": rol,
                "origen": "sharepoint",
                "archivo": os.path.basename(file_path)
            }
        })
    return chunks

def main():
    token = get_access_token()
    documentos = list_documents_in_folder(token)

    for doc in documentos:
        file_id = doc["id"]
        file_name = doc["name"]
        folder_name = doc.get("parentReference", {}).get("path", "")
        rol_tag = folder_name.split("/")[-1] if "/" in folder_name else "general"

        download_document(file_id, file_name, token)
        # Aquí podrías llamar a chunkify_document y luego enviar chunks a Cognitive Search

if __name__ == "__main__":
    main()