# CMIT-Python
**Version**: 0.1.0

This is a python implementation of the Common Messaging Interface Transport (CMIT) protocol.

As a protocol CMIT is designed to support internal process communication (IPC) within
a single node. Consequently, this current version only supports serving through a
UNIX domain socket. By default, CMIT supports 3 message command verbs (PING, EXECUTE, POLL).
However, CMIT is designed to be very flexible, and you may augment it with your own command verbs.

## Installation
```bash
pip install cmit
```

## Usage
Implementing a CMIT server can be very simple. A basic implementation is shown below. Another example can be
found in the `demo` directory.

```python
from cmit import server
SOCKET_PATH = "/tmp/cmit.sock"
demo_server = server.CMITServer(SOCKET_PATH, server.SimpleCMITRequestHandler)
demo_server.serve_forever()
```

**Note**: The default handler `SimpleCMITRequestHandler` will accept POLL and EXECUTE requests, the actual processing
of these requests is left up to the final implementation. That is, they are simply acknowledged.

## Rationale
I designed the CMIT protocol to handle communication between a webserver and a backend process. The backend process
was often a long-running process that would be invoked by the webserver when a request was received. Because the backend
process was long-running, it could not be invoked directly by the webserver or else the webserver would block. With CMIT,
the webserver could send a request to the backend process and continue processing other requests. The backend process
would then run in the background and send a response back to the webserver through the CMIT protocol when it was finished.
The additional benefit to taking this approach was that it didn't require any additional infrastructure such as a message
broker or cache. The CMIT protocol is designed to be very simple and lightweight, and is not intended to replace more
robust protocols such as AMQP or HTTP.

## Specification
The CMIT protocol is a simple text-based protocol. The protocol is designed to be flexible and extensible. If you
are already familiar with the HTTP protocol, you will find that CMIT is very similar in nature. 

### Request
The following describes the basic structure of a CMIT request.

```
<COMMAND> <VERSION>
<BLANK LINE>
<MESAAGE BODY>
<BLANK LINE>
```

A CMIT request is composed of a command verb, a version, and a message body. The command verb is a string that
identifies the type of request. The version is a string that identifies the version of the protocol. The message
body is a string that contains the actual message. Unlike HTTP, CMIT does not support headers and the message body
is not optional. In a plain CMIT request, the message body is a JSON object containing four fields: `id`, `timestamp`,
`topic`, and `payload`.

```json
{
"id": "f4dc4223403b22fbca286ec676717440", 
"timestamp": "1702712308.739593",
"topic": "test.handler",
"payload": {
"args": ["arg1", "arg2"], 
"kwargs": {"key1": "value1", "key2": "value2"}, 
"data": "some data"}
}
```

#### id
The `id` field is a string that uniquely identifies the message. The `id` field is used to match a response to a
request as well as assist in message deduplication, logging and storing message. When sending a request, the `id` field 
is optional, and will automatically be generated if not provided.

#### timestamp
The `timestamp` field is a string that identifies the time the message was sent. The `timestamp` field is optional and
will automatically be generated if not provided. If provided, the timestamp should be in POSIX time format.

#### topic
The `topic` field is a string that identifies the topic of the message. The `topic` is essentially a routing key that
is used to route the message to the appropriate handler. The `topic` field is required.

#### payload
The `payload` field can be any JSON serializable object such as a string, object, or list. The `payload` field is 
not required, however the default implementation of the `SimpleCMITRequestHandler` will append the `payload` field as
an object to both the request and response at a minimum.

### Response
The following describes the basic structure of a CMIT response.

```
<VERSION> <STATUS> <REASON>
<BLANK LINE>
<MESAAGE BODY>
<BLANK LINE>
```

A CMIT response is composed of a version, a status, a reason, and a message body. The version is a string that
identifies the version of the protocol. The status is a string that identifies the status of the response. The reason
is a string that provides a human-readable description of the status. The message body is a string that contains the
actual message. Just like the request, responses do not support headers and the message body is not optional and follows
the same general format of requests by containing a JSON object with the four fields: `id`, `timestamp`, `topic`, 
and `payload`.

The difference between a request and a response is that the `id` field is required in a response and must match the `id`
field of the request. The `timestamp` field should be the same as the request. The `topic` field should be the same as
the request. The `payload` field is optional and can be any JSON serializable object.

### Command Verbs
Command verbs are used to identify the type of request. The following command verbs are supported by default:
- PING
- EXECUTE
- POLL

However, you may add your own command verbs by extending the `CMITRequestHandler` with methods that match the command
verb. For example, if you wanted to add a command verb called `TEST`, you would add a method called `do_TEST` to your
handler. See the `demo/echo-server.py` file for an example on how to do this.


#### PING
The `PING` command verb is used to test the connection to the server. By default a `PING` request will return a response
with a copy of the request's `payload` field.

#### EXECUTE
The `EXECUTE` command verb is used to execute a command on the server. However, the default implementation of the
`SimpleCMITRequestHandler` does not actually execute any commands. Instead, it simply acknowledges the request and
returns a response with an ok status. The `EXECUTE` command verb is intended to be extended by the user to execute
scripts or commands on the server. This is the command verb that I use to execute commands on the backend process.

#### POLL
The `POLL` command verb is used to poll the server for messages. The default implementation of the 
`SimpleCMITRequestHandler` will return the length of the pending execution queue. This is the command verb that I use
to poll the backend process for messages.

### Final Notes
Like I said before, the CMIT protocol is designed to be very simple and lightweight. Its design is inspired by a
particular need I had, and I hope that it can be useful to others. If you have any questions or suggestions, please
feel free to open an issue or submit a pull request. I might at some point add more robust documentation, but for now
I think this is sufficient.

## Acknowledgements
I pulled a lot of inspiration from the HTTP protocol, and I also used the `BaseHTTPRequestHandler` class from the
`http.server` module as a starting point for the `CMITRequestHandler` class. I also used the `socketserver` module
to implement the `CMITServer` class. Finally, I based the `cmit.request` module on the `requests` library. All of these
ideas were of course modified to fit the needs of the CMIT protocol, but I wanted to acknowledge them nonetheless.