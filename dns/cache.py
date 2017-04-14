#!/usr/bin/env python3

"""A cache for resource records

This module contains a class which implements a cache for DNS resource records,
you still have to do most of the implementation. The module also provides a
class and a function for converting ResourceRecords from and to JSON strings.
It is highly recommended to use these.
"""

import json
from dns.resource import ResourceRecord

class RecordCache:
    """Cache for ResourceRecords"""

    def __init__(self):
        """Initialize the RecordCache"""
        self.records = {}

    def lookup(self, dname, type_, class_):
        """Lookup resource records in cache

        Lookup for the resource records for a domain name with a specific type and
        class.

        Args:
            dname (str): domain name
            type_ (Type): type
            class_ (Class): class
        Returns:
            [ResourceRecord): the list of resource records with dname, type_, class_
        """
        if not dname in self.records:
            return []

        # Remove all invalid records with dname.
        self.records[dname] = [record for record in self.records[dname]
            if record.is_valid()]
        if not self.records[dname]:
            del self.records[dname]
            return []

        # Return all (valid) resource records with dname, type_, class_.
        return [record for record in self.records[dname]
            if record.type_ == type_ and record.class_ == class_]

    def add_record(self, record, ttl=0):
        """Add a new Record to the cache

        Args:
            record (ResourceRecord): the record added to the cache
            ttl (int): TTL of cached entries (if > 0)
        """
        if ttl > 0:
            record.ttl = ttl
        if not str(record.name) in self.records:
            self.records[str(record.name)] = []

        # Check for and remove duplicate data (assume the new data is correct)
        self.records[str(record.name)] = [x for x in self.records[str(record.name)]
            if x.rdata != record.rdata]

        # Add the new record to the cache
        self.records[str(record.name)].append(record)

    def remove_record_set(self, dname):
        """Delete the record set for dname (for clearing up tests)

        Args:
            dname (str): domain name
        """
        if dname in self.records:
            del self.records[dname]

    def read_cache_file(self, filename):
        """Read the cache file from disk"""
        dcts = []
        try:
            with open(filename, "r") as file_:
                dcts = json.load(file_)
        except:
            print("could not read cachefile", filename)

        record_list = [ResourceRecord.from_dict(dct) for dct in dcts]
        self.records = {str(record.name) : [] for record in record_list}
        for record in record_list:
            self.records[str(record.name)].append(record)

    def write_cache_file(self, filename):
        """Write the cache file to disk"""
        dcts = []
        for key, record_set in self.records.items():
            dcts = dcts + [record.to_dict() for record in record_set]
        try:
            with open(filename, "w") as file_:
                json.dump(dcts, file_, indent=2)
        except:
            print("could not write cachefile", filename)

    def filter_cache(self):
        """Remove all invalid resource records"""
        for key, record_set in self.records.copy().items():
            self.records[key] = [record for record in record_set if record.is_valid()]
            if not self.records[key]:
                del self.records[key]

    def clear_cache(self):
        """Clear the cache"""
        self.records = {}
