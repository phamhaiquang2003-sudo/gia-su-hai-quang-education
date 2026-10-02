"""Find the IPv4 address used for the default route, without sending traffic."""

import socket


try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
        connection.connect(("1.1.1.1", 80))
        print(connection.getsockname()[0])
except OSError:
    print("127.0.0.1")
