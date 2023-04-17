#!/usr/bin/env python
from argparse import ArgumentParser
from functools import lru_cache, partial
from time import sleep, time
import os
from unittest.mock import Mock

from mininet.topo import Topo
from mininet.net import Mininet, Host, Node
from mininet.log import lg, info, setLogLevel
from mininet.cli import CLI
from mininet.node import Switch, OVSKernelSwitch
from mininet.node import OVSController
setLogLevel('info')

parser = ArgumentParser("Configure simple BGP network in Mininet.")
parser.add_argument('--rogue', action="store_true", default=False)
parser.add_argument('--sleep', default=3, type=int)
parser.add_argument('--frr-bin-dir', default='/usr/lib/frr')
parser.add_argument('--config-dir', default="./conf")
parser.add_argument('--log-dir', default="./logs")
args = parser.parse_args()

FLAGS_rogue_as = args.rogue
ROGUE_AS_NAME = 'R4'


def cleanup(ffr_bin_dir: str):
    ffr_daemon_names = " ".join(list_frr_daemon_names(ffr_bin_dir))
    os.system(f"killall -9  {ffr_daemon_names}> /dev/null 2>&1")


@lru_cache()
def list_frr_daemon_names(frr_bin_dir: str) -> list[str]:
    return [fname for fname in os.listdir(frr_bin_dir) if
            os.path.isfile(f"{frr_bin_dir}/{fname}") and os.access(f"{frr_bin_dir}/{fname}", os.X_OK)]


def start_frr_daemon_on_node(node: Node, daemon: str, frr_bin_dir: str, config_dir: str, log_dir: str):
    assert daemon in list_frr_daemon_names(frr_bin_dir)
    node.cmd("{bin_dir}/{daemon}"
             " -f {conf_dir}/{daemon}-{node_name}.conf"
             " -d"
             " -i /tmp/{daemon}-{node_name}.pid"
             " > {log_dir}/{daemon}-{node_name}.out 2>&1"
             .format(bin_dir=frr_bin_dir,
                     daemon=daemon,
                     conf_dir=config_dir,
                     log_dir=log_dir,
                     node_name=node.name))
    node.waitOutput()


@lru_cache()
def get_ip(hostname: str) -> str:
    AS = int(hostname[1])
    # AS = int(AS)
    if AS == 4:
        AS = 3
    ip = '%s.0.%s.1/24' % (10 + AS, hostname[2])
    return ip


@lru_cache()
def get_gateway(hostname: str) -> str:
    AS = int(hostname[1])
    # This condition gives AS4 the same IP range as AS3 so it can be an
    # attacker.
    if AS == 4:
        AS = 3
    gw = '%s.0.%s.254' % (10 + AS, hostname[2])
    return gw


class ExperimentTopo(Topo):
    def build(self):
        """The Autonomous System topology is a simple straight-line topology
        between AS1 -- AS2 -- AS3.  The rogue AS (AS4) connects to AS1 directly.

        """
        # if you change these, you need to build new config files accordingly!
        NUM_HOSTS_PER_AS = 3
        NUM_AS = 3
        # The topology has one router per AS
        for i in range(NUM_AS):
            as_id = i + 1
            self.addSwitch(f"R{as_id}")
        for i in range(NUM_AS):
            as_id = i + 1
            router_name = f"R{as_id}"
            for j in range(NUM_HOSTS_PER_AS):
                host_id = j + 1
                host_name = f"h{as_id}{host_id}"
                self.addHost(name=host_name,
                             ip=None,
                             inNamespace=True)
                self.addLink(router_name, host_name)

        for i in range(NUM_AS - 1):
            self.addLink('R%d' % (i + 1), 'R%d' % (i + 2))

        self.addSwitch("R4")
        # create hosts in rogueAS
        for j in range(NUM_HOSTS_PER_AS):
            as_id = NUM_AS + 1
            host_id = j + 1
            host_name = f"h{as_id}{host_id}"
            host = self.addHost(name=host_name,
                                ip=None,
                                inNamespace=True)
            self.addLink('R4', host_name)
        # This MUST be added at the end
        self.addLink('R1', 'R4')
        return

