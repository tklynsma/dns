#!/usr/bin/env python3

"""A recursive DNS server

This module provides a recursive DNS server. You will have to implement this
server using the algorithm described in section 4.3.2 of RFC 1034.
"""

import socket

from dns.classes import Class
from dns.message import Header, Message
from dns.name import Name
from dns.resolver import Resolver
from dns.resource import ResourceRecord, ARecordData, CNAMERecordData
from dns.rtypes import Type
from dns.util import vprint
from dns.zone import Zone
from threading import Thread


class RequestHandler(Thread):
    """A handler for requests to the DNS server"""

    def __init__(self, query, sock, address, zone, caching, ttl,
            verbose=False):
        """Initialize the handler thread"""
        super().__init__()
        self.daemon = True
        self.query = query
        self.id = query.header.ident
        self.sock = sock
        self.address = address
        self.zone = zone
        self.caching = caching
        self.ttl = ttl
        self.verbose = verbose

    def send_response(self, questions, answers, authorities, additionals, aa=False,
            rcode=0):
        """Send a response message into the socket containing the provided question,
        answers, authorities and additional sections.

        Args:
            questions ([Question]): the question section.
            answers ([ResourceRecord]): the answer section.
            authorities ([ResourceRecord]): the authority section.
            additionals ([ResourceRecord]): the additional section.
            aa (Bool): flag indicating an authorative answer.
            rcode (int): the response code
        """
        header = Header(self.id, 0, 1, len(answers), len(authorities),
            len(additionals))
        header.qr, header.opcode, header.ra = 1, 0, 1
        header.rd = self.query.header.rd
        header.aa = 1 if aa else 0
        header.rcode = rcode
        response = Message(header, [questions[0]], answers, authorities, additionals)

        try:
            self.sock.sendto(response.to_bytes(), self.address)
            vprint("Response send to {}, port {}, rcode = {}".format(self.address[0], 
                self.address[1], rcode), self.id, self.verbose)
        except socket.error:
            vprint("Error sending response.", self.id, self.verbose)

    def check_zone_for_answer(self, hostname):
        """Check the zonefile for an answer.

        Args:
            hostname (str): the hostname being queried

        Returns:
            (str, [ResourceRecord], [ResourceRecord]): (hostname, cnames, answers)
        """
        cnames = []
        record_set = self.zone.lookup(hostname, Type.CNAME)
        while record_set:
            cnames = cnames + record_set
            hostname = str(record_set[0].rdata)
            record_set = self.zone.lookup(hostname, Type.CNAME)

        answers = self.zone.lookup(hostname, Type.A)
        return (hostname, cnames, answers)

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

    def resolve(self, hostname):
        """Use the DNS resolver to answer the query.

        Args:
            hostname (str): the hostname to resolve
        """
        resolver = Resolver(2, self.caching, self.ttl, self.id)
        hostname, aliaslist, ipaddrlist = resolver.gethostbyname(hostname,
            verbose=self.verbose)
        aliaslist.append(hostname)
        cnames = [ResourceRecord(Name(aliaslist[i]), Type.CNAME, Class.IN, 60,
            CNAMERecordData(Name(aliaslist[i+1]))) for i in range(len(aliaslist)-1)]
        answers = [ResourceRecord(Name(hostname), Type.A, Class.IN, 60,
            ARecordData(address)) for address in ipaddrlist]
        if answers:
            self.send_response(self.query.questions, cnames + answers, [], [], [])
        else:
            vprint("Domain name does not exist", self.id, self.verbose)
            self.send_response(self.query.questions, [], [], [], rcode=3)

    def run(self):
        """ Run the handler thread"""
        # If the question's qtype if not of type A: send back a response with rcode 4
        # (not implemented)
        if self.query.questions[0].qtype != Type.A:
            vprint("Invalid query type.", self.id, self.verbose)
            self.send_response(self.query.questions, [], [], [], rcode=4)

        # Query is of type A:
        else:
            hostname = str(self.query.questions[0].qname)
            vprint("Query for domain: {}".format(hostname), self.id, self.verbose)
            hostname, cnames, answers = self.check_zone_for_answer(hostname)
            authorities, additionals = self.check_zone_for_hints(hostname)

            # If an answer was found in the zonefile return an authorative answer.
            if answers:
                vprint("Answer found in zonefile.", self.id, self.verbose)
                self.send_response(self.query.questions, cnames + answers,
                    authorities, additionals, aa=True)

            else:
                vprint("No answer found in zonefile.", self.id, self.verbose)

                # Recursion is not desired:
                if self.query.header.rd == 0:
                    # If other records were found in the zonefile return an
                    # authorative answer.
                    if cnames or authorities or additionals:
                        vprint("Authorative response.", self.id, self.verbose)
                        self.send_response(self.query.questions, cnames + answers,
                            authorities, additionals)

                    # If no records were found send back a response with rcode 5
                    # (refused)
                    else:
                        vprint("No records in zonefile, query refused.", self.id, 
                            self.verbose)
                        self.send_response(self.query.questions, [], [], [], rcode=5)

                # Recursion is desired:
                else:
                    vprint("Recursion desired, starting resolver.", self.id,
                        self.verbose)
                    self.resolve(hostname)


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

    def is_valid_query(self, query):
        """Check whether the query is a valid DNS query of qtype A.

        Args:
            query (Message): the received query
        Returns:
            Bool: true iff the query is a valid DNS query.
        """
        return query.header.qr == 0 \
            and query.header.opcode == 0 \
            and query.header.qd_count > 0

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
            if self.is_valid_query(message):
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
        vprint("Server started", 99999, self.verbose)

        while not self.done:
            query, address = self.receive_valid_query(sock)
            if query is not None:
                vprint("Valid DNS query received, starting request handler.",
                    query.header.ident, self.verbose)
                handler = RequestHandler(query, sock, address, self.zone,
                    self.caching, self.ttl, self.verbose)
                handler.start()

        sock.close()

    def shutdown(self):
        """Shut the server down"""
        self.done = True
