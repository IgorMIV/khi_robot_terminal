import sys
import socket
import select
import atexit

from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QMainWindow, QApplication
from PyQt6.QtWidgets import QPlainTextEdit, QLineEdit
from PyQt6.QtCore import QEvent, Qt, QTimer

step = 1.0

IP = "192.168.1.100"    # IP for K-Roset
PORT = 23         # Port for K-Roset

error_counter_limit = 1000000
footer_message = bytes.fromhex('0a')


class KhiRoTerm:
    def __init__(self, ip, port, parent):
        self.ip_address = ip
        self.port_number = port
        self.parent = parent
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
        if self.command_buffer is not None:
            if self.command_buffer == '':
                self.server.sendall(footer_message)
            else:
                self.server.sendall(self.command_buffer.encode())
                self.server.sendall(footer_message)

            self.command_buffer = None

        try:
            ready_to_read, ready_to_write, in_error = select.select([self.server, ], [], [], 0.01)
        except select.error:
            print('Transmission error')
        else:
            if len(in_error) > 0:
                return -1
            if len(ready_to_read) > 0:
                try:
                    recv = self.server.recv(4096)
                except:
                    print('Receive error')

                self.parent.print_text(recv.decode("utf-8", 'ignore'))

    def send_command(self, command):
        self.command_buffer = command

    def safe_exit(self):
        if self.server is not None:
            self.close_connection()

    def connect(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.connect((self.ip_address, self.port_number))

        kawasaki_msg = self.wait_recv([b'login:'], timeout=1)
        self.parent.print_text(kawasaki_msg.decode("utf-8", 'ignore'))

        self.server.sendall(b'as')
        self.server.sendall(b'\x0d\x0a')

        kawasaki_msg = self.wait_recv([b'\x3e'], timeout=1)
        self.parent.print_text(kawasaki_msg.decode("utf-8", 'ignore'))

        return 1

    def close_connection(self):
        self.server.close()

    def wait_recv(self, ends_list, timeout=0.01):
        break_actual = False
        while True:
            try:
                ready_to_read, ready_to_write, in_error = select.select([self.server, ], [], [], timeout)
            except select.error:
                print('Transmission error')
            else:
                if len(in_error) > 0:
                    print('Transmission error')
                    return -1
                if len(ready_to_read) > 0:
                    incoming = b''
                    while True:
                        if break_actual:
                            break
                        try:
                            recv = self.server.recv(1)
                        except:
                            print('Transmission error')
                            break_actual = True
                            break
                        if recv == b'':
                            break
                        incoming += recv
                        for eom in ends_list:
                            if incoming.find(eom) > -1:     # Wait eom message from robot
                                break_actual = True
                                break
            if break_actual:
                break
        # print(incoming)
        return incoming

    def read_r_variable(self, var_name):
        command = "list /r " + var_name
        self.server.sendall(command.encode())
        self.server.sendall(footer_message)

        kawasaki_msg = self.wait_recv([b'\x3e'], timeout=1)
        self.parent.print_text(kawasaki_msg.decode("utf-8", 'ignore'))

        tmp = kawasaki_msg.decode("utf-8", 'ignore').split('\r\n')
        for element in tmp:
            # print(element, element.find(var_name + ' ='))
            if element.find(var_name + ' =') > -1:
                return float(element.split(' ')[-1])

    def write_r_variable(self, var_name, var_value):
        command = var_name + " = " + str(var_value)
        self.server.sendall(command.encode())
        self.server.sendall(footer_message)

        kawasaki_msg = self.wait_recv([b'\x3e'], timeout=1)
        self.parent.print_text(kawasaki_msg.decode("utf-8", 'ignore'))


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.command_history = []
        self.last_command_in_hist = 0

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
        self.khiroterm = KhiRoTerm(tmp_ip, int(tmp_port), self)

        self.connect_button.setEnabled(False)
        self.ip_field.setEnabled(False)
        self.port_field.setEnabled(False)

    def print_text(self, text):
        self.text_terminal.insertPlainText(text)
        self.text_terminal.verticalScrollBar().setValue(self.text_terminal.verticalScrollBar().maximum())

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress and obj is self.text_line:
            if event.key() == 16777220 and self.text_line.hasFocus():  # Enter
                command = self.text_line.text()
                self.text_line.clear()
                if len(self.command_history) > 0:
                    if self.command_history[-1] != command:
                        self.command_history.append(command)
                        self.last_command_in_hist = len(self.command_history)
                else:
                    self.command_history.append(command)
                    self.last_command_in_hist = len(self.command_history)
                # print(self.last_command_in_hist)
                self.khiroterm.send_command(command)

            if event.key() == 16777235 and self.text_line.hasFocus():  # Up
                if len(self.command_history) > 0:
                    self.last_command_in_hist -= 1
                    if self.last_command_in_hist < 0:
                        self.last_command_in_hist = 0

                    self.text_line.setText(self.command_history[self.last_command_in_hist])

            if event.key() == 16777237 and self.text_line.hasFocus():  # Down
                if len(self.command_history) > 0:
                    self.last_command_in_hist += 1
                    if self.last_command_in_hist > (len(self.command_history)-1):
                        self.last_command_in_hist = (len(self.command_history)-1)

                    self.text_line.setText(self.command_history[self.last_command_in_hist])

        return super().eventFilter(obj, event)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    ex = MainWindow()
    ex.setWindowTitle("Kawasaki terminal")
    ex.setMinimumSize(800, 400)
    ex.show()
    sys.exit(app.exec())
