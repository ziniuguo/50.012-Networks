import argparse
from functools import partial
from unittest.mock import Mock, create_autospec, MagicMock

from bgp import start_frr_daemon_on_node
from run import main as run_in_node

from mininet.node import Node

if __name__ == "__main__":
    stop_zebra_cmd = "ps aux | grep -ie zebra-R4 | grep -v grep | awk '{print $2}' | xargs kill -9 "
    stop_bgpd_cmd = "ps aux | grep -ie bgpd-R4 | grep -v grep | awk '{print $2}' | xargs kill -9 "
    run_in_node(node="R4", cmd=stop_bgpd_cmd)
    run_in_node(node="R4", cmd=stop_zebra_cmd)
    run_in_node(node="R4", cmd="ip link set lo up")
