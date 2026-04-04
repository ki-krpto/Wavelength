import shutil
from pathlib import Path

def sort_images_nested(root_path):
    base_dir = Path(root_path)
    extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    # Common folder names to skip so we don't recurse
    protected_folders = {'jpg', 'jpeg', 'png', 'webp'}

    # CRITICAL: We use list() to freeze the file list so it doesn't 
    # see new folders we create during the loop.
    all_files = list(base_dir.rglob('*'))

    for file_path in all_files:
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            
            # Check if the file is already inside a sorted folder (like \png\)
            if file_path.parent.name.lower() in protected_folders:
                continue

            ext_folder_name = file_path.suffix.lower().replace('.', '')
            target_folder = file_path.parent / ext_folder_name
            
            target_folder.mkdir(exist_ok=True)
            destination = target_folder / file_path.name
            
            try:
                # Use move, but ensure we don't move a file onto itself
                if file_path != destination:
                    shutil.move(str(file_path), str(destination))
                    print(f"Moved: {file_path.name} -> {target_folder.relative_to(base_dir)}")
            except Exception as e:
                print(f"Error moving {file_path.name}: {e}")

if __name__ == "__main__":
    folder_to_sort = r"C:\Users\aj\Documents\Wavelength\assets"
    sort_images_nested(folder_to_sort)