import socket

def ftp_send(filename,host,port):
    BUFFER_SIZE = 4096 # send 4096 bytes each time step

    # create the client socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    print(f"[+] Connecting to {host}:{port}")
    s.connect((host, port))
    print("[+] Connected.")

    # send the filename and filesize
    # s.send(f"{filename}{SEPARATOR}{filesize}".encode())

    # start sending the file
    with open(filename, "rb") as f:
        while True:
            # read the bytes from the file
            bytes_read = f.read(BUFFER_SIZE)
            if not bytes_read:
            # file transmitting is done
                break
        # we use sendall to assure transimission in 
        # busy networks
            s.sendall(bytes_read)
    # close the socket
    print("...File Sent")
    s.close()