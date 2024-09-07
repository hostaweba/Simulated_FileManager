import os
import subprocess
import shutil
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QVBoxLayout, QWidget, QLabel, QTreeView, 
                                QAbstractItemView, QMenu, QMessageBox)
from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QStandardItemModel, QStandardItem
import csv
import re

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
            
    #-----------tree start
    def display_structure(self, file_name):
        # Clear current model
        self.model.clear()
        self.model.setHorizontalHeaderLabels(['File Path', 'File Size (MB)'])

        # Prepare data
        directories = set()
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

                # Determine if it's a file or directory
                if os.path.isdir(path):
                    # Add directory to set
                    directories.add(path)
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
        
        # Create root item
        root_item = self.model.invisibleRootItem()
        
        # Create a dictionary to track directory paths
        path_to_item = {}
        path_to_item[''] = root_item

        # Process directories to create the hierarchy
        for directory in sorted(directories):
            path_parts = os.path.normpath(directory).split(os.sep)
            parent_item = root_item
            
            current_path = ''
            for part in path_parts:
                current_path = os.path.join(current_path, part)
                if current_path not in path_to_item:
                    dir_item = add_item(parent_item, current_path)
                    path_to_item[current_path] = dir_item
                parent_item = path_to_item[current_path]
        
        # Add files to model
        for file_path, size_mb in sorted(files):
            path_parts = os.path.normpath(file_path).split(os.sep)
            parent_item = root_item
            current_path = ''
            
            for part in path_parts[:-1]:
                current_path = os.path.join(current_path, part)
                if current_path not in path_to_item:
                    dir_item = add_item(parent_item, current_path)
                    path_to_item[current_path] = dir_item
                parent_item = path_to_item[current_path]
            
            # Add the file item
            add_item(parent_item, path_parts[-1], size_mb)

        self.status_label.setText("Directory structure displayed.")

    #-------------------------------tree end 
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
        # Convert the file path to match the CSV format
        formatted_file_path = self.format_path_for_comparison(file_path)
        
        confirm = QMessageBox.question(self, 'Delete Confirmation',
                                       f"Are you sure you want to remove the address '{formatted_file_path}'?",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            # Remove the item from the model
            parent_item = item.parent()
            if parent_item:
                parent_item.removeRow(item.row())
                self.status_label.setText(f"Address '{formatted_file_path}' removed.")
                
                # Update the CSV file to remove the address
                self.update_csv(formatted_file_path)


    def update_csv(self, path_pattern: str):
        if not self.current_file:
            print("No current file loaded.")
            return

        formatted_pattern = self.format_path_for_comparison(path_pattern)
        print(f"Formatted path pattern to remove: '{formatted_pattern}'")

        try:
            # Read current CSV data
            df = pd.read_csv(self.current_file)
            df['File Path'] = df['File Path'].str.strip()  # Strip any extra spaces

            # Escape backslashes in the path pattern for regex usage
            escaped_pattern = re.escape(formatted_pattern)

            # Debugging: Print the paths in the CSV and the path pattern to remove
            print("Paths in CSV file:")
            print(df['File Path'].tolist())
            print(f"Path pattern to remove: '{escaped_pattern}'")

            # Remove rows based on the pattern
            # Match full paths and directories
            if formatted_pattern.endswith("\\"):
                # If pattern is a directory (ends with a backslash), remove all rows starting with that path
                df = df[~df['File Path'].str.startswith(formatted_pattern)]
            else:
                # Otherwise, match exact file or directory
                df = df[~df['File Path'].str.contains(escaped_pattern, regex=True)]

            # Debugging: Print the DataFrame before and after removal
            print("Dataframe before removal:")
            print(df.copy())
            print("Dataframe after removal:")
            print(df)

            # Write updated data to a temporary file
            temp_file = self.current_file + ".tmp"
            df.to_csv(temp_file, index=False)

            # Replace original file with updated file
            shutil.move(temp_file, self.current_file)

            # Print to terminal
            print(f"Updated CSV data:\n{self.read_csv(self.current_file)}")

        except Exception as e:
            print(f"Error updating CSV: {str(e)}")
            # Clean up temp file if it exists
            if os.path.exists(temp_file):
                os.remove(temp_file)



    def format_path_for_comparison(self, path: str) -> str:
        abs_path = os.path.abspath(path)
        rel_path = os.path.relpath(abs_path, start=os.path.abspath(os.path.dirname(self.current_file)))
        formatted_path = '.\\' + rel_path.replace(os.path.sep, '\\').replace('..\\', '')
        return formatted_path



    def read_csv(self, file_path):
        try:
            df = pd.read_csv(file_path)
            return df.to_string(index=False)
        except Exception as e:
            print(f"Error reading CSV: {str(e)}")
            return ""


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
