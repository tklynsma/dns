# Documentation
## Description
This document describes the implemented DNS resolver, cache and name server. The provided framework was used for the project, which already provided classes for manipulating DNS messages and converting them to and from bytes.

## Usage
Usage is as described in the assignment. In addition a "verbose" output option has been added to both dns_client.py and dns_server.py. To use this add the parameter ```-v``` or ```--verbose```.

The server, when running in its default settings (_localhost_ using port 5353), was tested using the following _dig_ command:

```
$ dig @localhost hostname -p 5353 +noedns [+norec]
```

_nslookup_ with the correct settings for server and port should work as well.

## Resolver
Name resolution roughly follows the algorithm described in [Section 5.3.3 of RFC 1034](https://tools.ietf.org/html/rfc1034##section-5.3.3). At creation, the list of root servers is initialized using the zone file _root_ (see [root hints](https://www.internic.net/domain/named.root)). The cache is read from the json cachefile _cache_. The cache is shared between _all_ resolver instances and written back to the cachefile at deletion.

#### Consulting the cache
When caching is enabled the resolver will first attempt to resolve the _hostname_ using the cache:

1. Check the cache for _CNAME_ resource records matching the _hostname_. While there is still a valid _CNAME_ record to be found in the cache: add the _hostname_ to the _aliaslist_ and change the current _hostname_ to the canonical name found in _rdata_.

2. Check the cache for _A_ resource records matching the _hostname_. If any were found return the answer; otherwise continue at the next step.

2. Check the cache for _NS_ resource records. Start matching down the labels in _hostname_, starting at _hostname_ and moving up to (but excluding) the root, until any matching _NS_ resource records are found. If found; lookup matching _A_ resource records, change the list of _hints_ to the found name servers and start an iterative query for the _hostname_.

#### Building an iterative query
If the cache was unsuccesful in resolving the _hostname_ or caching was disabled the resolver will build an iterative query:

1. Select and remove the first name server in the list of _hints_ and send a query for the _hostname_. The header's _QR_, _OPCODE_ and _RD_ bits are all set to zero. This tells the receiving name server that the message is a standard query and that no recursion is desired. If the list of _hints_ is empty go to step 5.

2. Check whether the response message (if any) is valid. The response is considered valid if the following conditions hold:
    * No unexpected error was encountered when sending or receiving datagrams. This includes timeout exceptions.
    * The response has a _RCODE_ of zero, indicating that no errors occurred.
    * The response has its _QR_ bit set to 1, indicating that it is a response message.
    * The identification number of the response corresponds to the identification number defined in the query.
    * The question section in the response is equal to the question section defined in the query.

    The first two conditions ensure that the datagram was received without errors. The last three conditions ensure that the response is an answer to the question defined in the query. This also guarantees that concurrent queries are handled correctly. If the response was invalid continue at the next name server in the list of hints (go back to step 1).

3. If the response contains an answer: Loop over all resource records found in the answer section. If the resource record is of type _CNAME_ add the _hostname_ to _aliaslist_ and change the current _hostname_ to the domain name found in _rdata_. If the resource record is of type _A_ add the IP address found in _rdata_ to the list of IP addresses. If any _A_ resource records were found return the answer. Otherwise, start a new query to the (new) _hostname_ using any additional name servers found in the authority and additional section as additional initial hints.

4. If the response contains no answers: Check the authority and additional sections for name server hints and for each server add its IP address (or if no corresponsing _A_ resource record is found: its domain name) to the start of the list of _hints_. Name servers with a provided IP address in the additional section are preferred over name servers without an IP address. Go back to step 1.

5. When the list of hints is exhausted and no answer is found: output the hostname and empty lists for the aliases and IP addresses.

## Cache
For efficient lookup the cache is implemented as a dictionary; with domain names as keys and lists of resource records as values. The cachefile is read from and stored on disk using _json_ format. The cache is also guarded against concurrent access.

To remove expired records a timestamp is associated with each resource record. Expired resource records are removed from the cache if the following condition is _false_:

```
self.timestamp + self.ttl > time.time()
```

When the cache file is first initialized _all_ resource records for which this condition does not hold are filtered from the cache. Thereafter this condition is only checked when doing a lookup: all resource records for _dname_ for which the condition does not hold are filtered from the cache before returning the result.

## Name server
The name server roughly follows the algorithm described in [Section 4.3.2 of RFC 1034](https://tools.ietf.org/html/rfc1034#section-4.3.2), omitting step 3.b. At creation, it will initialize its zonefile _zone_ and bind its UDP socket to _localhost_ and the indicated port number. When starting the DNS server using dns_server.py the default port is set to 5353.

### Server
The server listens for incoming datagrams and, if the datagram is a valid DNS query it will start a new thread to concurrently handle the request. A datagram is considered a valid DNS query if:
*   No errors occurred while parsing the message from bytes.
*   The message's _OPCODE_ is equal to zero, indicating a standard query.
*   The message's _QR_ bit is set to zero, indicating a query.
*   The message contains at least one resource record in its question section.

If any of these conditions fail then the datagram is simply ignored.

### Request handler
Each request handler runs in a separate thread, resolves the query and sends a response back to the datagram's source address. Concurrency is ensured by protecting the cache against concurrent access and by matching responses in the resolver to their DNS transaction ID. When sending a response the handler sets the header's _QR_ and _RA_ bits to 1, meaning the message is  a response and recursion is available on the server. The header's _RD_ bit is copied from the query and the _AA_ bit is set in case of an authorative response.

First, the handler checks whether the question's _QTYPE_ is of type _A_. If not, an empty response is send back with _RCODE_ 4 (not implemented). Otherwise, the handler will continue by consulting its _zone_:

1. Check the _zone_ for _CNAME_ resource records matching the _hostname_. While there is still a valid _CNAME_ record to be found in the _zone_: add the record to the list of _cnames_ and change the current _hostname_ to the canonical name found in _rdata_.

2. Check the _zone_ for _A_ resource records matching the _hostname_ and save these records in _answers_.

3. Check the _zone_ for _NS_ resource records. Start matching down the labels in _hostname_, starting at _hostname_ and moving up to (but excluding) the root, until any matching _NS_ resource records are found. If found; lookup matching _A_ resource records in the _zone_.

4. If _answers_ is non-empty: return an authorative response to the datagram's source address containing all found records.

The next steps depend on whether the query has its _RD_ bit set or not. If no recursion is desired the request handler executes the following steps:

1. If any _CNAME_ or _NS_ records were found in the _zone_ then send back an authorative response to the datagram's source address containing all found records.

2. If no records were found the _hostname_ points outside of the server's _zone_. An empty response is send back with _RCODE_ 5 (refused).

If it cannot find an answer using _zone_ resolution and recursion is desired, then the resolver is used to answer the query. When solving a recursive query the resolver will use the same transaction ID as the original query. If the resolver finds an answer it is send back to the datagram's source address. If not, an empty response is send back with RCODE 3 (name error).