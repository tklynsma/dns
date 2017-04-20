#!/usr/bin/env python3

""" 
DNS server: this script contains the code for starting a DNS server.
"""


from argparse import ArgumentParser
from dns.server import Server


def run_server():
    parser = ArgumentParser(description="DNS Server")
    parser.add_argument("-c", "--caching", action="store_true",
            help="Enable caching")
    parser.add_argument("-t", "--ttl", metavar="time", type=int, default=0, 
            help="TTL value of cached entries (if > 0)")
    parser.add_argument("-p", "--port", type=int, default=5353,
            help="Port which server listens on")
    parser.add_argument("-v", "--verbose", action="store_true",
            help="Enable verbose output")
    args = parser.parse_args()

    server = Server(args.port, args.caching, args.ttl, args.verbose)
    try:
        server.serve()
    except KeyboardInterrupt:
        server.shutdown()
        print()

if __name__ == "__main__":
    run_server()
