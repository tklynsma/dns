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
from dns.rtypes import Type
from dns.rcodes import RCode
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


class Resolver:
    """DNS resolver"""
    root_servers = initialize_root_servers()

    def __init__(self, timeout, caching, ttl):
        """Initialize the resolver

        Args:
            caching (bool): caching is enabled if True
            ttl (int): ttl of cache entries (if > 0)
        """
        self.timeout = timeout
        self.caching = caching
        self.ttl = ttl

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
        header = Header(9001, 0, 1, 0, 0, 0)
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

        # Replace any name servers with their IP address if an A
        # resource record is found in the additional section and
        # move them to the front of the list (prefer nameservers
        # whose IP address is known).
        for record in response.additionals:
            if record.type_ == Type.A:
                try:
                    index = name_servers.index(str(record.name))
                    name_servers[index] = str(record.rdata)
                    name_servers.insert(0, name_servers.pop(index))
                except ValueError: pass

        return name_servers

    def gethostbyname(self, hostname):
        """Translate a host name to IPv4 address.

        Args:
            hostname (str): the hostname to resolve

        Returns:
            (str, [str], [str]): (hostname, aliaslist, ipaddrlist)
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)
        result = self._gethostbyname(sock, hostname, self.root_servers, [])
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

        while hints:
            query, response = self.send_and_receive_query(sock, hostname, hints.pop(0))
            if self.is_valid_response(query, response):

                # The response contains an answer:
                if len(response.answers) > 0:
                    ipaddrlist = []

                    # Get the data from the answer section.
                    for answer in response.answers:
                        if answer.type_ == Type.CNAME:
                            if hostname == str(answer.name).rstrip('.'):
                                aliaslist.append(hostname)
                                hostname = str(answer.rdata).rstrip('.')
                        elif answer.type_ == Type.A:
                            if hostname == str(answer.name).rstrip('.'):
                                ipaddrlist.append(str(answer.rdata))

                    # The answer contains an IP address:
                    if ipaddrlist:
                        # Return the answer.
                        return hostname, aliaslist, ipaddrlist

                    # The answer does not contain an IP address:
                    else:
                        # Start a new query to the hostname found in the CNAME record 
                        # using any additional nameservers found in the authority 
                        # section as initial hints.
                        hints = self.get_name_servers(response) + self.root_servers
                        return self._gethostbyname(sock, hostname, hints, aliaslist)

                # The response does not contain an answer:
                else: 
                    # Update the hints with the NS records found in the authority section.
                    hints = self.get_name_servers(response) + hints

        # Exhausted all hints.
        return hostname, [], []
