import logging
import socketserver

from cmit import messages, server, utils, CMITStatus

logging.basicConfig(filename="/var/log/cmit/echo-server.log", level=logging.DEBUG)

SOCKET_FILE = "/src/echo.sock"

common_logger = logging.getLogger()


class UNIXServer(server.CMITServer):
    request_queue_size = 10
    task_router = {}
    logger = common_logger


class TaskHandler(server.SimpleCMITRequestHandler):
    server: UNIXServer
    logger = common_logger

    def get_task_queue(self, que_name) -> list:

        self.logger.debug(f"Retrieving job queue for {que_name}")

        # check if the task_router has been created
        if not hasattr(self.server, 'task_router'):
            setattr(self.server, 'task_router', {})

        if que_name not in self.server.task_router:
            self.server.task_router[que_name] = []

        return self.server.task_router[que_name]

    def register_task(self, task_route, task_id, task_args=None, task_kwargs=None, task_data=None):

        self.logger.debug(f"Registering task: {task_id} - {task_route}")

        new_task = {
            "route": task_route,
            "task_id": task_id,
            "args": task_args,
            "kwargs": task_kwargs,
            "data": task_data
        }

        self.get_task_queue(task_route).append(new_task)

    @utils.cmit_response
    def do_EXECUTE(self):
        """
        Handle the EXECUTE command.
        """

        # Add job to inbox
        self.register_task(self.msg.topic, self.msg.msg_id)

        msg = messages.CMITMessage(self.msg.topic, self.msg.msg_id)
        msg.payload = {"res": "Processed"}

        return CMITStatus.ACCEPTED, msg

    @utils.cmit_response
    def do_POLL(self):
        """
        Handle the POLL command
        """

        length = len(self.get_task_queue(self.msg.topic))

        msg = messages.CMITMessage(self.msg.topic, self.msg.msg_id)
        msg.payload = {"depth": length}

        return CMITStatus.OK, msg


def run(address, threading=False, on_bind=None, server_cls=UNIXServer):
    """
    Run a UNIX socket server.

    :param address: The address to bind to.
    :param threading: Whether to use threading or not.
    :param on_bind: Optional callback to be called after the server has bound.
    :param server_cls: The server class to use.
    """
    if threading:
        unixd_cls = type("UnixServer", (socketserver.ThreadingMixIn, server_cls), {})
    else:
        unixd_cls = server_cls
    unixd = unixd_cls(address, TaskHandler, bind_and_activate=True)
    if on_bind:
        on_bind(getattr(unixd, "server_address", address))

    if threading:
        unixd_cls.daemon_threads = True

    common_logger.info("Starting server...")
    unixd.serve_forever()


if __name__ == "__main__":
    run(SOCKET_FILE)
