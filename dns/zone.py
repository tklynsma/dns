#!/usr/bin/env python3

"""Zones of domain name space

See section 6.1.2 of RFC 1035 and section 4.2 of RFC 1034.
Instead of tree structures we simply use dictionaries from domain names to
zones or record sets.

These classes are merely a suggestion, feel free to use something else.
"""

from dns.classes import Class
from dns.name import Name
from dns.resource import ResourceRecord, ARecordData, CNAMERecordData, NSRecordData
from dns.rtypes import Type


class Catalog:
    """A catalog of zones"""

    def __init__(self):
        """Initialize the catalog"""
        self.zones = {}

    def add_zone(self, name, zone):
        """Add a new zone to the catalog

        Args:
            name (str): root domain name
            zone (Zone): zone
        """
        self.zones[name] = zone


class Zone:
    """A zone in the domain name space"""

    def __init__(self):
        """Initialize the Zone """
        self.records = {}

    def lookup(self, dname, type_):
        """Lookup resource records in the zone for a domain name with a specific type.

        Args:
            dname (str): domain name
            type_ (Type): type
        Returns:
            [ResourceRecord): the list of resource records with dname and type_
        """
        if not dname in self.records:
            return []
        return [record for record in self.records[dname] if record.type_ == type_]

    def add_node(self, name, record_set):
        """Add a record set to the zone

        Args:
            name (str): domain name
            record_set ([ResourceRecord]): resource records
        """
        self.records[name] = record_set

    def read_master_file(self, filename):
        """Read the zone from a master file

        See section 5 of RFC 1035.

        Args:
            filename (str): the filename of the master file
        """
        lines = []
        with open(filename, "r") as zonefile:
            lines = zonefile.readlines()
            lines = list(map(lambda x : x.split(';', 1)[0], lines))
            lines = list(filter(lambda x : x != "" and x != "\n", lines))
            lines = list(map(lambda x : x.split(), lines))

        self.records = {line[0] : [] for line in lines}

        for line in lines:
            name, ttl, type_, data = tuple(line)
            if type_ == 'A':
                rdata = ARecordData(data)
                record = ResourceRecord(Name(name), Type.A, Class.IN, int(ttl), rdata)
                self.records[name].append(record)
            elif type_ == 'CNAME':
                rdata = CNAMERecordData(Name(data))
                record = ResourceRecord(Name(name), Type.CNAME, Class.IN, int(ttl),
                    rdata)
                self.records[name].append(record)
            elif type_ == 'NS':
                rdata = NSRecordData(Name(data))
                record = ResourceRecord(Name(name), Type.NS, Class.IN, int(ttl),
                    rdata)
                self.records[name].append(record)
