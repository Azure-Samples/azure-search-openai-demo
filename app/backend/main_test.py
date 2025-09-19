import os
from dotenv import load_dotenv

# Load test environment variables
load_dotenv('.env.test')

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=50505, debug=True)