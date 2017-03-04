#!/usr/bin/env python3

"""DNS Resolver

This module contains a class for resolving hostnames. You will have to implement
things in this module. This resolver will be both used by the DNS client and the
DNS server, but with a different list of servers.
"""


import socket

from dns.classes import Class
from dns.message import Message, Question, Header
from dns.name import Name
from dns.types import Type


class Resolver:
    """DNS resolver"""

    def __init__(self, timeout, caching, ttl):
        """Initialize the resolver

        Args:
            caching (bool): caching is enabled if True
            ttl (int): ttl of cache entries (if > 0)
        """
        self.timeout = timeout
        self.caching = caching
        self.ttl = ttl

    def gethostbyname(self, hostname):
        """Translate a host name to IPv4 address.

        Currently this method contains an example. You will have to replace
        this example with the algorithm described in section 5.3.3 in RFC 1034.

        Args:
            hostname (str): the hostname to resolve

        Returns:
            (str, [str], [str]): (hostname, aliaslist, ipaddrlist)
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)

        # Create and send query
        question = Question(Name(hostname), Type.A, Class.IN)
        header = Header(9001, 0, 1, 0, 0, 0)
        header.qr = 0
        header.opcode = 0
        header.rd = 1
        query = Message(header, [question])
        sock.sendto(query.to_bytes(), ("8.8.8.8", 53))

        # Receive response
        data = sock.recv(512)
        response = Message.from_bytes(data)

        # Get data
        aliaslist = []
        ipaddrlist = []
        for answer in response.answers:
            if answer.type_ == Type.A:
                ipaddrlist.append(answer.rdata.address)
            if answer.type_ == Type.CNAME:
                aliaslist.append(hostname)
                hostname = str(answer.rdata.cname)

        return hostname, aliaslist, ipaddrlist
