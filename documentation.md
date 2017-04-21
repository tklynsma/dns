# Documentation
## Introduction
...

## File structure
...

## Implementation
...

### Resolver
...

1. Select and remove the first name server in the list of _hints_ and send a query to this name server for the _hostname_. The header's QR, OPCODE and RD bits are all set to zero. This tells the receiving name server that the message is a standard query and that no recursion is desired.
2. Check whether the response message (if any) is valid. The response message is considered valid if the following conditions hold:
    * No unexpected error was encountered when sending or receiving datagrams. This includes timeout exceptions.
    * The response packet has a RCODE of zero, indicating that no errors occurred.
    * The response packed has its QR bit set to 1, indicating that it is a response message.
    * The identification number of the response corresponds to the identification number defined in the query.
    * The question section in the response is equal to the question section defined in the query.

    The first two conditions ensure that the datagram was received without errors. The last three conditions ensure that the response is an answer to the question defined in the query. If the response was invalid continue at the next name server in the list of hints.
3. ...

### Cache
...

### Name server
...
