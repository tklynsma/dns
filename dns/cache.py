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

    def __init__(self, ttl):
        """Initialize the RecordCache

        Args:
            ttl (int): TTL of cached entries (if > 0)
        """
        self.records = {}
        self.ttl = ttl

    def lookup(self, dname, type_, class_):
        """Lookup resource records in cache

        Lookup for the resource records for a domain name with a specific type and class.

        Args:
            dname (str): domain name
            type_ (Type): type
            class_ (Class): class
        Returns:
            [ResourceRecord): the list of resource records with dname, type_, class_
        """
        if not dname in self.records:
            return []

        self.records[dname] = list(filter(lambda x : x.is_valid(), self.records[dname]))
        if not self.records[dname]:
            del self.records[dname]
            return []

        return list(filter(lambda x : x.type_ == type_ and x.class_ == class_,
            self.records[dname]))

    def add_record(self, record):
        """Add a new Record to the cache

        Args:
            record (ResourceRecord): the record added to the cache
        """
        if self.ttl > 0:
            record.ttl = self.ttl
        if not str(record.name) in self.records:
            self.records[str(record.name)] = []
        self.records[str(record.name)].append(record)

    def read_cache_file(self, filename):
        """Read the cache file from disk
        
        Args:
            filename (str): path of the read filename
        """
        dcts = []
        try:
            with open(filename, "r") as file_:
                dcts = json.load(file_)
        except:
            print("could not read cache", filename)

        record_list = [ResourceRecord.from_dict(dct) for dct in dcts]
        self.records = {str(record.name) : [] for record in record_list}
        for record in record_list:
            self.records[str(record.name)].append(record)

    def write_cache_file(self, filename):
        """Write the cache file to disk
        
        Args:
            filename (str): path of the filename written to
        """
        dcts = []
        for key, record_set in self.records.items():
            dcts = dcts + [record.to_dict() for record in record_set]
        try:
            with open(filename, "w") as file_:
                json.dump(dcts, file_, indent=2)
        except:
            print("could not write cache", filename)

    def filter_cache(self):
        """Remove all invalid resource records"""
        for key, record_set in self.records.copy().items():
            self.records[key] = list(filter(lambda x : x.is_valid(), record_set))
            if not self.records[key]:
                del self.records[key]

    def clear_cache(self):
        """Clear the cache"""
        self.records = {}
