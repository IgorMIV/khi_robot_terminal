import sys
import socket
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

    def timer_timeout(self):
        if self.command_buffer is not None:
            if self.command_buffer == '':
                self.server.sendall(footer_message)
            else:
                self.server.sendall(self.command_buffer.encode())
                self.server.sendall(footer_message)

            self.command_buffer = None
        print("IN")
        receive_string = self.server.recv(0, socket.MSG_PEEK)
        print("OUT")
        # if len(receive_string) > 0:
        #     receive_string = self.server.recv(4096)
        #     self.parent.print_text(receive_string.decode("utf-8", 'ignore'))

            # counter = 0
            # while True:
            #     receive_string = self.server.recv(4096, socket.MSG_PEEK)
            #     counter += 1
            #     # print("|", receive_string[-3:0].hex())
            #
            #     if receive_string.find(b'\x0d\x0a') >= 0:
            #         receive_string = self.server.recv(4096)
            #         print(receive_string.decode("utf-8", 'ignore'), end='')
            #         # print("STATE2")
            #         break
            #
            #     if receive_string.find(b'\x3e') >= 0:
            #         receive_string = self.server.recv(4096)
            #         print(receive_string.decode("utf-8", 'ignore'), end='')
            #         # print("STATE1")
            #         break

    def send_command(self, command):
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
                self.parent.print_text(receive_string.decode("utf-8", 'ignore'))
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
                self.parent.print_text(receive_string.decode("utf-8", 'ignore'))
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

        self.white_compensation = 0
        self.green_compensation = 0
        self.red_compensation = 0
        self.blue_compensation = 0
        self.black_compensation = 0
        self.yellow_compensation = 0
        self.water_compensation = 0
        self.canvas_compensation = 0

        central_widget = QWidget()
        gui_layout = QVBoxLayout()

        central_widget.setLayout(gui_layout)
        self.setCentralWidget(central_widget)

        brush_height_layout = QHBoxLayout()
        gui_layout.addLayout(brush_height_layout)

        self.text_terminal = QPlainTextEdit()
        self.text_terminal.setReadOnly(True)
        gui_layout.addWidget(self.text_terminal)
        self.text_terminal.installEventFilter(self)

        self.text_line = QLineEdit()
        gui_layout.addWidget(self.text_line)
        self.text_line.installEventFilter(self)
        self.text_line.installEventFilter(self)

        white_layout = QVBoxLayout()
        green_layout = QVBoxLayout()
        red_layout = QVBoxLayout()
        blue_layout = QVBoxLayout()
        black_layout = QVBoxLayout()
        yellow_layout = QVBoxLayout()
        canvas_layout = QVBoxLayout()
        water_layout = QVBoxLayout()
        brush_height_layout.addLayout(white_layout)
        brush_height_layout.addLayout(green_layout)
        brush_height_layout.addLayout(red_layout)
        brush_height_layout.addLayout(blue_layout)
        brush_height_layout.addLayout(black_layout)
        brush_height_layout.addLayout(yellow_layout)
        brush_height_layout.addLayout(canvas_layout)
        brush_height_layout.addLayout(water_layout)

        # white
        button_white_up = QPushButton("White up")
        button_white_up.clicked.connect(self.button_white_up_function)
        self.label_white = QLabel(str(self.white_compensation))
        button_white_down = QPushButton("White down")
        button_white_down.clicked.connect(self.button_white_down_function)
        white_layout.addWidget(button_white_up)
        white_layout.addWidget(self.label_white)
        white_layout.addWidget(button_white_down)

        # green
        button_green_up = QPushButton("Green up")
        button_green_up.clicked.connect(self.button_green_up_function)
        self.label_green = QLabel(str(self.green_compensation))
        button_green_down = QPushButton("Green down")
        button_green_down.clicked.connect(self.button_green_down_function)
        green_layout.addWidget(button_green_up)
        green_layout.addWidget(self.label_green)
        green_layout.addWidget(button_green_down)

        # red
        button_red_up = QPushButton("Red up")
        button_red_up.clicked.connect(self.button_red_up_function)
        self.label_red = QLabel(str(self.red_compensation))
        button_red_down = QPushButton("Red down")
        button_red_down.clicked.connect(self.button_red_down_function)
        red_layout.addWidget(button_red_up)
        red_layout.addWidget(self.label_red)
        red_layout.addWidget(button_red_down)

        # blue
        button_blue_up = QPushButton("Blue up")
        button_blue_up.clicked.connect(self.button_blue_up_function)
        self.label_blue = QLabel(str(self.blue_compensation))
        button_blue_down = QPushButton("Blue down")
        button_blue_down.clicked.connect(self.button_blue_down_function)
        blue_layout.addWidget(button_blue_up)
        blue_layout.addWidget(self.label_blue)
        blue_layout.addWidget(button_blue_down)

        # black
        button_black_up = QPushButton("Black up")
        button_black_up.clicked.connect(self.button_black_up_function)
        self.label_black = QLabel(str(self.black_compensation))
        button_black_down = QPushButton("Black down")
        button_black_down.clicked.connect(self.button_black_down_function)
        black_layout.addWidget(button_black_up)
        black_layout.addWidget(self.label_black)
        black_layout.addWidget(button_black_down)

        # yellow
        button_yellow_up = QPushButton("Yellow up")
        button_yellow_up.clicked.connect(self.button_yellow_up_function)
        self.label_yellow = QLabel(str(self.yellow_compensation))
        button_yellow_down = QPushButton("Yellow down")
        button_yellow_down.clicked.connect(self.button_yellow_down_function)
        yellow_layout.addWidget(button_yellow_up)
        yellow_layout.addWidget(self.label_yellow)
        yellow_layout.addWidget(button_yellow_down)

        # canvas
        button_canvas_up = QPushButton("Canvas up")
        button_canvas_up.clicked.connect(self.button_canvas_up_function)
        self.label_canvas = QLabel(str(self.canvas_compensation))
        button_canvas_down = QPushButton("Canvas down")
        button_canvas_down.clicked.connect(self.button_canvas_down_function)
        canvas_layout.addWidget(button_canvas_up)
        canvas_layout.addWidget(self.label_canvas)
        canvas_layout.addWidget(button_canvas_down)

        # water
        button_water_up = QPushButton("Water up")
        button_water_up.clicked.connect(self.button_water_up_function)
        self.label_water = QLabel(str(self.water_compensation))
        button_water_down = QPushButton("Water down")
        button_water_down.clicked.connect(self.button_water_down_function)
        water_layout.addWidget(button_water_up)
        water_layout.addWidget(self.label_water)
        water_layout.addWidget(button_water_down)

        self.khiroterm = KhiRoTerm(IP, PORT, self)


    def button_white_up_function(self):
        self.white_compensation = self.white_compensation + step
        self.label_white.setText(str(self.white_compensation))

    def button_white_down_function(self):
        self.white_compensation = self.white_compensation - step
        self.label_white.setText(str(self.white_compensation))

    def button_green_up_function(self):
        self.green_compensation = self.green_compensation + step
        self.label_green.setText(str(self.green_compensation))

    def button_green_down_function(self):
        self.green_compensation = self.green_compensation - step
        self.label_green.setText(str(self.green_compensation))

    def button_red_up_function(self):
        self.red_compensation = self.red_compensation + step
        self.label_red.setText(str(self.red_compensation))

    def button_red_down_function(self):
        self.red_compensation = self.red_compensation - step
        self.label_red.setText(str(self.red_compensation))

    def button_blue_up_function(self):
        self.blue_compensation = self.blue_compensation + step
        self.label_blue.setText(str(self.blue_compensation))

    def button_blue_down_function(self):
        self.blue_compensation = self.blue_compensation - step
        self.label_blue.setText(str(self.blue_compensation))

    def button_black_up_function(self):
        self.black_compensation = self.black_compensation + step
        self.label_black.setText(str(self.black_compensation))

    def button_black_down_function(self):
        self.black_compensation = self.black_compensation - step
        self.label_black.setText(str(self.black_compensation))

    def button_yellow_up_function(self):
        self.yellow_compensation = self.yellow_compensation + step
        self.label_yellow.setText(str(self.yellow_compensation))

    def button_yellow_down_function(self):
        self.yellow_compensation = self.yellow_compensation - step
        self.label_yellow.setText(str(self.yellow_compensation))

    def button_canvas_up_function(self):
        self.canvas_compensation = self.canvas_compensation + step
        self.label_canvas.setText(str(self.canvas_compensation))

    def button_canvas_down_function(self):
        self.canvas_compensation = self.canvas_compensation - step
        self.label_canvas.setText(str(self.canvas_compensation))

    def button_water_up_function(self):
        self.water_compensation = self.water_compensation + step
        self.label_water.setText(str(self.water_compensation))

    def button_water_down_function(self):
        self.water_compensation = self.water_compensation - step
        self.label_water.setText(str(self.water_compensation))

    def print_text(self, text):
        self.text_terminal.insertPlainText(text)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress and obj is self.text_line:
            if event.key() == 16777220 and self.text_line.hasFocus():
                command = self.text_line.text()
                self.text_line.clear()
                self.khiroterm.send_command(command)
        return super().eventFilter(obj, event)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    ex = MainWindow()
    ex.setWindowTitle("Kawasaki terminal")
    ex.setMinimumSize(800, 400)
    ex.show()
    sys.exit(app.exec())
