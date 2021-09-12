import socket
from threading import Thread
from typing import List, Dict, Optional, Tuple

from pyrtshm.protocol.protocol_v1_pb2 import State


class RTSharedMemory(Thread):
    host: str
    port: int
    forward_list: List
    socket: Optional[socket.socket]
    data: Dict

    def __init__(self, listen: Tuple, forward_nodes: List):
        """
        Build the shared memory.

        :param listen: The tuple with (host, port) to listen.
        :param forward_nodes: The list of tuples to where incoming states
            should be forwarded.
        """
        super(RTSharedMemory, self).__init__()
        self.host, self.port = listen
        self.socket = None
        self.data = {}

        self.forward_nodes = forward_nodes

        self.should_run = True
        self.sock_bufsize = 1024

    def init_socket(self):
        if self.socket is not None:
            return
        family = socket.AF_INET6 if ":" in self.host else socket.AF_INET
        self.socket = socket.socket(family, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))

    def run(self):
        self.init_socket()
        while self.should_run:
            data = self.socket.recv(self.sock_bufsize)
            msg = State()
            msg.ParseFromString(data)
            key = msg.key

            self[key] = msg
            self.forward([data])

    def forward(self, packets):
        for destination in self.forward_nodes:
            for pkt in packets:
                self.socket.sendto(pkt, destination)

    def join(self, *args, **kwargs):
        self.should_run = False
        super(RTSharedMemory, self).join(*args, **kwargs)

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, key, value):
        assert isinstance(value, State)
        assert key == value.key
        # If it's setting an outdated value, move on.
        if key in self.data and self.data[key].seq_number > value.seq_number:
            return
        self.data[key] = value
        self.forward([value.SerializeToString()])
