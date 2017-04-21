#!/usr/bin/env python3

"""Tests for your DNS resolver and server"""


import os
import socket
import sys
import time
import unittest

from unittest import TestCase
from argparse import ArgumentParser
from dns.cache import RecordCache
from dns.classes import Class
from dns.message import Message, Header, Question
from dns.name import Name
from dns.resolver import Resolver
from dns.resource import CNAMERecordData, ARecordData, ResourceRecord
from dns.rtypes import Type
from dns.server import Server
from threading import Thread

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
        hostname1 = "gaia.cs.umass.edu"
        hostname2 = "gaia.cs.umass.edu."
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
        """Test cache lookup for exceeded ttl, record should not be in answer."""
        rdata = ARecordData("1.1.1.1")
        record = ResourceRecord(Name("a"), Type.A, Class.IN, TTL, rdata)
        self.cache.add_record(record)
        result = self.cache.lookup("a.", Type.A, Class.IN)
        self.assertEqual(result, [self.record1, record])
        time.sleep(TTL)
        result = self.cache.lookup("a.", Type.A, Class.IN)
        self.assertEqual(result, [self.record1])

    def test_add_duplicate(self):
        """Test adding duplicate data, only last added record should be in cache."""
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
        """Solve invalid cached CNAME chain, output IP corresponds to alias"""
        hostname1 = "invalid_address4.com."
        hostname2 = "invalid_address5.com."
        hostname3 = "gaia.cs.umass.edu."
        rdata1 = CNAMERecordData(Name(hostname2))
        rdata2 = CNAMERecordData(Name(hostname3))
        record1 = ResourceRecord(Name(hostname1), Type.CNAME, Class.IN, 1, rdata1)
        record2 = ResourceRecord(Name(hostname2), Type.CNAME, Class.IN, 1, rdata2)
        self.resolver.cache.add_record(record1)
        self.resolver.cache.add_record(record2)
        result = self.resolver.gethostbyname(hostname1)
        self.assertEqual(result, (hostname3, [hostname1, hostname2],
            ['128.119.245.12']))

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


class RunTestServer(Thread):
    """A thread to run the server for testing."""

    def __init__(self, server):
        super().__init__()
        self.daemon = True
        self.done = False
        self.server = server

    def run(self):
        """Run the server thread."""
        while not self.done:
            self.server.serve()

    def shutdown(self):
        """Shut the test server down."""
        self.done = True
        self.server.shutdown()


