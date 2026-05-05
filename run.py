from dotenv import load_dotenv
load_dotenv()

from config import DEBUG
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081, debug=DEBUG)
