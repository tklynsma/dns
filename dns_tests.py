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
TTL = 1


class TestResolver(TestCase):
    """Resolver tests without cache"""

    @classmethod
    def setUpClass(cls):
        cls.resolver = Resolver(TIMEOUT, False, 0)

    def test_valid_hostname1(self):
        """Solve valid FQDN."""
        hostname = "gaia.cs.umass.edu."
        result = self.resolver.gethostbyname(hostname)
        self.assertEqual(result, (hostname, [], ['128.119.245.12']))

    def test_valid_hostname2(self):
        """Solve valid FQDN with one alias."""
        hostname = "www.ru.nl."
        result = self.resolver.gethostbyname(hostname)
        self.assertEqual(result, ("wwwproxy.ru.nl.", [hostname], ['131.174.78.60']))

    def test_valid_hostname3(self):
        """Solve valid FQDN with two aliases."""
        hostname = "www.gmail.com."
        result = self.resolver.gethostbyname(hostname)
        self.assertEqual(result, ("googlemail.l.google.com.",
            [hostname, "mail.google.com."], ["172.217.17.69"]))

    def test_valid_hostname4(self):
        """Test equal output for input with and without trailing dot."""
        hostname1 = "google.nl"
        hostname2 = "google.nl."
        result1 = self.resolver.gethostbyname(hostname1)
        result2 = self.resolver.gethostbyname(hostname2)
        self.assertEqual(result1, result2)

    def test_invalid_hostname(self):
        """Solve invalid FQDN, empty output generated."""
        hostname = "invalid_address.com."
        result = self.resolver.gethostbyname(hostname)
        self.assertEqual(result, (hostname, [], [])) 


class TestCache(TestCase):
    """Cache tests"""

    @classmethod
    def setUpClass(cls):
        rdata1 = ARecordData("0.0.0.0")
        rdata2 = CNAMERecordData(Name("b"))
        rdata3 = CNAMERecordData(Name("c"))
        cls.record1 = ResourceRecord(Name("a"), Type.A, Class.IN, 10, rdata1)
        cls.record2 = ResourceRecord(Name("a"), Type.CNAME, Class.IN, 10, rdata2)
        cls.record3 = ResourceRecord(Name("a"), Type.CNAME, Class.IN, 10, rdata3)

        cls.cache = RecordCache()
        cls.cache.add_record(cls.record1)
        cls.cache.add_record(cls.record2)
        cls.cache.add_record(cls.record3)

    @classmethod
    def tearDownClass(cls):
        del cls.cache
        try:
            os.remove("test_cache")
        except:
            print("\nFailed to remove test_cache")

    def test_lookup1(self):
        """Test cache lookup for A records."""
        result = self.cache.lookup("a.", Type.A, Class.IN)
        self.assertEqual(result, [self.record1])

    def test_lookup2(self):
        """Test cache lookup for CNAME records."""
        result = self.cache.lookup("a.", Type.CNAME, Class.IN)
        self.assertEqual(result, [self.record2, self.record3])

    def test_lookup3(self):
        """Test cache lookup for non-existing records, output should be empty."""
        result = self.cache.lookup("b.", Type.A, Class.IN)
        self.assertEqual(result, [])

    def test_ttl(self):
        """Test cache lookup for exceeded ttl, record should not be included in answer."""
        rdata = ARecordData("1.1.1.1")
        record = ResourceRecord(Name("a"), Type.A, Class.IN, TTL, rdata)
        self.cache.add_record(record)
        result = self.cache.lookup("a.", Type.A, Class.IN)
        self.assertEqual(result, [self.record1, record])
        time.sleep(TTL)
        result = self.cache.lookup("a.", Type.A, Class.IN)
        self.assertEqual(result, [self.record1])

    def test_add_duplicate(self):
        """Test adding duplicate data, only the last added record should be in cache."""
        cache = RecordCache()
        rdata1 = ARecordData("2.2.2.2")
        rdata2 = ARecordData("2.2.2.2")
        record1 = ResourceRecord(Name("a"), Type.A, Class.IN, 1, rdata1)
        record2 = ResourceRecord(Name("a"), Type.A, Class.IN, 1, rdata2)
        cache.add_record(record1)
        cache.add_record(record2)
        result = cache.lookup("a.", Type.A, Class.IN)
        self.assertEqual(result, [record2])

    def test_filter_cache(self):
        """Test cache filtering for exceeded ttl."""
        rdata1 = ARecordData("5.5.5.5")
        rdata2 = CNAMERecordData(Name("a"))
        record1 = ResourceRecord(Name("a"), Type.A, Class.IN, TTL, rdata1)
        record2 = ResourceRecord(Name("b"), Type.CNAME, Class.IN, TTL, rdata2)
        cache = RecordCache()
        cache.add_record(record1)
        cache.add_record(record2)
        time.sleep(TTL)
        cache.filter_cache()
        self.assertEqual(cache.records, {})

    def test_read_write_cache_file(self):
        """Test cache file reading and writing."""
        self.cache.write_cache_file("test_cache")
        cache_copy = RecordCache()
        cache_copy.read_cache_file("test_cache")
        for key, record_set in self.cache.records.items():
            self.assertTrue(key in cache_copy.records)
            for i, record in enumerate(record_set):
                self.assertEqual(record, cache_copy.records[key][i])


