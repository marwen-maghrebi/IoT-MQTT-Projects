# ========================
#         Imports
# ========================
import ctypes

import sys
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from mainwindow import Ui_MainWindow
from data import *
import paho.mqtt.client as mqtt
from Mqtt import MqttClient

# Project-specific modules
from custom_switch import CustomSwitch
from project1 import LED_and_Button
from project2 import Tem_hum_Sensor
from project3 import WaterLevelControllerWindow
from project4 import LOADCELL
from project5 import AccelerometerGyroscopeController
from project6 import GasSensorController


# ========================
#       Main Window
# ========================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # --- UI Setup ---
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.retranslateUi(self)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('com.mycompany.myapp')
        self.setWindowIcon(QIcon(":/pic/logo/demo.ico"))

        # --- State Variables ---
        self.active_line_edit = None
        self.mqtt_client = MqttClient()
        self.current_project = None
        self.drag_pos = QtCore.QPoint()

        # --- Layout Settings ---
        self.normal_left_margin = 780
        self.maximized_left_margin = 1300
        self.normal_spacing = 6
        self.maximized_spacing = 0

        # --- Connect Buttons ---
        self.ui.btn_close.clicked.connect(self.close)
        self.ui.btn_minimize.clicked.connect(self.showMinimized)
        self.ui.btn_maximize.clicked.connect(self.toggle_maximize)

        # --- Enable Window Dragging ---
        self.ui.TitelBar.mousePressEvent = self.title_bar_mouse_press
        self.ui.TitelBar.mouseMoveEvent = self.title_bar_mouse_move

        # --- Initialize Interface ---
        self.initUI()

    # ========================
    #     UI Initialization
    # ========================
    
    def initUI(self):
        # Set default screen
        self.ui.stackedWidget.setCurrentIndex(screen_home)
        
        # ResetKeyboard
        self.ResetKeyboard()
        self.ui.Authentification_label.hide()
        # --- MQTT Buttons ---
        self.ui.Connect_Button.clicked.connect(self.Connect)
        self.ui.Disconnect_Button.clicked.connect(self.Disconnect)

        # --- Keyboard Buttons ---
        for btn in [
            self.ui.Btn_A, self.ui.Btn_Z, self.ui.Btn_E, self.ui.Btn_R,
            self.ui.Btn_T, self.ui.Btn_Y, self.ui.Btn_U, self.ui.Btn_I,
            self.ui.Btn_O, self.ui.Btn_P, self.ui.Btn_Q, self.ui.Btn_S,
            self.ui.Btn_D, self.ui.Btn_F, self.ui.Btn_G, self.ui.Btn_H,
            self.ui.Btn_J, self.ui.Btn_K, self.ui.Btn_L, self.ui.Btn_M,
            self.ui.Btn_W, self.ui.Btn_X, self.ui.Btn_C, self.ui.Btn_V,
            self.ui.Btn_B, self.ui.Btn_N, self.ui.Btn_Us, self.ui.Btn_Sl,
            self.ui.Btn_Dot, self.ui.Btn_Comma, self.ui.Btn_Back,
            self.ui.Btn_Symbols, self.ui.Btn_Caps,
            self.ui.Btn_Space, self.ui.Btn_KB_Hide, self.ui.Btn_Enter
        ]:
            btn.clicked.connect(self.Keyboard_Handler)

        self.ui.Btn_Space.setText(QtWidgets.QApplication.translate(" ", " "))
        self.ui.Btn_KB_Hide.clicked.connect(self.ResetKeyboard)
        # --- Show/Hide Password ---
        self.ui.btn_show_wifi.clicked.connect(self.ShowPassword)
        self.ui.password_lineEdit.clear()
        self.ui.password_lineEdit.setEchoMode(QtWidgets.QLineEdit.Password)

        # --- Input Field Focus Events ---
        for field in [self.ui.host_lineEdit, self.ui.user_lineEdit, self.ui.password_lineEdit]:
            field.installEventFilter(self)

        # --- Navigation Buttons ---
        self.ui.btn_accueil.clicked.connect(self.goToHome)
        self.ui.btn_retour_buttonPr.clicked.connect(self.goToScreenProject)
        self.ui.btn_retour_watherPr.clicked.connect(self.goToScreenProject)
        self.ui.btn_retour_SensorPr.clicked.connect(self.goToScreenProject)
        self.ui.btn_retour_LoadCell_Pr.clicked.connect(self.goToScreenProject)
        self.ui.btn_retour_Accelo_Pr.clicked.connect(self.goToScreenProject)
        self.ui.btn_retour_MQ2.clicked.connect(self.goToScreenProject)

        self.ui.btn_Project_1.clicked.connect(self.goToScreenButton)
        self.ui.btn_Project_2.clicked.connect(self.goToScreenWather)
        self.ui.btn_Project_3.clicked.connect(self.goToScreenSensor)
        self.ui.btn_Project_4.clicked.connect(self.goToScreenLoadCell)
        self.ui.btn_Project_5.clicked.connect(self.goToScreenAccelo)
        self.ui.btn_Project_6.clicked.connect(self.goToScreenGasSensor)

    # ========================
    #   Title Bar Handling
    # ========================

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.adjust_titlebar_margin(self.normal_left_margin)
            self.set_titlebar_spacing(self.normal_spacing)
        else:
            self.showMaximized()
            self.adjust_titlebar_margin(self.maximized_left_margin)
            self.set_titlebar_spacing(self.maximized_spacing)

    def adjust_titlebar_margin(self, left_margin):
        if self.ui.TitelBar.layout():
            margins = self.ui.TitelBar.layout().getContentsMargins()
            self.ui.TitelBar.layout().setContentsMargins(left_margin, margins[1], margins[2], margins[3])

    def set_titlebar_spacing(self, spacing):
        if self.ui.TitelBar.layout():
            self.ui.TitelBar.layout().setSpacing(spacing)

    def title_bar_mouse_press(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def title_bar_mouse_move(self, event):
        if event.buttons() == QtCore.Qt.LeftButton and self.drag_pos:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    # ========================
    #     Keyboard Logic
    # ========================

    def SetKeys(self, Sender):
        index = 2 if "Symbols" in Sender and self.ui.Btn_Symbols.isChecked() else \
                2 if self.ui.Btn_Symbols.isChecked() else \
                0 if self.ui.Btn_Caps.isChecked() else 1

        button_text_map = {
            "Btn_A": Password_BTN_PasswordAtext[index],
            "Btn_Z": Password_BTN_PasswordZtext[index],
            "Btn_E": Password_BTN_PasswordEtext[index],
            "Btn_R": Password_BTN_PasswordRtext[index],
            "Btn_T": Password_BTN_PasswordTtext[index],
            "Btn_Y": Password_BTN_PasswordYtext[index],
            "Btn_U": Password_BTN_PasswordUtext[index],
            "Btn_I": Password_BTN_PasswordItext[index],
            "Btn_O": Password_BTN_PasswordOtext[index],
            "Btn_P": Password_BTN_PasswordPtext[index],
            "Btn_Q": Password_BTN_PasswordQtext[index],
            "Btn_S": Password_BTN_PasswordStext[index],
            "Btn_D": Password_BTN_PasswordDtext[index],
            "Btn_F": Password_BTN_PasswordFtext[index],
            "Btn_G": Password_BTN_PasswordGtext[index],
            "Btn_H": Password_BTN_PasswordHtext[index],
            "Btn_J": Password_BTN_PasswordJtext[index],
            "Btn_K": Password_BTN_PasswordKtext[index],
            "Btn_L": Password_BTN_PasswordLtext[index],
            "Btn_M": Password_BTN_PasswordMtext[index],
            "Btn_W": Password_BTN_PasswordWtext[index],
            "Btn_X": Password_BTN_PasswordXtext[index],
            "Btn_C": Password_BTN_PasswordCtext[index],
            "Btn_V": Password_BTN_PasswordVtext[index],
            "Btn_B": Password_BTN_PasswordBtext[index],
            "Btn_N": Password_BTN_PasswordNtext[index],
            "Btn_Us": Password_BTN_PasswordUstext[index],
            "Btn_Sl": Password_BTN_PasswordSltext[index],
            "Btn_Dot": Password_BTN_PasswordDottext[index],
            "Btn_Comma": Password_BTN_PasswordCommatext[index],
        }

        for button_name, text in button_text_map.items():
            getattr(self.ui, button_name).setText(QtWidgets.QApplication.translate("Ui_MainWindow", text))

    def Keyboard_Handler(self):
        if "Caps" in self.sender().objectName():
            self.SetKeys("Caps")
            return
        elif "Symbols" in self.sender().objectName():
            self.SetKeys("Symbols")
            return

        if self.active_line_edit is None:
            return

        if "Back" in self.sender().objectName():
            text = self.active_line_edit.text()
            self.active_line_edit.setText(text[:-1])
        else:
            text = self.active_line_edit.text()
            self.active_line_edit.setText(text + self.sender().text())

    def show_keyboard(self):
        self.ui.Keyboard.show()

    def ResetKeyboard(self):
        self.ui.Keyboard.hide()
        if self.ui.Btn_Symbols.isChecked():
            self.ui.Btn_Symbols.toggle()
        if not self.ui.Btn_Caps.isChecked():
            self.ui.Btn_Caps.toggle()
        self.SetKeys("Caps")

    def ShowPassword(self):
        if self.ui.btn_show_wifi.isChecked():
            self.ui.password_lineEdit.setEchoMode(QtWidgets.QLineEdit.Normal)
        else:
            self.ui.password_lineEdit.setEchoMode(QtWidgets.QLineEdit.Password)

    # ========================
    #     Input Focus
    # ========================

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if obj in [self.ui.host_lineEdit, self.ui.user_lineEdit, self.ui.password_lineEdit]:
                self.active_line_edit = obj
                self.show_keyboard()
        return super(MainWindow, self).eventFilter(obj, event)

    def mousePressEvent(self, event):
        if QApplication.focusWidget():
            QApplication.focusWidget().clearFocus()

    def mouseReleaseEvent(self, QMouseEvent):
        pass  # Placeholder for future logic

    # ========================
    #       MQTT Actions
    # ========================

    def Connect(self):
        # Get connection parameters from UI
        mqtt_username = self.ui.user_lineEdit.text()
        mqtt_password = self.ui.password_lineEdit.text()
        mqtt_broker = self.ui.host_lineEdit.text()
        
        # Validate inputs
        if not mqtt_broker:
            self.ui.Authentification_label.setText("Please enter a broker host.")
            self.ui.Authentification_label.show()
            return
        
        # Attempt connection
        try:
            rc = self.mqtt_client.connect_to_broker(mqtt_broker, mqtt_port, mqtt_username, mqtt_password)
            
            # Handle connection result
            if rc == 0:
                print("Connection successful")
                self.ui.Authentification_label.hide()
                self.goToScreenProject()
            elif rc == 1:
                self.ui.Authentification_label.setText("Connection refused - incorrect protocol version.")
                self.ui.Authentification_label.show()
            elif rc == 5:
                self.ui.Authentification_label.setText("Connection refused - bad username or password.")
                self.ui.Authentification_label.show()
            elif rc == -1:
                self.ui.Authentification_label.setText("Connection error: could not reach host.")
                self.ui.Authentification_label.show()
            else:
                self.ui.Authentification_label.setText(f"Connection failed with code {rc}")
                self.ui.Authentification_label.show()
                
        except Exception as e:
            print(f"Connection error: {e}")
            self.ui.Authentification_label.setText(f"Connection error: {str(e)}")
            self.ui.Authentification_label.show()



    def Disconnect(self):
        """Handle MQTT disconnection"""
        print("Disconnect")
        self.mqtt_client.disconnect_from_broker()

    # ========================
    #     Navigation Logic
    # ========================

    def GotoScreen(self, index):
        self.ui.stackedWidget.setCurrentIndex(index)

    def goToHome(self):
        self.GotoScreen(screen_home)

    def goToScreenProject(self):
        self.deactivate_current_project()
        self.GotoScreen(screen_project)

    def deactivate_current_project(self):
        if self.current_project and hasattr(self.current_project, "deactivate"):
            self.current_project.deactivate()
        self.current_project = None

    def goToScreenButton(self):
        self.GotoScreen(screen_button)
        self.current_project = LED_and_Button(self.mqtt_client, self.ui)

    def goToScreenWather(self):
        self.GotoScreen(screen_wather)
        self.current_project = Tem_hum_Sensor(self.mqtt_client, self.ui)

    def goToScreenSensor(self):
        self.GotoScreen(screen_sensor)
        self.current_project = WaterLevelControllerWindow(self.mqtt_client, self.ui)

    def goToScreenLoadCell(self):
        self.GotoScreen(screen_load_cell)
        self.current_project = LOADCELL(self.mqtt_client, self.ui)

    def goToScreenAccelo(self):
        self.GotoScreen(screen_accelo)
        self.current_project = AccelerometerGyroscopeController(self.mqtt_client, self.ui)

    def goToScreenGasSensor(self):
        self.GotoScreen(screen_gas_sensor)
        self.current_project = GasSensorController(self.mqtt_client, self.ui)


# ========================
#       Main Entry
# ========================

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QIcon("demo.ico"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
