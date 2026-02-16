"""Application theme and stylesheet for RESA Pro GUI."""

STYLESHEET = """
QMainWindow {
    background-color: #1e1e2e;
}
QTabWidget::pane {
    border: 1px solid #3b3b5c;
    background-color: #1e1e2e;
}
QTabBar::tab {
    background-color: #2b2b3d;
    color: #cdd6f4;
    padding: 8px 16px;
    border: 1px solid #3b3b5c;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
    font-size: 11px;
}
QTabBar::tab:selected {
    background-color: #313244;
    color: #89b4fa;
    border-bottom: 2px solid #89b4fa;
}
QTabBar::tab:hover {
    background-color: #363650;
}
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-size: 11px;
}
QGroupBox {
    border: 1px solid #3b3b5c;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
    color: #89b4fa;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QPushButton {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: bold;
    font-size: 11px;
    min-height: 28px;
}
QPushButton:hover {
    background-color: #a6c8ff;
}
QPushButton:pressed {
    background-color: #6b9bea;
}
QPushButton:disabled {
    background-color: #45475a;
    color: #6c7086;
}
QPushButton[secondary="true"] {
    background-color: #45475a;
    color: #cdd6f4;
}
QPushButton[secondary="true"]:hover {
    background-color: #585b70;
}
QDoubleSpinBox, QSpinBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #3b3b5c;
    border-radius: 3px;
    padding: 3px 6px;
    min-height: 22px;
}
QDoubleSpinBox:focus, QSpinBox:focus {
    border: 1px solid #89b4fa;
}
QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #3b3b5c;
    border-radius: 3px;
    padding: 3px 6px;
    min-height: 22px;
}
QComboBox:focus {
    border: 1px solid #89b4fa;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #313244;
    color: #cdd6f4;
    selection-background-color: #45475a;
    border: 1px solid #3b3b5c;
}
QTableWidget {
    background-color: #181825;
    alternate-background-color: #1e1e2e;
    color: #cdd6f4;
    gridline-color: #313244;
    border: 1px solid #3b3b5c;
    border-radius: 3px;
    font-size: 11px;
}
QTableWidget::item {
    padding: 2px 6px;
}
QHeaderView::section {
    background-color: #313244;
    color: #89b4fa;
    padding: 4px 6px;
    border: none;
    border-bottom: 1px solid #3b3b5c;
    font-weight: bold;
    font-size: 10px;
}
QPlainTextEdit {
    background-color: #181825;
    color: #a6e3a1;
    border: 1px solid #3b3b5c;
    border-radius: 3px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 10px;
}
QLabel {
    color: #cdd6f4;
}
QScrollBar:vertical {
    background-color: #1e1e2e;
    width: 10px;
}
QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background-color: #1e1e2e;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background-color: #45475a;
    border-radius: 4px;
    min-width: 20px;
}
QSplitter::handle {
    background-color: #3b3b5c;
}
QStatusBar {
    background-color: #181825;
    color: #6c7086;
    font-size: 10px;
}
"""