class TestResolverCache(TestCase):
    """Resolver tests with cache enabled"""

    @classmethod
    def setUpClass(cls):
        cls.resolver = Resolver(TIMEOUT, True, 0)
        cls.resolver.cache.clear_cache()

    def test_cached_hostname1(self):
        """Solve an invalid cached FQDN, output corresponds to cache."""
        hostname = "invalid_address1.com."
        rdata = ARecordData("0.0.0.0")
        record = ResourceRecord(Name(hostname), Type.A, Class.IN, 1, rdata)
        self.resolver.cache.add_record(record)
        result = self.resolver.gethostbyname(hostname)
        self.assertEqual(result, (hostname, [], ["0.0.0.0"]))

    def test_cached_hostname2(self):
        """Solve an invalid cached CNAME and FQDN, output corresponds to cache."""
        hostname1 = "invalid_address2.com."
        hostname2 = "invalid_address3.com."
        rdata1 = CNAMERecordData(Name(hostname2))
        rdata2 = ARecordData("1.1.1.1")
        record1 = ResourceRecord(Name(hostname1), Type.CNAME, Class.IN, 1, rdata1)
        record2 = ResourceRecord(Name(hostname2), Type.A, Class.IN, 1, rdata2)
        self.resolver.cache.add_record(record1)
        self.resolver.cache.add_record(record2)
        result = self.resolver.gethostbyname(hostname1)
        self.assertEqual(result, (hostname2, [hostname1], ["1.1.1.1"]))

    def test_cached_hostname3(self):
        """Solve invalid cached CNAME chain, output corresponds to alias (google.nl.)"""
        hostname1 = "invalid_address4.com."
        hostname2 = "invalid_address5.com."
        hostname3 = "google.nl."
        rdata1 = CNAMERecordData(Name(hostname2))
        rdata2 = CNAMERecordData(Name(hostname3))
        record1 = ResourceRecord(Name(hostname1), Type.CNAME, Class.IN, 1, rdata1)
        record2 = ResourceRecord(Name(hostname2), Type.CNAME, Class.IN, 1, rdata2)
        self.resolver.cache.add_record(record1)
        self.resolver.cache.add_record(record2)
        result = self.resolver.gethostbyname(hostname1)
        self.assertEqual(result, (hostname3, [hostname1, hostname2], ["172.217.17.67"]))

    def test_cached_hostname4(self):
        """Wait TTL time for an invalid cached FQDN to expire, output is empty."""
        hostname = "invalid_address6.com."
        rdata = ARecordData("2.2.2.2")
        record = ResourceRecord(Name(hostname), Type.A, Class.IN, TTL, rdata)
        self.resolver.cache.add_record(record)
        time.sleep(TTL)
        result = self.resolver.gethostbyname(hostname)
        self.assertEqual(result, (hostname, [], []))
        
    def test_shared_cache(self):
        """Test shared cache between resolvers."""
        resolver2 = Resolver(TIMEOUT, True, 0)
        hostname = "invalid_address7.com."
        rdata = ARecordData("3.3.3.3")
        record = ResourceRecord(Name(hostname), Type.A, Class.IN, 1, rdata)
        resolver2.cache.add_record(record)
        result = self.resolver.gethostbyname(hostname)
        self.assertEqual(result, (hostname, [], ["3.3.3.3"]))


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
