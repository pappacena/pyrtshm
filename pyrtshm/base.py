import pickle
import socket
from threading import Thread
from typing import List, Dict, Optional, Tuple

from pyrtshm.protocol.protocol_v1_pb2 import State, OperationType


class SharedMemory(Thread):
    host: str
    port: int
    forward_list: List
    socket: Optional[socket.socket]
    states: Dict
    data: Dict

    def __init__(self, listen: Tuple, forward_nodes: List):
        """
        Build the shared memory.

        :param listen: The tuple with (host, port) to listen.
        :param forward_nodes: The list of tuples to where incoming states
            should be forwarded.
        """
        super(SharedMemory, self).__init__()
        self.host, self.port = listen
        self.socket = None
        self.data = {}
        self.states = {}

        self.forward_nodes = forward_nodes

        self.should_run = True
        self.sock_bufsize = 1024

    def init_socket(self):
        if self.socket is not None:
            return self.socket
        family = socket.AF_INET6 if ":" in self.host else socket.AF_INET
        self.socket = socket.socket(family, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))
        return self.socket

    def decode_key(self, obj_bytes: bytes) -> object:
        return pickle.loads(obj_bytes)

    def decode_value(self, obj_bytes: bytes) -> object:
        return pickle.loads(obj_bytes)

    def encode_key(self, obj: object) -> bytes:
        return pickle.dumps(obj)

    def encode_value(self, obj: object) -> bytes:
        return pickle.dumps(obj)

    def run(self):
        self.init_socket()
        with self.init_socket():
            while self.should_run:
                try:
                    self.process_msg()
                except socket.error:
                    pass

    def process_msg(self):
        data = self.socket.recv(self.sock_bufsize)
        msg = State()
        msg.ParseFromString(data)
        key = self.decode_key(msg.key)

        current_state = self.states.get(key)
        if current_state and current_state.seq_number > msg.seq_number:
            # Don't override our value with older values.
            return

        self.states[key] = msg
        if msg.operation_type == OperationType.DELETE:
            try:
                del self.data[key]
            except KeyError:
                # Delete operation should fail silently if the key doesn't
                # exist. We might have missed the state setting this key,
                # for example.
                pass
        else:
            self.data[key] = self.decode_value(msg.data)

    def forward(self, packets):
        for destination in self.forward_nodes:
            for pkt in packets:
                self.socket.sendto(pkt, destination)

    def stop(self):
        self.should_run = False

    def get_next_state(self, key: object, value: object) -> State:
        state = self.states.get(key)
        data = self.encode_value(value)
        if state is not None:
            state.seq_number += 1
            state.data = data
        else:
            state = State(key=self.encode_key(key), seq_number=1, data=data)
            self.states[key] = state
        return state

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, key: object, value: object):
        state = self.get_next_state(key, value)
        self.data[key] = value
        self.forward([state.SerializeToString()])

    def __delitem__(self, key):
        state = self.get_next_state(key, None)
        state.operation_type = OperationType.DELETE
        del self.data[key]
        self.forward([state.SerializeToString()])
