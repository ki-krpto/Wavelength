# RUN THIS ONLY TO CLEAN UP THE NESTED PNG FOLDERS
from pathlib import Path
import shutil

# Target the specific messy folder
messy_folder = Path(r"C:\Users\aj\Documents\Wavelength\assets\games\gn")

# Find every image deep inside the tunnels
for image in list(messy_folder.rglob('*.png')):
    # Move them back to the root of 'gn'
    destination = messy_folder / image.name
    if image != destination:
        shutil.move(str(image), str(destination))

print("Files rescued. You can now delete the empty 'png' folders manually.")