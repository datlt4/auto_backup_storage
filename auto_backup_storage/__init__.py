import os
from .auto_backup_storage import *

# Get the path to the VERSION file
version_file = os.path.join(os.path.dirname(__file__), "package_version.txt")

# Read the version from the VERSION file
with open(version_file) as f:
    __version__ = f.read().strip()
