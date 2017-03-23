#!/usr/bin/env python3

"""Tests for your DNS resolver and server"""

import sys
import unittest
from unittest import TestCase
from argparse import ArgumentParser
from dns.resolver import Resolver

PORT = 5001
SERVER = "localhost"
TIMEOUT = 2

class TestResolver(TestCase):
    """Resolver tests"""

    def test_valid_FQDN1(self):
        hostname = "gaia.cs.umass.edu"
        resolver = Resolver(TIMEOUT, False, 0)
        result = resolver.gethostbyname(hostname)
        self.assertEqual(result, (hostname, [], ['128.119.245.12']))

    def test_valid_FQDN2(self):
        hostname = "www.ru.nl"
        resolver = Resolver(TIMEOUT, False, 0)
        result = resolver.gethostbyname(hostname)
        self.assertEqual(result, ("wwwproxy.ru.nl", [hostname], ['131.174.78.60']))

    def test_valid_FQDN3(self):
        hostname = "www.gmail.com"
        resolver = Resolver(TIMEOUT, False, 0)
        result = resolver.gethostbyname(hostname)
        self.assertEqual(result, ("googlemail.l.google.com", [hostname, "mail.google.com"], ['172.217.17.37']))

    def test_invalid_FQDN(self):
        hostname = "invalid.cs.ru.nl"
        resolver = Resolver(TIMEOUT, False, 0)
        result = resolver.gethostbyname(hostname)
        self.assertEqual(result, (hostname, [], [])) 

class TestCache(TestCase):
    """Cache tests"""

class TestResolverCache(TestCase):
    """Resolver tests with cache enabled"""

class TestServer(TestCase):
    """Server tests"""

def run_tests():
    """Run the DNS resolver and server tests"""
    parser = ArgumentParser(description="DNS Tests")
    parser.add_argument("-s", "--server", type=str, default="localhost",
                        help="the address of the server")
    parser.add_argument("-p", "--port", type=int, default=5001,
                        help="the port of the server")
    args, extra = parser.parse_known_args()
    global PORT, SERVER
    PORT = args.port
    SERVER = args.server

    # Pass the extra arguments to unittest
    sys.argv[1:] = extra

    # Start test suite
    unittest.main()

if __name__ == "__main__":
    run_tests()
