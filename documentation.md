# Documentation
## Introduction
...

## File structure
...

## Implementation
...

### Resolver
...
1. Check the cache for an answer. For any CNAME record found add the _hostname_ to the list of aliases and change the current _hostname_ to the alias found in RDATA. When no more CNAME records are found lookup any A resource records corresponsing to the current _hostname_. If any A resource records were found return the answer, otherwise continue at step 2.
2. Check the cache for name server hints. Start matching down the labels in _hostname_, starting at the _hostname_ and moving up to the root, until any matching NS resource records are found. For these name servers lookup any matching A resource records and change the list of _hints_ to these new name servers. If no NS records were found at any domain level in the cache then use the root servers as initial _hints_. Root servers are initialized using the zone file root.
1. Select and remove the first name server in the list of _hints_ and send a query to this name server for the _hostname_. The header's QR, OPCODE and RD bits are all set to zero. This tells the receiving name server that the message is a standard query and that no recursion is desired.
2. Check whether the response message (if any) is valid. The response message is considered valid if the following conditions hold:
    * No unexpected error was encountered when sending or receiving datagrams. This includes timeout exceptions.
    
    The next conditions assume that a response message was successfully received:
    * The response packet has a RCODE of zero, indicating that no errors occurred.
    * The response packed has its QR bit set to 1, indicating that it is a response message.
    * The identification number of the response corresponds to the identification number defined in the query.
    * The question section in the response is equal to the question section defined in the query.

    The first two conditions ensure that the datagram was received without errors. The last three conditions ensure that the response is an answer to the question defined in the query. If the response was invalid continue at the next name server in the list of hints.
3. Two distinct cases are considered when a valid response has been received:
    1. The response contains an answer. In this case loop over all resource records found in the answer section. If the resource record is of type CNAME and its NAME field corresponds to the current FQDN: add the FQDN to the list of aliases and change the current FQDN to the domain name found in RDATA. If the resource record is of type A and its NAME field corresponds to the current FQDN: add the IP address found in RDATA to the list of IP addresses. Note that this does assume that CNAME records are listed before A records and that the CNAME records themselves are ordered.

### Cache
...

### Name server
...
