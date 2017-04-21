# Documentation
## Introduction
...

## File structure
...

## Resolver
Name resolution of roughly follows the algorithm described in [Section 5.3.3 of RFC 1034](https://tools.ietf.org/html/rfc1034##section-5.3.3). At creation, the list of root servers is initialized using the zone file _root_ (see [root hints](https://www.internic.net/domain/named.root)). The cache is read from the json cachefile _cache_. The cache is shared between _all_ resolver instances and written back to the cachefile at deletion.

#### Consulting the cache
When caching is enabled the resolver will first attempt to resolve the _hostname_ using the cache:
1. Check the cache for _CNAME_ resource records matching the _hostname_. While there is still a valid _CNAME_ record to be found in the cache: add the _hostname_ to the _aliaslist_ and change the current _hostname_ to the canonical name found in _rdata_.
2. Check the cache for _A_ resource records matching the _hostname_. If any were found return the answer; otherwise continue at the next step.
2. Check the cache for _NS_ resource records. Start matching down the labels in _hostname_, starting at _hostname_ and moving up to (but excluding) the root, until any matching _NS_ resource records are found. If found; lookup any matching _A_ resource records, change the list of _hints_ to the found name servers and start an iterative query for the _hostname_.

#### Building an iterative query
If the cache was unsuccesful in resolving the _hostname_ or caching was disabled the resolver will build an iterative query:

1. Select and remove the first name server in the list of _hints_ and send it a query for the _hostname_. The header's _QR_, _OPCODE_ and _RD_ bits are all set to zero. This tells the receiving name server that the message is a standard query and that no recursion is desired.
2. Check whether the response message (if any) is valid. The response is considered valid if the following conditions hold:
    * No unexpected error was encountered when sending or receiving datagrams. This includes timeout exceptions.
    * The response has a _RCODE_ of zero, indicating that no errors occurred.
    * The response has its _QR_ bit set to 1, indicating that it is a response message.
    * The identification number of the response corresponds to the identification number defined in the query.
    * The question section in the response is equal to the question section defined in the query.

    The first two conditions ensure that the datagram was received without errors. The last three conditions ensure that the response is an answer to the question defined in the query. This also guarantees that concurrent queries are handled correctly. If the response was invalid continue at the next name server in the list of hints (go back to step 3).
3. Two distinct cases are considered when a valid response has been received:
    1. The response contains an answer. In this case loop over all resource records found in the answer section. If the resource record is of type _CNAME_ and its _NAME_ field corresponds to the current _hostname_: add the _hostname_ to the list of aliases and change the current _hostname_ to the domain name found in _RDATA_. If the resource record is of type _A_ and its _NAME_ field corresponds to the current _hostname_: add the IP address found in _RDATA_ to the list of IP addresses. Note that this does assume that _CNAME_ records are listed before _A_ records and that the _CNAME_ records themselves are ordered.

        If any _A_ resource records were found then return the resulting host name, alias list and IP address list. If only _CNAME_ resource record(s) were found then start a new query to the new _hostname_ using any additional name servers found in the authority and additional sections as initial hints. In addition append the root server hints in case the provided name server hints fail or they are absent. Go back to step 3.
    2. The response has an empty answer section. In this case check the authority and additional section for any _NS_ and _A_ resource records and if found, add their IP addresses (or if no corresponding A resource record is found in the additional section, their domain names) at the start of the list of hints. Name servers with a provided IP address in the additional section are preferred over name servers without an IP address. Go back to step 3.
6. When the list of hints is exhausted and no answer is found: output the hostname and empty lists for the aliases and IP addresses.

## Cache
For efficient lookup the cache is implemented as a dictionary; with domain names as keys. 

## Name server
...