class TestServer(TestCase):
    """Server tests"""

    @classmethod
    def setUpClass(cls):
        server = Server(PORT, True, 0)
        cls.run_server = RunTestServer(server)
        cls.run_server.start()
        cls.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        cls.sock.settimeout(TIMEOUT)

    @classmethod
    def tearDownClass(cls):
        cls.run_server.shutdown()
        cls.sock.close()

    def send_and_receive_query(self, hostname, rd, qtype=Type.A, ident=9001):
        """Create and send a query to the server and receive a response.

        Args:
            hostname (str): the hostname to resolve
            rd (Bool): indicates whether recursion is desired
            qtype (Type): the query type (default Type.A)
            ident (int): the identification number

        Returns:
            Message: the response message
        """
        question = Question(Name(hostname), qtype, Class.IN)
        header = Header(ident, 0, 1, 0, 0, 0)
        header.qr, header.opcode, header.rd = 0, 0, 1 if rd else 0
        query = Message(header, [question])
        try:
            self.sock.sendto(query.to_bytes(), (SERVER, PORT))
            response = Message.from_bytes(self.sock.recv(512))
            return response
        except:
            return None

    def test_server_zone1(self):
        """Solve a query for a FQDN for which the server has direct authority."""
        response = self.send_and_receive_query("ru.nl.", False)
        self.assertEqual(response.header.aa, 1)
        self.assertEqual(response.answers[0].type_, Type.A)
        self.assertEqual(str(response.answers[0].rdata), "131.174.78.60")

    def test_server_zone2(self):
        """Solve a query for a FQDN for which the server has direct authority,
        including a CNAME record."""
        response = self.send_and_receive_query("www.ru.nl.", False)
        self.assertEqual(response.header.aa, 1)
        self.assertEqual(response.answers[0].type_, Type.CNAME)
        self.assertEqual(response.answers[1].type_, Type.A)
        self.assertEqual(str(response.answers[0].rdata), "wwwproxy.ru.nl.")
        self.assertEqual(str(response.answers[1].rdata), "131.174.78.60")

    def test_server_zone3(self):
        """Solve a query for a FQDN for which your server does not have direct
        authority, yet there is a name server within your zone which does."""
        response = self.send_and_receive_query("cs.ru.nl.", False)
        self.assertEqual(response.header.an_count, 0)
        self.assertEqual(response.header.aa, 0)
        self.assertEqual(str(response.authorities[0].rdata), "ns1.science.ru.nl.")
        self.assertEqual(str(response.authorities[1].rdata), "ns2.science.ru.nl.")
        self.assertEqual(str(response.authorities[2].rdata), "ns3.science.ru.nl.")
        self.assertEqual(str(response.additionals[0].rdata), "131.174.224.4")
        self.assertEqual(str(response.additionals[1].rdata), "131.174.16.133")
        self.assertEqual(str(response.additionals[2].rdata), "131.174.30.34")

    def test_server_zone4(self):
        """Solve a query for a FQDN for which your server does not have direct
        authority, yet there is a (higher level) name server within your zone which
        does."""
        response = self.send_and_receive_query("sub.sub.sub.science.ru.nl.", False)
        self.assertEqual(response.header.an_count, 0)
        self.assertEqual(response.header.aa, 0)
        self.assertEqual(str(response.authorities[0].rdata), "ns1.science.ru.nl.")
        self.assertEqual(str(response.authorities[1].rdata), "ns2.science.ru.nl.")
        self.assertEqual(str(response.authorities[2].rdata), "ns3.science.ru.nl.")
        self.assertEqual(str(response.additionals[0].rdata), "131.174.224.4")
        self.assertEqual(str(response.additionals[1].rdata), "131.174.16.133")
        self.assertEqual(str(response.additionals[2].rdata), "131.174.30.34")

    def test_server_resolver1(self):
        """Solve a query for a FQDN which points outside your zone, with recursion"""
        response = self.send_and_receive_query("gaia.cs.umass.edu.", True)
        self.assertEqual(response.header.aa, 0)
        self.assertEqual(str(response.answers[0].rdata), '128.119.245.12')

    def test_server_resolver2(self):
        """Solve a query for a FQDN for which your server does not have direct
        authority, yet there is a name server within your zone which does, with
        recursion."""
        response = self.send_and_receive_query("cs.ru.nl.", True)
        self.assertEqual(response.header.aa, 0)
        self.assertEqual(str(response.answers[0].rdata), "131.174.8.6")

    def test_server_parallel(self):
        """Solve parallel requests for different FQDN."""
        hostname1 = "www.gmail.com."
        hostname2 = "wiki.science.ru.nl."
        question1 = Question(Name(hostname1), Type.A, Class.IN)
        question2 = Question(Name(hostname2), Type.A, Class.IN)
        header1 = Header(3333, 0, 1, 0, 0, 0)
        header2 = Header(4444, 0, 1, 0, 0, 0)
        header1.qr, header1.opcode, header1.rd = 0, 0, 1
        header2.qt, header2.opcode, header2.rd = 0, 0, 1
        query1 = Message(header1, [question1])
        query2 = Message(header2, [question2])

        try:
            self.sock.sendto(query1.to_bytes(), (SERVER, PORT))
            self.sock.sendto(query2.to_bytes(), (SERVER, PORT))
        except socket.error: self.assertTrue(False) # Test failed

        try:
            message1 = Message.from_bytes(self.sock.recv(512))
            message2 = Message.from_bytes(self.sock.recv(512))
        except: self.assertTrue(False) # Test failed

        response1 = message1 if message1.header.ident == 3333 else message2
        response2 = message1 if message1.header.ident == 4444 else message2
        self.assertEqual(response1.answers[0].type_, Type.CNAME)
        self.assertEqual(response1.answers[1].type_, Type.CNAME)
        self.assertEqual(response1.answers[2].type_, Type.A)
        self.assertEqual(response2.answers[0].type_, Type.A)
        self.assertEqual(str(response1.answers[0].rdata), "mail.google.com.")
        self.assertEqual(str(response1.answers[1].rdata), "googlemail.l.google.com.")
        self.assertEqual(str(response1.answers[2].rdata), "172.217.17.69")
        self.assertEqual(str(response2.answers[0].rdata), "131.174.8.71")

    def test_server_rcode3(self):
        """Solve a query for an invalid FQDN, with recursion."""
        response = self.send_and_receive_query("invalid_address.com.", True)
        self.assertEqual(response.header.rcode, 3)
        self.assertEqual(response.header.an_count, 0)
        self.assertEqual(response.header.ns_count, 0)
        self.assertEqual(response.header.ar_count, 0)

    def test_server_rcode4(self):
        """Solve a query of invalid (not implemented) type."""
        response = self.send_and_receive_query("ru.nl.", False, qtype=Type.MX)
        self.assertEqual(response.header.rcode, 4)
        self.assertEqual(response.header.an_count, 0)
        self.assertEqual(response.header.ns_count, 0)
        self.assertEqual(response.header.ar_count, 0)

    def test_server_rcode5(self):
        """Solve a query for a FQDN which points outside your zone, no recursion"""
        response = self.send_and_receive_query("gaia.cs.umass.edu.", False)
        self.assertEqual(response.header.rcode, 5)
        self.assertEqual(response.header.an_count, 0)
        self.assertEqual(response.header.ns_count, 0)
        self.assertEqual(response.header.ar_count, 0)


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
