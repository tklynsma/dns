#!/usr/bin/env python3

"""Tests for your DNS resolver and server"""

import sys
import unittest
from unittest import TestCase
from argparse import ArgumentParser

PORT = 5001
SERVER = "localhost"

class TestResolver(TestCase):
    """Resolver tests"""

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
