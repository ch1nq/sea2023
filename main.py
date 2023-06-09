import logging
import src.server

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    app = src.server.app
    app.run(debug=True)
