"""
Validación de acceso a Azure OpenAI
"""
import os
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI

def check_env_vars():
    print("🔍 Validando variables de entorno...")
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_MODEL",
        "AZURE_OPENAI_API_VERSION"
    ]
    for var in required_vars:
        val = os.getenv(var)
        print(f"  {var}: {'✅' if val else '❌'} {val or 'No definida'}")

def check_token():
    print("\n🔑 Probando adquisición de token para MI...")
    cred = DefaultAzureCredential()
    try:
        token = cred.get_token("https://cognitiveservices.azure.com/.default")
        print("  Token adquirido ✅:", token.token[:50], "...")
        return cred
    except Exception as e:
        print("  ❌ Error al adquirir token:", e)
        return None

def test_openai_call(cred):
    print("\n🧪 Probando llamada a chat completion...")
    try:
        client = AzureOpenAI(
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            azure_ad_token_credential=cred
        )

        messages = [
            {"role": "system", "content": "Eres un copiloto técnico."},
            {"role": "user", "content": "Haz un echo de prueba para validar acceso."}
        ]

        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_MODEL"),
            messages=messages,
            temperature=0.7,
            max_tokens=100
        )
        print("  Respuesta ✅:", response.choices[0].message.content)
    except Exception as e:
        print("  ❌ Error en completion:", e)

if __name__ == "__main__":
    check_env_vars()
    credential = check_token()
    if credential:
        test_openai_call(credential)
