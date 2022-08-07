'''Node connections using socket programming'''
import time
import socket
import threading
from threading import Timer
import csv
import os
import ftpsender


SEPARATOR=","

myIP = socket.gethostbyname(socket.gethostname()) #SERVER IP
print('myIP ',myIP)

# rendezvous = ('169.254.90.175', 12345)

# # connect to rendezvous to discover other peers
# print('connecting to rendezvous server')

# def rendezvous_discover():
#     '''Every node creates a socket which is used to listen 
#     and send to rendezvous server to discover peers.
#     Rendezvous server is a server known by all and helps establishing
#     p2p connections.'''
#     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     sock.bind(('', 23456)) # created socket on node to connect to rendezvous server to discover peers
#     sock.sendto(b'0', rendezvous) # initial message to rendezvous to get response from the rendezvous server
#     while True:    
#         data, address = sock.recvfrom(128)
#         if data.strip() == 'ready':
#             print('checked in with server, waiting')
#         break
#         data = sock.recv(1024).decode()
#         ip, sport, dport = data.split(' ')
#         sport = int(sport)
#         dport = int(dport)
#     return (ip, sport, dport) #source port for  listening and destport for sending

class NodeC():
    # If your node initiated the connection, it's outbound, otherwise it's inbound.
    # Nodes will send and receive data from both types of connections exactly the same way.
    def __init__(self):
        self.outbound = [] # Connections you made. Store Address
        self.inbound = [] # Connections others made to you.  Store Address
        self.osock=[]
        self.isock=[]
    def create_connection_to_other_node(self,port_on_my_device , address_of_other_node):
        # print(type(port_on_my_device), address_of_other_node)
        if address_of_other_node in self.inbound or address_of_other_node in self.outbound:
            # We are already connected to that node using tcp
            pass
        else:
            #Create outbound connection
            outsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            outsock.bind(('', port_on_my_device)) # created socket on node to connect to rendezvous server to discover peers
            
            try:
                outsock.connect(address_of_other_node)
                
                print('connected to: {}'.format(address_of_other_node))
                
                thread = threading.Thread(target=self.handle_outbound_node, args=( outsock,address_of_other_node) )
                thread.start()
                
            except Exception as e:
                print('No such address!!',e)
    
    def clisten(self,listening_port): #listen on tcp socket
        # For create inbound connections
        insock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        insock.bind(('', listening_port)) # created socket on node to listen inbound
        insock.listen()
        print('Listening for incoming connection on,',myIP,':',listening_port)
        while True: #listen for inbound tcp connections
            conn, addr = insock.accept()
            if (conn not in self.inbound) and (conn not in self.outbound):
                thread = threading.Thread(target=self.handle_inbound_node, args=(conn,addr,) )
                thread.start()
                print(f'ACTIVE Inbound CONNECTIONS : {threading.active_count()-1}')
        insock.close()

    def handle_inbound_node(self,conn,address_of_other_node): #completed#
        self.inbound += [address_of_other_node] # save this inbound connection
        self.isock+=[conn]
        connection = True
        conn.settimeout(100) # Initial connection Timeout
        while connection: # while the inbound node does not disconnect itself or face timeout.
            try:
                msg_length , addr = conn.recvfrom(1024)
                msg_length =msg_length.decode()
                if msg_length=='Alive!': #ack message
                    conn.settimeout(100) # timeout of 10 sec
                elif msg_length:
                    msg_length = int(msg_length)
                    msg = conn.recv(msg_length).decode()
                    print(msg)
                    if msg=='ftp': #create a new tcp connection for ftp
                        metadata , addr = conn.recvfrom(1024).decode()
                        filename, destination_port = metadata.split(SEPARATOR)
                        thread = threading.Thread(target=self.file_transfer, args=(filename,destination_port,addr) )
                        thread.start()
            except socket.error as e:
                conn.close()
                print(f'#Inbound Connection Closed {address_of_other_node}')
                self.inbound.remove(address_of_other_node)
                self.isock.remove(conn)
                break
            time.sleep(0.01)  #user action wait
    def handle_outbound_node(self,conn,address_of_other_node):
        self.outbound += [address_of_other_node] # save this outbound connection
        self.osock+=[conn]
        connection = True
        conn.settimeout(100)
        while connection: # while the outbound node does not disconnect or face timeout.
            try:
                msg_length , addr = conn.recvfrom(1024) # Try to receive Acknowledgement or msg length
                msg_length =msg_length.decode()

                if msg_length=='Alive!': #ack message
                    conn.settimeout(100) # timeout of 10 sec
                elif msg_length:
                    msg_length = int(msg_length)
                    msg = conn.recv(msg_length).decode()
                    print(msg)
                    if msg=='ftp': #create a new tcp connection for ftp
                        SEPARATOR=","
                        metadata , addr = conn.recvfrom(1024).decode()
                        filename, destination_port = metadata.split(SEPARATOR)
                        thread = threading.Thread(target=self.file_send_transfer, args=(filename,destination_port,addr) )
                        thread.start()
            except socket.error as e:
                conn.close()
                print(f'#Outbound Connection Closed {address_of_other_node}')
                self.outbound.remove(address_of_other_node)
                self.osock.remove(conn)
                break
            time.sleep(0.01)  #user action wait
    def send(self,msg,conn):
        message =msg.encode()
        msg_length =len(message)
        send_length = str(msg_length).encode()
        send_length += b' ' * (1024 - len(send_length))
        conn.send(send_length)
        conn.send(message)

    def sendACKtoALL(self):
        for conn in self.isock:
            # print(conn)
            self.send('Alive!',conn)
        for conn in self.osock:
            # print(conn)
            self.send('Alive!',conn)
    def file_send_transfer(self,filename,destination_port,tcp_address): #I am sending the file
        host,communication_port= tcp_address        
        if not self.checkExists(filename):
            self.send('File does not Exists!!',tcp_address)
            return
        ftpsender.ftp_send(filename,host,destination_port)
        # threading.Lock()
        self.update_metadata(filename,host,communication_port)
        # threading.Lock()        
        
    def file_recv_transfer(self,receive_port,filename):
        open_ftp_port = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # open ftp port where I would receive the file
        open_ftp_port.bind(('', receive_port))
        open_ftp_port.listen()
        conn, addr = open_ftp_port.accept()
      
        path = './recv'
        file = os.path.join(path, filename)
        with open(file, "wb") as f:
            while True:
            # read 4096 bytes from the socket (receive)
                bytes_read = open_ftp_port.recv(4096)
                if not bytes_read:    
                    # nothing is received
                    # file transmitting is done
                    break
                # write to the file the bytes we just received
                f.write(bytes_read)
                # update the progress bar

            open_ftp_port.close()
                # close the FTP socket
        print(filename+ " received")
        
    def checkExists(self,filename):
        path ='./files'
        file = os.path.join(path,filename)
        return os.path.isfile(file)
    def update_metadata(self,filename,host,communication_port):
        dict = {"fname":filename,"IP":host,"communication_port":communication_port}
        with open("metadata.txt","a",newline='') as f:
            writer = csv.DictWriter(f, fieldnames = field)
            writer.writerow(dict)
        