from mininet.node import Switch, Node
class Router(Switch):
    """Defines a new router that is inside a network namespace so that the
    individual routing entries don't collide.
    """

    ID = 0

    def __init__(self, name, **kwargs):

        kwargs['inNamespace'] = True
        Switch.__init__(self, name, **kwargs)

        Router.ID += 1
        self.switch_id = Router.ID

    def start(self, controllers):
        pass

    def defaultIntf(self):
        if hasattr(self, "controlIntf") and self.controlIntf:
            return self.controlIntf

        return Node.defaultIntf(self)

def main():
    # os.system("rm -f /tmp/R*.log /tmp/R*.pid logs/*")
    # os.system("mn -c >/dev/null 2>&1")
    # os.system("killall -9 zebra bgpd > /dev/null 2>&1")
    # os.system('pgrep -f webserver.py | xargs kill -9')

    _start_frr_daemon_on_node = partial(start_frr_daemon_on_node,
                                        frr_bin_dir=args.frr_bin_dir,
                                        config_dir=args.config_dir,
                                        log_dir=args.log_dir)
    _cleanup = partial(cleanup, ffr_bin_dir=args.frr_bin_dir)
    net = Mininet(topo=ExperimentTopo(), switch=Router)
    net.start()
    for router in net.switches:
        router.cmd("sysctl -w net.ipv4.ip_forward=1")
        router.waitOutput()

    print("Waiting %d seconds for sysctl changes to take effect..."
          % args.sleep)
    sleep(args.sleep)

    os.makedirs("./logs", exist_ok=True)
    for router in net.switches:
        if router.name == ROGUE_AS_NAME and not FLAGS_rogue_as:
            continue
        _start_frr_daemon_on_node(router, "zebra")
        _start_frr_daemon_on_node(router, "bgpd")
        # router.cmd(
        #     "/usr/lib/frr/zebra -f ./conf/zebra-%s.conf -d -i /tmp/zebra-%s.pid > logs/%s-zebra-stdout 2>&1" % (
        #         router.name, router.name, router.name))
        # router.waitOutput()
        # router.cmd(
        #     "/usr/lib/frr/bgpd -f ./conf/bgpd-%s.conf -d -i /tmp/bgp-%s.pid > logs/%s-bgpd-stdout 2>&1" % (
        #         router.name, router.name, router.name), shell=True)
        # router.waitOutput()
        # bring up lo interface, idk why it gets disabled
        router.cmd("ip link set lo up")
        print("Starting zebra and bgpd on %s" % router.name)

    for host in net.hosts:
        # start zebra in all hosts
        # host.cmd("{bin_dir}/{daemon}"
        #          " -f {conf_dir}/{daemon}-{node_name}.conf"
        #          " -d"
        #          " -i /tmp/{daemon}-{node_name}.pid"
        #          " > ./logs/{daemon}-{node_name}.out 2>&1"
        #          .format(bin_dir="/usr/lib/frr",
        #                  daemon="zebra",
        #                  conf_dir="./conf",
        #                  node_name=host.name))
        # host.waitOutput()
        # # start staticd in all hosts
        # host.cmd("{bin_dir}/{daemon}"
        #          " -f {conf_dir}/{daemon}-{node_name}.conf"
        #          " -d"
        #          " -i /tmp/{daemon}-{node_name}.pid"
        #          " > ./logs/{daemon}-{node_name}.out 2>&1"
        #          .format(bin_dir="/usr/lib/frr",
        #                  daemon="staticd",
        #                  conf_dir="./conf",
        #                  node_name=host.name))
        # host.waitOutput()
        _start_frr_daemon_on_node(host, "zebra")
        _start_frr_daemon_on_node(host, "staticd")
        print("Starting zebra and staticd in " + host.name)

    print("Starting web servers")
    net.getNodeByName("h31").popen("python3 -m http.server --directory webdirs/normal 80")
    net.getNodeByName("h41").popen("python3 -m http.server --directory webdirs/rogue 80")

    CLI(net)
    net.stop()

    _cleanup()


if __name__ == "__main__":
    main()
