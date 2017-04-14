#!/usr/bin/env python3

"""Tests for your DNS resolver and server"""


import os
import sys
import time
import unittest

from unittest import TestCase
from argparse import ArgumentParser
from dns.cache import RecordCache
from dns.classes import Class
from dns.name import Name
from dns.resolver import Resolver
from dns.resource import CNAMERecordData, ARecordData, ResourceRecord
from dns.rtypes import Type

PORT = 5001
SERVER = "localhost"
TIMEOUT = 2


class TestResolver(TestCase):
    """Resolver tests"""

    @classmethod
    def setUpClass(cls):
        cls.resolver = Resolver(TIMEOUT, False, 0)

    def test_valid_hostname1(self):
        hostname = "gaia.cs.umass.edu."
        result = self.resolver.gethostbyname(hostname)
        self.assertEqual(result, (hostname, [], ['128.119.245.12']))

    def test_valid_hostname2(self):
        hostname = "www.ru.nl."
        result = self.resolver.gethostbyname(hostname)
        self.assertEqual(result, ("wwwproxy.ru.nl.", [hostname], ['131.174.78.60']))

    def test_valid_hostname3(self):
        hostname1 = "nyan.cat"
        hostname2 = "nyan.cat."
        result1 = self.resolver.gethostbyname(hostname1)
        result2 = self.resolver.gethostbyname(hostname2)
        self.assertEqual(result1, result2)

    def test_invalid_hostname(self):
        hostname = "invalid_domain.nl."
        result = self.resolver.gethostbyname(hostname)
        self.assertEqual(result, (hostname, [], [])) 


class TestCache(TestCase):
    """Cache tests"""

    @classmethod
    def setUpClass(cls):
        cls.r1 = ResourceRecord(Name("a"), Type.A, Class.IN, 60, ARecordData("0.0.0.0"))
        cls.r2 = ResourceRecord(Name("a"), Type.CNAME, Class.IN, 60, CNAMERecordData(Name("b")))
        cls.r3 = ResourceRecord(Name("a"), Type.CNAME, Class.IN, 60, CNAMERecordData(Name("c")))

        cls.cache = RecordCache()
        cls.cache.add_record(cls.r1)
        cls.cache.add_record(cls.r2)
        cls.cache.add_record(cls.r3)

    @classmethod
    def tearDownClass(cls):
        del cls.cache
        try:
            os.remove("test_cache")
        except:
            print("\nFailed to remove test_cache")

    def test_lookup(self):
        self.assertEqual(self.cache.lookup("a.", Type.A, Class.IN), [self.r1])
        self.assertEqual(self.cache.lookup("a.", Type.CNAME, Class.IN), [self.r2, self.r3])
        self.assertEqual(self.cache.lookup("b.", Type.A, Class.IN), [])

    def test_lookup_ttl_exceeded(self):
        record = ResourceRecord(Name("a"), Type.A, Class.IN, 1, ARecordData("1.1.1.1"))
        self.cache.add_record(record)
        self.assertEqual(self.cache.lookup("a.", Type.A, Class.IN), [self.r1, record])
        time.sleep(1)
        self.assertEqual(self.cache.lookup("a.", Type.A, Class.IN), [self.r1])

    def test_filter_cache(self):
        cache = RecordCache()
        r1 = ResourceRecord(Name("a"), Type.A, Class.IN, 1, ARecordData("0.0.0.0"))
        r2 = ResourceRecord(Name("a"), Type.A, Class.IN, 1, ARecordData("1.1.1.1"))
        cache.add_record(r1)
        cache.add_record(r2)
        time.sleep(1)
        cache.filter_cache()
        self.assertEqual(cache.records, {})

    def test_read_write_cache_file(self):
        self.cache.write_cache_file("test_cache")
        cache_copy = RecordCache()
        cache_copy.read_cache_file("test_cache")
        for key, record_set in self.cache.records.items():
            self.assertTrue(key in cache_copy.records)
            for i, record in enumerate(record_set):
                self.assertEqual(record, cache_copy.records[key][i])


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
