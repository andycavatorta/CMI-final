import zmq
import sys
import time
import json

port = "5556"
context = zmq.Context()
socket = context.socket(zmq.PAIR)
socket.connect("tcp://localhost:%s" % port)

if len(sys.argv) == 2:
    msg = json.dumps([sys.argv[1]])
    print msg
    socket.send(msg)

if len(sys.argv) == 3:
    msg = json.dumps([sys.argv[1], sys.argv[2]])
    print msg
    socket.send(msg)
