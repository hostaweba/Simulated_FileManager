import csv
import os
import subprocess
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QFileDialog, QVBoxLayout, QWidget, QLabel, QTreeView, 
                                QAbstractItemView, QMenu, QMessageBox)
from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QStandardItemModel, QStandardItem

class FileAddressManager(QMainWindow):
    def __init__(self):
        super().__init__()

        self.current_file = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("File Address Manager")
        self.setGeometry(100, 100, 800, 600)

        # Create a central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout()

        # Label to show status
        self.status_label = QLabel("Load CSV file to display directory structure.")
        layout.addWidget(self.status_label)

        # TreeView to show directory structure
        self.tree_view = QTreeView()
        self.tree_view.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Prevent editing
        layout.addWidget(self.tree_view)

        # Set layout
        central_widget.setLayout(layout)

        # Initialize the model
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['File Path', 'File Size (MB)'])
        self.tree_view.setModel(self.model)

        # Connect double-click event
        self.tree_view.doubleClicked.connect(self.on_item_double_clicked)

        # Connect right-click event
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)

        # Menu bar setup
        self.menu_bar = self.menuBar()
        self.files_menu = self.menu_bar.addMenu("Files")

        # Add "Load CSV" action to menu
        self.load_action = self.files_menu.addAction("Load CSV")
        self.load_action.triggered.connect(self.load_csv)

        # Add "Save Updated Data to CSV" action to menu
        self.save_action = self.files_menu.addAction("Save Updated Data to CSV")
        self.save_action.triggered.connect(self.write_updated_data_to_csv)

    def load_csv(self):
        # Open file dialog to select CSV
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv);;All Files (*)", options=options)

        if file_name:
            self.current_file = file_name
            self.display_structure(file_name)

    def display_structure(self, file_name):
        # Clear current model
        self.model.clear()
        self.model.setHorizontalHeaderLabels(['File Path', 'File Size (MB)'])

        directories = {}
        files = []

        # Read CSV and process paths
        with open(file_name, 'r') as file:
            reader = csv.reader(file)
            header = next(reader)  # Read header
            for row in reader:
                if len(row) < 2:
                    continue
                path = row[0].strip()
                try:
                    size_mb = float(row[1].strip())
                except ValueError:
                    size_mb = 0.0

                if not path:
                    continue

                # Add to directories or files list
                if os.path.isdir(path):
                    directories[path] = size_mb
                else:
                    files.append((path, size_mb))

        # Create a map to store model items for directories
        directory_items = {}

        def add_item(parent_item, path, size_mb=None):
            item = QStandardItem(os.path.basename(path))
            item.setEditable(False)
            size_item = QStandardItem(f"{size_mb:.2f}" if size_mb is not None else "")
            parent_item.appendRow([item, size_item])
            return item

        # Add directory structure to model
        root_item = self.model.invisibleRootItem()
        for directory in sorted(directories):
            path_parts = os.path.relpath(directory, start=os.path.dirname(file_name)).split(os.sep)
            parent_item = root_item
            for part in path_parts:
                if part not in directory_items:
                    dir_item = add_item(parent_item, os.path.join(os.path.dirname(directory), part))
                    directory_items[part] = dir_item
                parent_item = directory_items[part]

        # Add files to model
        for file_path, size_mb in sorted(files):
            path_parts = os.path.relpath(file_path, start=os.path.dirname(file_name)).split(os.sep)
            parent_item = root_item
            for part in path_parts[:-1]:
                if part not in directory_items:
                    dir_item = add_item(parent_item, os.path.join(os.path.dirname(file_path), part))
                    directory_items[part] = dir_item
                parent_item = directory_items[part]
            add_item(parent_item, os.path.basename(file_path), size_mb)

        self.status_label.setText("Directory structure displayed.")

    def on_item_double_clicked(self, index: QModelIndex):
        item = self.model.itemFromIndex(index)
        file_path = self.get_full_path(item)
        
        if os.path.isfile(file_path):
            self.open_file(file_path)

    def show_context_menu(self, position):
        index = self.tree_view.indexAt(position)
        item = self.model.itemFromIndex(index)
        if not item:
            return

        file_path = self.get_full_path(item)
        
        menu = QMenu(self)
        
        # Create actions
        open_action = menu.addAction("Open")
        delete_action = menu.addAction("Delete")
        
        # Connect actions
        open_action.triggered.connect(lambda: self.open_file(file_path))
        delete_action.triggered.connect(lambda: self.delete_item(file_path, item))
        
        # Show the context menu
        menu.exec(self.tree_view.viewport().mapToGlobal(position))

    def delete_item(self, file_path: str, item: QStandardItem):
        confirm = QMessageBox.question(self, 'Delete Confirmation', f"Are you sure you want to remove the address '{file_path}'?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            # Remove the item from the model
            parent_item = item.parent()
            if parent_item:
                parent_item.removeRow(item.row())
                self.status_label.setText(f"Address '{file_path}' removed.")
                
                # Update the CSV file to remove the address
                self.update_csv(file_path)

    def update_csv(self, file_path: str):
        if not self.current_file:
            return
        
        temp_file = self.current_file + ".tmp"
        
        # Read current CSV data and write to temp file
        with open(self.current_file, 'r') as read_file, open(temp_file, 'w', newline='') as write_file:
            reader = csv.reader(read_file)
            writer = csv.writer(write_file)
            
            header = next(reader)
            writer.writerow(header)  # Write header
            
            # Write all rows except the deleted one
            for row in reader:
                if len(row) > 0 and row[0].strip() != file_path:
                    writer.writerow(row)
        
        # Replace original file with updated file
        os.replace(temp_file, self.current_file)
        
        # Print to terminal
        print(f"Updated CSV data: {self.read_csv(self.current_file)}")

    def read_csv(self, file_name):
        with open(file_name, 'r') as file:
            return list(csv.reader(file))

    def get_full_path(self, item: QStandardItem) -> str:
        path_parts = []
        while item:
            path_parts.append(item.text())
            item = item.parent()
        path_parts.reverse()
        # Construct path with the same format used in the CSV
        return os.path.normpath(os.path.join(os.path.dirname(self.current_file), *path_parts))

    def open_file(self, file_path: str):
        if os.name == 'nt':  # For Windows
            os.startfile(file_path)
        else:
            try:
                subprocess.run(['xdg-open', file_path], check=True)  # For Unix-based systems
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")

    def write_updated_data_to_csv(self):
        QMessageBox.warning(self, "Warning", "This function is not implemented in the current code.")
        # Uncomment and implement this method if you need to save updates to CSV.

if __name__ == "__main__":
    app = QApplication([])
    window = FileAddressManager()
    window.show()
    app.exec()
