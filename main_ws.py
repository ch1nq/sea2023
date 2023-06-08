import asyncio
import logging
import signal
import websockets

import src.editor

logging.basicConfig(level=logging.INFO)


async def main():
    # Set the stop condition when receiving SIGTERM.
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)
    async with websockets.serve(src.editor.handler, "", 8001):
        await stop


if __name__ == "__main__":
    asyncio.run(main())
