import socket
import time
import logging

from cmit import requests

logging.basicConfig(filename="/var/log/cmit/echo-client.log", level=logging.DEBUG)

logger = logging.getLogger(__name__)


SOCKET_FILE = "cmit://src/echo.sock"

if __name__ == "__main__":
    logger.info("Starting client...")

    cycle = 0

    while True:
        try:

            while cycle < 1000:
                t = f"ping-{cycle}"
                logger.info(f"Send PING request at cycle {cycle} - {time.time()}")
                resp = requests.ping(SOCKET_FILE, t)

                logger.info(f"Got response {resp.status_code} - elapsed {resp.elapsed}")
                if resp.status_code == 200 and resp.msg.topic == t:
                    logger.info(f"Response {resp.msg.topic} - {resp.msg.payload}")
                    cycle += 1
                else:
                    logger.info(f"Response {resp.reason}")
                    cycle = 1000

            while cycle < 2000:
                t = 'a.b.c'
                logger.info(f"Send EXECUTE request at cycle {cycle} - {time.time()}")
                resp = requests.execute(SOCKET_FILE, t)

                logger.info(f"Got response {resp.status_code} - elapsed {resp.elapsed}")

                if resp.status_code in (200, 202) and resp.msg.topic == t:
                    logger.info(f"Response {resp.msg.topic} - {resp.msg.payload}")
                    cycle += 1
                else:
                    logger.info(f"Response {resp.reason}")
                    cycle = 2002

            if 2000 <= cycle < 2001:
                t = 'a.b.c'
                logger.info(f"Send POLL request at cycle {cycle} - {time.time()}")
                resp = requests.poll(SOCKET_FILE, t)

                if resp.status_code == 200 and resp.msg.topic == t:
                    logger.info(f"Response {resp.msg.topic} - {resp.msg.payload} - {type(resp.msg.payload)}")
                    cycle += 1
                else:
                    logger.info(f"Response {resp.reason}")
                    cycle = 2001

        except FileNotFoundError:
            logger.info("File not found")
            time.sleep(5)

        except socket.error:
            time.sleep(0.1)

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.exception(e)
