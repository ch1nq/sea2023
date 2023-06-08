import logging
import src.server

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    app = src.server.app
    # TODO: change to wss when using https
    app.config["ws_url"] = "ws://localhost:8001"
    app.run(debug=True)
