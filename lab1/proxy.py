# 50.012 network lab 1
import socket
from socket import *
import sys, os
import _thread as thread

proxy_port = 8079
cache_directory = "./cache/"


def client_thread(client_facing_socket):
    client_facing_socket.settimeout(5.0)

    try:
        message = client_facing_socket.recv(4096).decode()
        msg_elements = message.split()

        if len(msg_elements) < 5 or msg_elements[0].upper() != 'GET' or 'Range:' in msg_elements:
            # print("non-supported request: " , msg_elements)
            client_facing_socket.close()
            return

        # Extract the following info from the received message
        #   webServer: the web server's host name
        #   resource: the web resource requested
        #   file_to_use: a valid file name to cache the requested resource
        #   Assume the HTTP reques is in the format of:
        #      GET http://www.mit.edu/ HTTP/1.1\r\n
        #      Host: www.mit.edu\r\n
        #      User-Agent: .....
        #      Accept:  ......

        resource = msg_elements[1].replace("http://", "", 1)

        host_header_index = msg_elements.index('Host:')
        web_server = msg_elements[host_header_index + 1]

        port = 80

        print("webServer:", web_server)
        print("resource:", resource)

        message = message.replace("Connection: keep-alive", "Connection: close")

        website_directory = cache_directory + web_server.replace("/", ".") + "/"

        if not os.path.exists(website_directory):
            os.makedirs(website_directory)

        file_to_use = website_directory + resource.replace("/", ".")
    except:
        print("exception caught when receiving from client facing socket: ")
        print(str(sys.exc_info()[0]))
        client_facing_socket.close()
        return

    # Check whether the file exists in the cache
    try:
        if os.path.exists(file_to_use):
            print("cache hit")
            with open(file_to_use, "rb") as f:
                # ProxyServer finds a cache hit and generates a response message
                print("  served from the cache")
                while True:
                    buff = f.read(4096)
                    if buff:
                        client_facing_socket.send(buff)
                    else:
                        break
        else:
            print("cache NOT hit")
            # Create a socket on the proxy server
            server_facing_socket = socket(AF_INET, SOCK_STREAM)  # Fill in start             # Fill in end
            # Connect to the socket to port 80
            # Fill in start
            print("  sending to web server...")
            server_facing_socket.connect((web_server, port))
            server_facing_socket.sendall(message.encode())
            # Fill in end
            with open(file_to_use, "wb") as cacheFile:
                while True:
                    print("  receiving and writing cache...")
                    buff = server_facing_socket.recv(4096)  # Fill in start
                    cacheFile.write(buff)
                    # Fill in end
                    if buff:
                        print("    sending to browser...")
                        client_facing_socket.send(buff)
                    else:
                        client_facing_socket.close()
                        server_facing_socket.close()
                        break
    except:
        print(str(sys.exc_info()[0]))


if len(sys.argv) > 2:
    print('Usage : "python proxy.py port_number"\n')
    sys.exit(2)
if len(sys.argv) == 2:
    proxy_port = int(sys.argv[1])

if not os.path.exists(cache_directory):
    os.makedirs(cache_directory)

# Create a server socket, bind it to a port and start listening
welcomeSocket = socket(AF_INET, SOCK_STREAM)
# Fill in start
welcomeSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)  # fix linux bug
welcomeSocket.bind(('', proxy_port))
welcomeSocket.listen(10)
# Fill in end


print('Proxy ready to serve at port', proxy_port)

try:
    while True:
        # Start receiving data from the client
        inSocket, addr = welcomeSocket.accept()  # Fill in start             # Fill in end
        print('Received a connection from:', addr)

        # the following function starts a new thread, taking the function name as the first argument, and a tuple of
        # arguments to the function as its second argument
        thread.start_new_thread(client_thread, (inSocket,))

except KeyboardInterrupt:
    print('bye...')

finally:
    welcomeSocket.shutdown(SHUT_RDWR)
    welcomeSocket.close()
# Fill in start             # Fill in end
