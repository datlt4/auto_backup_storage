from setuptools import setup, find_packages

setup(
    name="auto_backup_storage",
    version="0.1.6",
    description="A Python script for backing up and synchronizing data between SSD and HDD with CPU usage monitoring.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Koi",
    author_email="your.email@example.com",
    url="https://github.com/datlt4/auto_backup_storage",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "auto_backup_storage=auto_backup_storage.cli:backup",
        ],
    },
    install_requires=["psutil"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
