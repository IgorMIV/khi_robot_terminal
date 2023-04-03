import sys
import socket
import atexit

from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QMainWindow, QApplication
from PyQt6.QtWidgets import QPlainTextEdit, QLineEdit
from PyQt6.QtCore import QEvent, Qt, QTimer

step = 1.0

IP = "192.168.1.11"    # IP for K-Roset
PORT = 23         # Port for K-Roset

error_counter_limit = 1000000
footer_message = bytes.fromhex('0a')


class KhiRoTerm:
    def __init__(self, ip, port):
        self.ip_address = ip
        self.port_number = port
        self.server = None

        self.command_buffer = None

        atexit.register(self.safe_exit)

        if self.connect() != 1:
            print("Can't establish connection with robot")
        else:
            self.timer = QTimer()
            self.timer.setInterval(100)
            self.timer.timeout.connect(self.timer_timeout)
            self.timer.start()

    def timer_timeout(self):
        print("Timeout")
        pass
        # while True:
        #     if self.command_buffer is not None:
        #         if self.command_buffer == '':
        #             self.server.sendall(footer_message)
        #         else:
        #             self.server.sendall(self.command_buffer.encode())
        #             self.server.sendall(footer_message)
        #
        #         self.command_buffer = None
        #
        #         counter = 0
        #         while True:
        #             receive_string = self.server.recv(4096, socket.MSG_PEEK)
        #             counter += 1
        #             # print("|", receive_string[-3:0].hex())
        #
        #             if receive_string.find(b'\x0d\x0a') >= 0:
        #                 receive_string = self.server.recv(4096)
        #                 print(receive_string.decode("utf-8", 'ignore'), end='')
        #                 # print("STATE2")
        #                 break
        #
        #             if receive_string.find(b'\x3e') >= 0:
        #                 receive_string = self.server.recv(4096)
        #                 print(receive_string.decode("utf-8", 'ignore'), end='')
        #                 # print("STATE1")
        #                 break

    def get_command(self, command):
        self.command_buffer = command

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


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__()

        central_widget = QWidget()
        gui_layout = QVBoxLayout()

        central_widget.setLayout(gui_layout)
        self.setCentralWidget(central_widget)

        ip_layout = QHBoxLayout()
        gui_layout.addLayout(ip_layout)

        ip_layout.addStretch(1)

        ip_layout.addWidget(QLabel("IP:"))
        self.ip_field = QLineEdit()
        self.ip_field.setText(IP)
        ip_layout.addWidget(self.ip_field)

        ip_layout.addWidget(QLabel("Port:"))
        self.port_field = QLineEdit()
        self.port_field.setText(str(PORT))
        ip_layout.addWidget(self.port_field)

        self.connect_button = QPushButton("Connect")
        ip_layout.addWidget(self.connect_button)
        self.connect_button.clicked.connect(self.connect_button_function)

        self.text_terminal = QPlainTextEdit()
        self.text_terminal.setReadOnly(True)
        gui_layout.addWidget(self.text_terminal)
        self.text_terminal.installEventFilter(self)

        self.text_line = QLineEdit()
        gui_layout.addWidget(self.text_line)
        self.text_line.installEventFilter(self)
        self.text_line.installEventFilter(self)

        # khiroterm = KhiRoTerm(IP, PORT)

    def connect_button_function(self):
        tmp_ip = self.ip_field.text()
        tmp_port = self.port_field.text()

        # khiroterm = KhiRoTerm(tmp_ip, tmp_port)
        # khiroterm = KhiRoTerm(tmp_ip, int(tmp_port))

        self.connect_button.setEnabled(False)
        self.ip_field.setEnabled(False)
        self.port_field.setEnabled(False)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress and obj is self.text_terminal:
            pass
            # if event.key() == 16777220 and self.text_terminal.hasFocus():
            #     string_text = self.text_terminal.toPlainText().split('\n')[-1]
            #     print(string_text)
            #     print('Enter pressed')
        if event.type() == QEvent.Type.KeyPress and obj is self.text_line:
            if event.key() == 16777220 and self.text_line.hasFocus():
                # string_text = self.text_terminal.toPlainText().split('\n')[-1]
                # print(string_text)
                # print('Enter pressed')
                command = self.text_line.text()
                self.text_line.clear()
                self.text_terminal.insertPlainText(command + "\n")
        return super().eventFilter(obj, event)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    ex = MainWindow()
    ex.setWindowTitle("Kawasaki terminal")
    ex.setMinimumSize(800, 400)
    ex.show()
    sys.exit(app.exec())
