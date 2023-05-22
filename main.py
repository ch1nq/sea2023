import logging
import os

import ngrok

import src.server

logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    if os.environ.get("NGROK_AUTH_TOKEN"):
        tunnel = ngrok.werkzeug_develop()
    src.server.app.run(debug=True)
