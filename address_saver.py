import os
import csv

# Function to get all file paths and their sizes in MB
def get_file_paths_and_sizes(directory):
    file_info = []
    # Walk through all directories and files
    for root, dirs, files in os.walk(directory):
        # Skip the entire directory structure if the folder name starts with "_[sys]_"
        dirs[:] = [d for d in dirs if not d.startswith("_[sys]_")]

        # Collect file paths and sizes
        for file in files:
            full_path = os.path.join(root, file)
            size_mb = os.path.getsize(full_path) / (1024 * 1024)  # Size in MB
            file_info.append((full_path, round(size_mb, 2)))  # Round size to 2 decimal places
    
    return file_info

# Function to save file paths and sizes to a CSV file
def save_paths_and_sizes_to_csv(file_info, csv_file):
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        # Writing header
        writer.writerow(['File Path', 'Size (MB)'])
        # Writing all file paths and sizes
        for path, size in file_info:
            writer.writerow([path, size])

# Replace '.' with the path to the folder you want to scan
directory = '.'

# Set the output CSV file name
csv_file = 'file_addresses.csv'

# Get file paths and sizes and save to CSV
file_info = get_file_paths_and_sizes(directory)
save_paths_and_sizes_to_csv(file_info, csv_file)

print(f"File paths and sizes have been written to {csv_file}")
