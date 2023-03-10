import socket
import atexit

IP = "192.168.1.11"    # IP for K-Roset
PORT = 23         # Port for K-Roset

error_counter_limit = 1000000
footer_message = bytes.fromhex('0a')


class KhiRoTerm:
    def __init__(self, ip, port):
        self.ip_address = ip
        self.port_number = port
        self.server = None

        atexit.register(self.safe_exit)

        if self.connect() != 1:
            print("Can't establish connection with robot")
        else:
            while True:
                command_text = input()

                if command_text == '':
                    self.server.sendall(footer_message)
                else:
                    self.server.sendall(command_text.encode())
                    self.server.sendall(footer_message)

                counter = 0
                while True:
                    receive_string = self.server.recv(4096, socket.MSG_PEEK)
                    counter += 1
                    # print("|", receive_string[-3:0].hex())

                    if receive_string.find(b'\x0d\x0a') >= 0:
                        receive_string = self.server.recv(4096)
                        print(receive_string.decode("utf-8", 'ignore'), end='')
                        # print("STATE2")
                        break

                    if receive_string.find(b'\x3e') >= 0:
                        receive_string = self.server.recv(4096)
                        print(receive_string.decode("utf-8", 'ignore'), end='')
                        # print("STATE1")
                        break

    def safe_exit(self):
        if self.server is not None:
            self.close_connection()

    def connect(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.connect((self.ip_address, self.port_number))

        error_counter = 0
        while True:
            error_counter += 1
            receive_string = self.server.recv(4096, socket.MSG_PEEK)
            if receive_string.find(b'login:') > -1:     # Wait 'login:' message from robot
                receive_string = self.server.recv(4096)
                print(receive_string.decode("utf-8", 'ignore'), end='')
                break
            if error_counter > error_counter_limit:
                print("Connection timeout error - 1")
                self.server.close()
                return -1000

        self.server.sendall(b'as')
        self.server.sendall(b'\x0d\x0a')

        error_counter = 0
        while True:
            error_counter += 1
            receive_string = self.server.recv(4096, socket.MSG_PEEK)
            if receive_string.find(b'\x3e') > -1:     # This is AS monitor terminal..  Wait '>' sign from robot
                receive_string = self.server.recv(4096)
                print(receive_string.decode("utf-8", 'ignore'), end='')
                return 1
            if error_counter > error_counter_limit:
                print("Connection timeout error - 2")
                self.server.close()
                return -1000

    def close_connection(self):
        self.server.close()


khiroterm = KhiRoTerm(IP, PORT)
