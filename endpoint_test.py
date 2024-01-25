import requests
import json
    
# Define the data you'll send with the request
data = {
    "key1": "value1",
    "key2": "value2",
}

# Convert your data into JSON format
jsonData = json.dumps(data)

response = requests.post("http://localhost:50505/evaluate", data=jsonData)

if response.status_code == 200:
    print("Endpoint is active.")
else:
    print("Endpoint might not be active.")