############################# MAIN #########################################
field = ["fname","IP","communication_port"]
def meta_exists():
    print("Checking metadata existence...")
    if not os.path.isfile("metadata.txt"):
        print("Metadata does not exist...Creating blank metadata file")
        with open("metadata.txt","a",newline='') as file:
            writer = csv.DictWriter(file, fieldnames = field)
            writer.writeheader()

# meta_exists()

my = NodeC()

listen_port=60600
listen_port=int(input('Enter listening port:'))

listener = threading.Thread(target=my.clisten,args=(listen_port,), daemon=True);
listener.start()

def parse_create(msg):
    port_on_my_device , address_of_other_node = msg.split(' ')
    ip,port = address_of_other_node.split(':')
    return int(port_on_my_device) , ip , int(port)
def parse_send(msg):
    addr , message = msg.split(',,,')
    ip, port = addr.split(':')
    return ip, int(port), message
def parse_ftp(msg):
    #pasrsed output gives filename, receieve_port
    filename, receive_port = msg.split(SEPARATOR)
    return filename, int(receive_port)
while True:
    msg=input('>')
    if msg=='outbound':
        print('Outbound=',my.outbound)
    if msg=='inbound':
        print('Inbound=',my.inbound)
    if msg=='all':
        print('Outbound=',my.outbound)
        print('Inbound=',my.inbound)
    if msg.startswith('!create'):
        msg=msg[8:]
        port_on_my_device , ip , port = parse_create(msg)
        my.create_connection_to_other_node(port_on_my_device,(ip,port))
        
        # my.create_connection_to_other_node(50500,ip,60600)
    if msg.startswith('!send'):
       
        msg=msg[6:]
        ip, port, msg = parse_send(msg)
        
        if msg.startswith('ftp'):
            filename, receive_port = parse_ftp(msg[4:])
            thread = threading.Thread(target=my.file_recv_transfer, args=(receive_port,filename) )
            thread.start()
        for addr,conn in zip(my.inbound,my.isock):
            if ip==addr[0]:
                my.send(msg,conn)               
        for addr,conn in zip(my.outbound,my.osock):
            if ip==addr[0]:
                my.send(msg,conn)
    # else:
    #     print("Incorrent Input!!")
    time.sleep(0.5)
    my.sendACKtoALL()
        