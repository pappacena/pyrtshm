---
# pyrtshm

[![codecov](https://codecov.io/gh/pappacena/pyrtshm/branch/main/graph/badge.svg?token=pyrtshm_token_here)](https://codecov.io/gh/pappacena/pyrtshm)
[![CI](https://github.com/pappacena/pyrtshm/actions/workflows/main.yml/badge.svg)](https://github.com/pappacena/pyrtshm/actions/workflows/main.yml)

pyrtshm is a real-time distributed shared memory implemented in python over 
UDP protocol using protobuf.

It is intended to be used as a dict that mirrors its keys and values 
across distributed nodes in environments that can tolerate packet losses, 
but need real time updates. For example, games backend, live stream of stock 
prices, machine discovery and monitoring, etc.

To give a simple example, think of 2 hosts running your project, `node-1` 
and `node-2`. In `node-1` you have:

```python
mem = SharedMemory(listen=('0.0.0.0', 3333), forward_nodes=[('node-2', 3333)])
```

In `node-2`, you have:

```python
mem = SharedMemory(listen=('0.0.0.0', 3333), forward_nodes=[('node-1', 3333)])
```

Now, if you set any key in one of the nodes like this:

```python
mem["my-key"] = 1
```

In almost real time, with high thoughput, `mem["my-key"]` will have value 
`1` in the other node. You can add as many nodes as needed in the 
`forward_nodes` list.

## Install it from PyPI

```bash
pip install pyrtshm
```

## Usage

```py
from pyrtshm import SharedMemory

# Each node initializes itself by indicating its own port, and the 
# host & sport of the other nodes (the "forward nodes").
other_nodes = [('host1', 3333), ('host2', 3333), ('host3', 3333)]
mem = SharedMemory(listen=('0.0.0.0', 3333), forward_nodes=other_nodes)

# Set a key, making it available to other nodes.
mem["host1/cpu"] = 75.1

# Get a key set by another node.
avg_cpu = mem["host1/cpu"] + mem["host2/cpu"]

# Deletes a key locally and to the other nodes
del mem["host0/cpu"]
```

## Development

Read the [CONTRIBUTING.md](CONTRIBUTING.md) file.
