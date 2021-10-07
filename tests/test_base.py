import time
from unittest import TestCase

from pyrtshm import SharedMemory


class ValueObject:
    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c

    def __eq__(self, other):
        return other.a == self.a and other.b == self.b and other.c == self.c


class TestBasicForwarding(TestCase):
    def start_nodes(self, n=3, initial_port=5551):
        host = "127.0.0.1"
        all_forwards = [(host, initial_port + i) for i in range(n)]
        nodes = []
        for i in range(n):
            forwards = [
                (host, port)
                for host, port in all_forwards
                if port != initial_port + i
            ]
            nodes.append(SharedMemory((host, initial_port + i), forwards))
        for n in nodes:
            # Force socket initialization and timeout.
            n.init_socket()
            n.socket.settimeout(0.1)
            n.start()
            self.addCleanup(n.stop)
            self.addCleanup(n.join)
        return nodes

    def stop_nodes(self, nodes):
        for n in nodes:
            n.stop()
            n.join()
            n.socket.close()

    def wait_nodes(self, nodes):
        time.sleep(0.1)
        for n in nodes:
            n.stop()

    def values_got_set_and_forwarded(self, nodes, key, value):
        some_node = nodes[0]
        some_node[key] = value

        self.wait_nodes(nodes)
        for n in nodes:
            retries = 3
            while retries > 0:
                if n[key] == value:
                    break
                else:
                    if retries == 0:
                        return False
                    else:
                        retries -= 1
                        time.sleep(0.05)
        return True

    def test_primitive_object_set(self):
        keys = [1, b"bin", "some str", 1.34, (1, 2)]
        values = keys + [{1: "a"}, [3, 2, 1], ValueObject("1", b"x", 123)]
        for key in keys:
            if key == 1:
                continue
            for value in values:
                nodes = self.start_nodes()
                self.assertTrue(
                    self.values_got_set_and_forwarded(nodes, key, value),
                    f"Error setting {key}: {value}",
                )
                self.stop_nodes(nodes)
            return

    def test_set_value(self):
        main, *nodes = self.start_nodes(n=3)
        main[1] = 123

        self.wait_nodes([main] + nodes)
        self.assertEqual(2, main.metrics.sent_packets)
        self.assertEqual(0, main.metrics.forward_key_set)
        for n in nodes:
            self.assertEqual(123, n[1])
            self.assertEqual(1, n.metrics.received_packets)
            self.assertEqual(1, n.metrics.forward_key_set)

    def test_get_default_value_key_not_set(self):
        main, *nodes = self.start_nodes(n=3)
        main[1] = 123

        self.wait_nodes([main] + nodes)
        for n in nodes:
            self.assertEqual(123, n.get(1))
            self.assertEqual(-1, n.get("no-existing-key", -1))

    def test_set_value_multiple_times(self):
        main, *nodes = self.start_nodes(n=3)
        main["x"] = 123
        main["x"] = 333
        main["x"] = 987

        self.wait_nodes([main] + nodes)
        self.assertEqual(2 * 3, main.metrics.sent_packets)
        self.assertEqual(0, main.metrics.forward_key_set)
        for n in nodes:
            self.assertEqual(3, n.states["x"].seq_number)
            self.assertEqual(987, n["x"])
            self.assertEqual(3, n.metrics.received_packets)
            self.assertEqual(3, n.metrics.forward_key_set)

    def test_delete_value(self):
        main, *nodes = self.start_nodes()

        main[1] = 123
        del main[1]

        self.wait_nodes([main] + nodes)

        # Should have send 4 packets: 2 to set, and 2 to del.
        self.assertEqual(2 * 2, main.metrics.sent_packets)
        self.assertEqual(0, main.metrics.forward_key_set)
        self.assertEqual(0, main.metrics.forward_key_del)
        for n in nodes:
            self.assertNotIn("x", n.states)
            self.assertRaises(KeyError, lambda: n[1])
            self.assertEqual(0, n.metrics.sent_packets)
            self.assertEqual(1, n.metrics.forward_key_set)
            self.assertEqual(1, n.metrics.forward_key_del)
