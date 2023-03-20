import sys
import socket
import select
import atexit

from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QMainWindow, QApplication
from PyQt6.QtWidgets import QPlainTextEdit, QLineEdit
from PyQt6.QtCore import QEvent, Qt, QTimer

step = 0.5

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

        self.read_all_variables()


    def button_white_up_function(self):
        self.white_compensation = self.khiroterm.read_r_variable("white_comp") + step
        self.khiroterm.write_r_variable("white_comp", self.white_compensation)
        self.label_white.setText(str(self.white_compensation))

    def button_white_down_function(self):
        self.white_compensation = self.khiroterm.read_r_variable("white_comp") - step
        self.khiroterm.write_r_variable("white_comp", self.white_compensation)
        self.label_white.setText(str(self.white_compensation))

    def button_green_up_function(self):
        self.green_compensation = self.khiroterm.read_r_variable("green_comp") + step
        self.khiroterm.write_r_variable("green_comp", self.green_compensation)
        self.label_green.setText(str(self.green_compensation))

    def button_green_down_function(self):
        self.green_compensation = self.khiroterm.read_r_variable("green_comp") - step
        self.khiroterm.write_r_variable("green_comp", self.green_compensation)
        self.label_green.setText(str(self.green_compensation))

    def button_red_up_function(self):
        self.red_compensation = self.khiroterm.read_r_variable("red_comp") + step
        self.khiroterm.write_r_variable("red_comp", self.red_compensation)
        self.label_red.setText(str(self.red_compensation))

    def button_red_down_function(self):
        self.red_compensation = self.khiroterm.read_r_variable("red_comp") - step
        self.khiroterm.write_r_variable("red_comp", self.red_compensation)
        self.label_red.setText(str(self.red_compensation))

    def button_blue_up_function(self):
        self.blue_compensation = self.khiroterm.read_r_variable("blue_comp") + step
        self.khiroterm.write_r_variable("blue_comp", self.blue_compensation)
        self.label_blue.setText(str(self.blue_compensation))

    def button_blue_down_function(self):
        self.blue_compensation = self.khiroterm.read_r_variable("blue_comp") - step
        self.khiroterm.write_r_variable("blue_comp", self.blue_compensation)
        self.label_blue.setText(str(self.blue_compensation))

    def button_black_up_function(self):
        self.black_compensation = self.khiroterm.read_r_variable("black_comp") + step
        self.khiroterm.write_r_variable("black_comp", self.black_compensation)
        self.label_black.setText(str(self.black_compensation))

    def button_black_down_function(self):
        self.black_compensation = self.khiroterm.read_r_variable("black_comp") - step
        self.khiroterm.write_r_variable("black_comp", self.black_compensation)
        self.label_black.setText(str(self.black_compensation))

    def button_yellow_up_function(self):
        self.yellow_compensation = self.khiroterm.read_r_variable("yellow_comp") + step
        self.khiroterm.write_r_variable("yellow_comp", self.yellow_compensation)
        self.label_yellow.setText(str(self.yellow_compensation))

    def button_yellow_down_function(self):
        self.yellow_compensation = self.khiroterm.read_r_variable("yellow_comp") - step
        self.khiroterm.write_r_variable("yellow_comp", self.yellow_compensation)
        self.label_yellow.setText(str(self.yellow_compensation))

    def button_canvas_up_function(self):
        self.canvas_compensation = self.khiroterm.read_r_variable("canvas_comp") + step
        self.khiroterm.write_r_variable("canvas_comp", self.canvas_compensation)
        self.label_canvas.setText(str(self.canvas_compensation))

    def button_canvas_down_function(self):
        self.canvas_compensation = self.khiroterm.read_r_variable("canvas_comp") - step
        self.khiroterm.write_r_variable("canvas_comp", self.canvas_compensation)
        self.label_canvas.setText(str(self.canvas_compensation))

    def button_water_up_function(self):
        self.water_compensation = self.khiroterm.read_r_variable("water_comp") + step
        self.khiroterm.write_r_variable("water_comp", self.water_compensation)
        self.label_water.setText(str(self.water_compensation))

    def button_water_down_function(self):
        self.water_compensation = self.khiroterm.read_r_variable("water_comp") - step
        self.khiroterm.write_r_variable("water_comp", self.water_compensation)
        self.label_water.setText(str(self.water_compensation))

    def print_text(self, text):
        self.text_terminal.insertPlainText(text)
        self.text_terminal.verticalScrollBar().setValue(self.text_terminal.verticalScrollBar().maximum())

    def read_all_variables(self):
        self.white_compensation = self.khiroterm.read_r_variable("white_comp")
        self.green_compensation = self.khiroterm.read_r_variable("green_comp")
        self.red_compensation = self.khiroterm.read_r_variable("red_comp")
        self.blue_compensation = self.khiroterm.read_r_variable("blue_comp")
        self.black_compensation = self.khiroterm.read_r_variable("black_comp")
        self.yellow_compensation = self.khiroterm.read_r_variable("yellow_comp")
        self.canvas_compensation = self.khiroterm.read_r_variable("canvas_comp")
        self.water_compensation = self.khiroterm.read_r_variable("water_comp")

        self.label_white.setText(str(self.white_compensation))
        self.label_green.setText(str(self.green_compensation))
        self.label_red.setText(str(self.red_compensation))
        self.label_blue.setText(str(self.blue_compensation))
        self.label_black.setText(str(self.black_compensation))
        self.label_yellow.setText(str(self.yellow_compensation))
        self.label_canvas.setText(str(self.canvas_compensation))
        self.label_water.setText(str(self.water_compensation))

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress and obj is self.text_line:
            if event.key() == 16777220 and self.text_line.hasFocus():  # Enter
                command = self.text_line.text()
                self.text_line.clear()
                if len(self.command_history) > 0:
                    if self.command_history[-1] != command:
                        self.command_history.append(command)
                        self.last_command_in_hist = len(self.command_history)
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
    ex.setBaseSize(800, 600)
    ex.show()
    sys.exit(app.exec())
