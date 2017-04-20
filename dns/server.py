#!/usr/bin/env python3

"""A recursive DNS server

This module provides a recursive DNS server. You will have to implement this
server using the algorithm described in section 4.3.2 of RFC 1034.
"""

import socket

from dns.message import Header, Message
from dns.name import Name
from dns.rtypes import Type
from dns.util import vprint
from dns.zone import Zone
from threading import Thread


class RequestHandler(Thread):
    """A handler for requests to the DNS server"""

    def __init__(self, query, sock, address, zone, caching, ttl, verbose=False):
        """Initialize the handler thread"""
        super().__init__()
        self.daemon = True
        self.query = query
        self.sock = sock
        self.address = address
        self.zone = zone
        self.caching = caching
        self.ttl = ttl
        self.verbose = verbose

    def send_response(self, questions, answers, authorities, additionals, aa):
        """Send a response message into the socket containing the provided question,
        answers, authorities and additional sections.

        Args:
            questions ([Question]): the question section.
            answers ([ResourceRecord]): the answer section.
            authorities ([ResourceRecord]): the authority section.
            additionals ([ResourceRecord]): the additional section.
            aa (Bool): flag indicating an authorative answer.
        """
        header = Header(self.query.header.ident, 0, 1, len(answers), len(authorities),
            len(additionals))
        header.qr, header.opcode, header.ra, header.aa = 1, 0, 1, 1 if aa else 0
        header.rd = self.query.header.rd
        response = Message(header, [questions[0]], answers, authorities, additionals)

        try:
            self.sock.sendto(response.to_bytes(), self.address)
            vprint(";; {}: Authorative response send to {}".format(
                self.query.header.ident, self.address), self.verbose and aa)
            vprint(";; {}: Response send to {}".format(self.query.header.ident,
                self.address), self.verbose and not aa)
        except socket.error:
            vprint(";; {}: Error sending response.".format(self.query.header.ident,
                self.verbose))

    def check_zone_for_answer(self, hostname):
        """Check the zonefile for an answer.

        Args:
            hostname (str): the hostname being queried

        Returns:
            (str, [ResourceRecord]): (hostname, answers)
        """
        answers = []
        record_set = self.zone.lookup(hostname, Type.CNAME)
        while record_set:
            answers = answers + record_set
            hostname = str(record_set[0].rdata)
            record_set = self.zone.lookup(hostname, Type.CNAME)

        answers = answers + self.zone.lookup(hostname, Type.A)
        return (hostname, answers)

    def check_zone_for_hints(self, hostname):
        """Check the zonefile for name server hints.

        Args:
            hostname (str): the hostname to resolve

        Returns:
            ([ResourceRecord], [ResourceRecord]): (authorities, additionals)
        """
        name = Name(hostname)
        for level in reversed(range(1, len(name.labels) + 1)):
            # Find all nameservers for the top n levels of the domain name.
            domain = name.domain_name(level)
            authorities = self.zone.lookup(str(domain), Type.NS)
            additionals = []

            # For each nameserver add its found IP addresses in the zonefile to the
            # additional section.
            name_servers = [str(record.rdata) for record in authorities]
            for name_server in name_servers:
                additionals = additionals + self.zone.lookup(name_server, Type.A)

            if authorities:
                return authorities, additionals

        # No name servers in zonefile found:
        return [], []

    def run(self):
        """ Run the handler thread"""
        hostname = str(self.query.questions[0].qname)
        vprint(";; {}: Query for domain name {}".format(self.query.header.ident,
            hostname), self.verbose)

        hostname, answers = self.check_zone_for_answer(hostname)
        authorities, additionals = self.check_zone_for_hints(hostname)
        if answers or authorities or additionals:
            self.send_response(self.query.questions, answers, authorities,
                additionals, True)


class Server:
    """A recursive DNS server"""

    def __init__(self, port, caching, ttl, verbose=False):
        """Initialize the server

        Args:
            port (int): port that server is listening on
            caching (bool): server uses resolver with caching if true
            ttl (int): ttl for records (if > 0) of cache
        """
        self.port = port
        self.caching = caching
        self.ttl = ttl
        self.verbose = verbose
        self.done = False
        self.zone = Zone()
        self.zone.read_master_file("zone")

    def receive_valid_query(self, sock):
        """Attempt to receive a valid DNS query, return None otherwise.

        Args:
            sock (socket): the socket to receive datagrams from
        Returns:
            (Message, str): the valid DNS query (if any) and the sender's address
        """
        try:
            data, address = sock.recvfrom(512)
            message = Message.from_bytes(data)
            if message.header.qr == 0 and message.header.opcode == 0 \
                    and message.header.qd_count > 0:
                return message, address
            else:
                return None, address
        except:
            return None, None

    def serve(self):
        """Start serving requests"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("localhost", self.port))
        sock.setblocking(0)

        while not self.done:
            query, address = self.receive_valid_query(sock)
            if query is not None:
                vprint(";; DNS query received (id {}), starting request handler."
                    .format(query.header.ident), self.verbose)
                handler = RequestHandler(query, sock, address, self.zone,
                    self.caching, self.ttl, self.verbose)
                handler.start()

        sock.close()

    def shutdown(self):
        """Shut the server down"""
        self.done = True
