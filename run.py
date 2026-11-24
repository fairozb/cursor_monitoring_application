"""Entry point: run the demo app on localhost port 5000."""

from app import create_app
from app.config import Config

app = create_app()

if __name__ == "__main__":
    # Local Jumpbox demo only — do not change firewall or bind publicly
    app.run(host=Config.HOST, port=Config.PORT, debug=False)
