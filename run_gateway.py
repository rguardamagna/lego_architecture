"""Simple dev server to run the gateway locally."""
import sys
import os

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "services"))

from gateway.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
