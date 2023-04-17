#!/usr/bin/env python
from argparse import ArgumentParser
import sys
import shlex
import os
import psutil
from subprocess import Popen, PIPE
import re

node_pat = re.compile(r'.*mininet:(.*)')


def list_nodes(do_print=False):
    pids = dict()
    for p in psutil.process_iter():
        if m := re.match(node_pat, shlex.join(p.cmdline())):
            host = m.group(1)
            pids[host] = p.pid
    return pids


def main(node: str, cmd: str):
    pid_by_name = list_nodes()
    # print pid_by_name
    pid = pid_by_name.get(node)
    if pid is None:
        raise ValueError
    os.system("mnexec -a %s %s" % (pid, cmd))


if __name__ == '__main__':
    parser = ArgumentParser("Connect to a mininet node and run a command")
    parser.add_argument('--node',
                        help="The node's name (e.g., h1, h2, etc.)")
    parser.add_argument('--list', action="store_true", default=False,
                        help="List all running nodes.")
    parser.add_argument('--cmd', default='ifconfig',
                        help="Command to run inside node.")

    FLAGS = parser.parse_args()
    if FLAGS.list:
        list_nodes(do_print=True)
        exit(0)

    if not FLAGS.node:
        parser.print_help()
        exit(1)
    try:
        main(FLAGS.node, FLAGS.cmd)
    except ValueError:
        print(f"node {FLAGS.node} not found")
        exit(1)
