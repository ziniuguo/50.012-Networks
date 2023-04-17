import argparse
from functools import partial
from unittest.mock import Mock, create_autospec, MagicMock

from bgp import start_frr_daemon_on_node
from run import main as run_in_node

from mininet.node import Node

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Start routing services in rogue AS")
    parser.add_argument('--frr-bin-dir', default='/usr/lib/frr')
    parser.add_argument('--config-dir', default="./conf")
    parser.add_argument('--log-dir', default="./logs")
    args = parser.parse_args()

    class FakeNode: pass
    fake_node = FakeNode()
    setattr(fake_node, "name", "R4")
    fake_node.cmd = Mock()
    fake_node.waitOutput = Mock()
    _start_frr_daemon = partial(start_frr_daemon_on_node,
                                frr_bin_dir=args.frr_bin_dir,
                                config_dir=args.config_dir,
                                log_dir=args.log_dir)
    _start_frr_daemon(node=fake_node, daemon="bgpd")
    start_bgpd_cmd = fake_node.cmd.call_args.args[0]
    fake_node.cmd.reset_mock()
    _start_frr_daemon(node=fake_node, daemon="zebra")
    start_zebra_cmd = fake_node.cmd.call_args.args[0]

    run_in_node(node="R4", cmd=start_zebra_cmd)
    run_in_node(node="R4", cmd=start_bgpd_cmd)
    run_in_node(node="R4", cmd="ip link set lo up")
