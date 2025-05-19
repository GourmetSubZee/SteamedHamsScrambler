# utils.py
import os
import shutil

def clean_output(output_dir_name):
    # Get the project root (one level above the current file's directory)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_dir = os.path.join(project_root, output_dir_name)
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            file_path = os.path.join(output_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")
        print("Output folder cleaned.")
    else:
        print("Output folder does not exist.")

def create_incremental_filename(output_dir, base_name, extension):
    # Create an incremental filename that appends the next number based on existing files
    existing_files = [f for f in os.listdir(output_dir) if f.startswith(base_name) and f.endswith(extension)]
    if not existing_files:
        return os.path.join(output_dir, f"{base_name}_001{extension}")

    existing_numbers = []
    for filename in existing_files:
        number_part = filename[len(base_name):-len(extension)].strip('_')
        if number_part.isdigit():
            existing_numbers.append(int(number_part))

    next_number = max(existing_numbers) + 1 if existing_numbers else 1
    return os.path.join(output_dir, f"{base_name}_{next_number:03d}{extension}")