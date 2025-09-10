from PySide6.QtCore import Qt
from qfluentwidgets import SearchLineEdit


class CustomSearchLineEdit(SearchLineEdit):
    """ Search line edit with Enter key support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        #self.returnPressed.connect(self.search)

    def keyPressEvent(self, event):
        """ Override keyPressEvent to prevent focus loss on Enter key """
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.search()
            event.accept()
            self.setFocus()
        else:
            super().keyPressEvent(event)