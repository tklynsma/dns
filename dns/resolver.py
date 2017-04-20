#!/usr/bin/env python3

"""DNS Resolver

This module contains a class for resolving hostnames. You will have to implement
things in this module. This resolver will be both used by the DNS client and the
DNS server, but with a different list of servers.
"""

import socket

from dns.cache import RecordCache
from dns.classes import Class
from dns.message import Message, Question, Header
from dns.name import Name
from dns.rtypes import Type
from dns.rcodes import RCode
from dns.util import vprint
from dns.zone import Zone
from enum import Enum


def initialize_root_servers():
    """Initialize root server IP addresses from the root hints zone file

    Returns:
        [str]: the list of root IP addresses
    """
    zone = Zone()
    zone.read_master_file("root")
    nameservers = [str(record.rdata) for record in zone.records['.']]
    return [str(zone.records[nameserver][0].rdata) for nameserver in nameservers]

def initialize_cache():
    """Load the cache from the cachefile and remove any invalid records"""
    cache = RecordCache()
    cache.read_cache_file("cache")
    cache.filter_cache()
    return cache


class Resolver:
    """DNS resolver"""
    root_servers = initialize_root_servers()
    cache = initialize_cache()

    def __init__(self, timeout, caching, ttl, ident=9001):
        """Initialize the resolver

        Args:
            caching (bool): caching is enabled if True
            ttl (int): ttl of cache entries (if > 0)
        """
        self.timeout = timeout
        self.caching = caching
        self.ttl = ttl
        self.ident = ident

    def __del__(self):
        """Write cache contents to cache file on deletion."""
        if self.caching:
            self.cache.write_cache_file("cache")

    def send_and_receive_query(self, sock, hostname, nameserver):
        """ Create and send a query into the socket and receive a response.
        
        Args:
            sock(socket): the socket to send the datagram into
            hostname(str): the hostname to resolve
            nameserver(str): the nameserver to send the query to

        Returns:
            (Message, Message): the query and response messages
        """
        question = Question(Name(hostname), Type.A, Class.IN)
        header = Header(self.ident, 0, 1, 0, 0, 0)
        header.qr, header.opcode, header.rd = 0, 0, 0
        query = Message(header, [question])
        try:
            sock.sendto(query.to_bytes(), (nameserver, 53))
            response = Message.from_bytes(sock.recv(512))
            return query, response
        except:
            return query, None

    def is_valid_response(self, query, response):
        """ Check whether the response is a valid response to the query.

        Args:
            query(Message): the send query message
            response(Message): the received response message
        Returns:
            Bool: true iff the response is a valid response to the query
        """
        return response is not None \
            and response.header.qr == 1 \
            and response.header.rcode == RCode.NoError \
            and query.header.ident == response.header.ident \
            and query.questions == response.questions

    def get_name_servers(self, response):
        """ Extract all name servers from the response and Check 
        the additional section for any nameserver IP addresses.

        Args:
            response(Message): the received response message
        Returns:
            [str]: a list containing all found name servers
        """
        # Find all name servers contained in NS records.
        name_servers = []
        for record in response.authorities:
            if record.type_ == Type.NS:
                name_servers.append(str(record.rdata))

                # Add the NS record to cache if caching is enabled.
                if self.caching:
                    self.cache.add_record(record, self.ttl)

        # Replace any name servers with their IP address if an A
        # resource record is found in the additional section and
        # move them to the front of the list (prefer nameservers
        # whose IP address is known).
        for record in reversed(response.additionals):
            if record.type_ == Type.A:
                try:
                    index = name_servers.index(str(record.name))
                    name_servers[index] = str(record.rdata)
                    name_servers.insert(0, name_servers.pop(index))
                except ValueError: pass

                # Add the A record to cache if caching is enabled.
                if self.caching:
                    self.cache.add_record(record, self.ttl)

        return name_servers

    def get_answers(self, response, hostname, aliaslist):
        """Obtain all relevant answers from the answer section and
        add them to the cache if caching is enabled.

        Args:
            answers [ResourceRecord]: the answer section
            hostname (str): the hostname to resolve
            aliaslist [str]: the list of alias domain names

        Returns:
            (str, [str], [str]): (hostname, aliaslist, ipaddrlist)
        """
        ipaddrlist = []
        for answer in response.answers:
            if hostname == str(answer.name):
                if answer.type_ == Type.CNAME:
                    aliaslist.append(hostname)
                    hostname = str(answer.rdata)
                    vprint(";; Found alias in response: {}".format(hostname),
                        self.verbose)
                elif answer.type_ == Type.A:
                    ipaddrlist.append(str(answer.rdata))

                # Add the record to cache if caching is enabled.
                if self.caching:
                    self.cache.add_record(answer, self.ttl)

        return (hostname, aliaslist, ipaddrlist)

    def check_cache_for_answer(self, hostname, aliaslist):
        """Check the cache for an answer.

        Args:
            hostname (str): the hostname to resolve

        Returns:
            (str, [str], [str]): (hostname, aliaslist, ipaddrlist)
        """
        record_set = self.cache.lookup(hostname, Type.CNAME, Class.IN)
        while record_set:
            aliaslist.append(hostname)
            hostname = str(record_set[0].rdata)
            vprint(";; Found alias in cache: {}".format(hostname), self.verbose)
            record_set = self.cache.lookup(hostname, Type.CNAME, Class.IN)

        record_set = self.cache.lookup(hostname, Type.A, Class.IN)
        ipaddrlist = [str(record.rdata) for record in record_set]
        return (hostname, aliaslist, ipaddrlist)

    def check_cache_for_hints(self, hostname):
        """Find the highest domain level name server hints in the cache for the
        given hostname.

        Args:
            hostname (str): the hostname to resolve

        Returns:
            [str]: a list containing the found name servers
        """
        name = Name(hostname)
        for level in reversed(range(1, len(name.labels) + 1)):
            # Find all nameservers for the top n levels of the domain name.
            domain = name.domain_name(level)
            record_set = self.cache.lookup(domain, Type.NS, Class.IN)
            name_servers = [str(record.rdata) for record in record_set]
            hints = []

            # For each nameserver add its IP address to the list of hints
            # if found in the cache, otherwise add the name server.
            for name_server in reversed(name_servers):
                record_set = self.cache.lookup(name_server, Type.A, Class.IN)
                ipaddrlist = [str(record.rdata) for record in record_set]
                if ipaddrlist:
                    hints = ipaddrlist + hints
                else:
                    hints.append(name_server)

            # Return the found name server addresses (if any), otherwise start
            # searching for name servers one domain level higher.
            if hints:
                vprint(";; Found hints in cache for domain: {}".format(domain),
                    self.verbose)
                return hints

        # No name servers in cache found:
        return []

    def gethostbyname(self, hostname, verbose=False):
        """Translate a host name to IPv4 address.

        Args:
            hostname (str): the hostname to resolve

        Returns:
            (str, [str], [str]): (hostname, aliaslist, ipaddrlist)
        """
        self.verbose = verbose
        hostname = str(Name(hostname))
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)
        result = self._gethostbyname(sock, hostname, self.root_servers.copy(), [])
        sock.close()
        return result

    def _gethostbyname(self, sock, hostname, hints, aliaslist):
        """Translate a host name to IPv4 address.

        Args:
            sock (Socket): the socket to send datagrams into
            hostname (str): the hostname to resolve
            hints [str]: the list of initial nameserver hints
            aliaslist [str]: the list of alias domain names

        Returns:
            (str, [str], [str]): (hostname, aliaslist, ipaddrlist)
        """

        # Consult the cache if caching is enabled:
        if self.caching:
            # Check the cache for an answer.
            hostname, aliaslist, ipaddrlist = self.check_cache_for_answer(hostname,
                aliaslist)
            if ipaddrlist:
                # Result found in cache:
                vprint(";; Found answer in cache:", self.verbose)
                return hostname, aliaslist, ipaddrlist

            # Check the cache for name server hints.
            name_servers = self.check_cache_for_hints(hostname)
            if name_servers:
                hints = name_servers

        while hints:
            name_server = hints.pop(0)
            vprint(";; Quering nameserver {}".format(name_server), self.verbose)
            query, response = self.send_and_receive_query(sock, hostname, name_server)
            if self.is_valid_response(query, response):

                # The response contains an answer:
                if len(response.answers) > 0:
                    # Get the data from the answer section.
                    hostname, aliaslist, ipaddrlist = self.get_answers(
                        response, hostname, aliaslist)

                    # The answer contains an IP address:
                    if ipaddrlist:
                        # Return the answer.
                        vprint(";; Found answer in response:", self.verbose)
                        return hostname, aliaslist, ipaddrlist

                    # The answer does not contain an IP address:
                    else:
                        # Start a new query to the hostname found in the CNAME record 
                        # using any additional nameservers found in the authority 
                        # section as initial hints.
                        hints = self.get_name_servers(response) + self.root_servers.copy()
                        return self._gethostbyname(sock, hostname, hints, aliaslist)

                # The response does not contain an answer:
                else: 
                    # Update the hints with the NS records found in the authority
                    # section.
                    hints = self.get_name_servers(response) + hints

        # Exhausted all hints.
        return hostname, [], []
