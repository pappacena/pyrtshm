import socket
import time
from unittest import TestCase

from pyrtshm import RTSharedMemory
from pyrtshm.protocol.protocol_v1_pb2 import State


class TestBasicForwarding(TestCase):
    def start_nodes(self, n=5, initial_port=5551):
        host = '127.0.0.1'
        all_forwards = [(host, initial_port + i) for i in range(n)]
        nodes = []
        for i in range(n):
            forwards = [(host, port) for host, port in all_forwards
                        if port != initial_port + i]
            nodes.append(RTSharedMemory((host, initial_port + i), forwards))

        for n in nodes:
            n.start()
            self.addCleanup(n.join)
        return nodes

    def wait_nodes(self, nodes):
        time.sleep(0.1)
        for n in nodes:
            n.join()

    def test_set_local_value_forwards(self):
        nodes = self.start_nodes(10)

        some_node = nodes[0]
        msg = State(key=444, seq_number=1, data=b"some data goes here")
        some_node[444] = msg

        self.wait_nodes(nodes)
        for n in nodes:
            self.assertEqual(1, n[444].seq_number)
            self.assertEqual(444, n[444].key)
            self.assertEqual(b"some data goes here", n[444].data)

    def test_receive_message_forwards(self):
        nodes = self.start_nodes(3, initial_port=5551)

        msg = State()
        msg.key = 123
        msg.seq_number = 1
        msg.data = b"some data is here"

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(msg.SerializeToString(), ('127.0.0.1', 5551))

        self.wait_nodes(nodes)

        for n in nodes:
            self.assertEqual(b"some data is here", n[123].data)

