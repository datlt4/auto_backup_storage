# Setup dev environment

```bash
python3 -m pip install -r requirements.txt
pre-commit install
```

# Run application

1. Backup

    ```bash
    python3 -c "\
    from auto_backup_storage import process_pair_in_pool;\
    source_destination_pairs = [\
        ('/mnt/C67881AE78819DB5/PIXAR/Vizgard/', '/mnt/90848C74848C5F1A/Vizgard/',),\
        ('/mnt/C67881AE78819DB5/DISNEY/', '/mnt/404A81F44A81E74E/DISNEY/',),\
        ('/mnt/C67881AE78819DB5/Downloads-Windows/', '/mnt/404A81F44A81E74E/Downloads-Windows/',),\
        ('/mnt/00AE2C6B5AC8D335/', '/mnt/404A81F44A81E74E/365GB-SSD/',),\
        ('/mnt/C67881AE78819DB5/PIXAR/', '/mnt/404A81F44A81E74E/PIXAR/',),\
        ('/home/emoi/Downloads/', '/mnt/404A81F44A81E74E/Downloads-Ubuntu/',),\
        ('/mnt/90848C74848C5F1A/4k/', '/mnt/404A81F44A81E74E/1TB-HDD/4K-videos',),\
        ('/mnt/90848C74848C5F1A/8k/', '/mnt/404A81F44A81E74E/1TB-HDD/8K-videos',),\
    ];\
    process_pair_in_pool(source_destination_pairs);"
    ```

```bash
python3 -c "\
from auto_backup_storage import process_pair_in_pool;\
source_destination_pairs = [\
    ('/home/emoi/Downloads/Boost.Asio.Cpp.Network.Programming.Cookbook/', '/mnt/404A81F44A81E74E/Boost.Asio.Cpp.Network.Programming.Cookbook/',),\
];\
process_pair_in_pool(source_destination_pairs);"
```


2. Restore

    - reverse source path, destination path

# Build package

```bash
python3 setup.py sdist bdist_wheel
```

# Publish package to Pypi

```bash
twine upload dist/*
```

# Setup daemon

```bash
sudo nano /etc/systemd/system/auto-backup-storage.service
```

```yml
[Unit]
Description=Daemon for serving auto-backup-storage
After=network.target

[Service]
User=1000
Group=1000
ExecStart=/bin/bash -c "\
/home/emoi/anaconda3/bin/python3 -m pip install --upgrade auto-backup-storage && \
/home/emoi/anaconda3/bin/python3 -c 'from auto_backup_storage import process_pair_in_pool; source_destination_pairs = [\
    (\"/mnt/C67881AE78819DB5/PIXAR/Vizgard/\", \"/mnt/90848C74848C5F1A/Vizgard/\"),\
    (\"/mnt/C67881AE78819DB5/DISNEY/\", \"/mnt/404A81F44A81E74E/DISNEY/\"),\
    (\"/mnt/C67881AE78819DB5/Downloads-Windows/\", \"/mnt/404A81F44A81E74E/Downloads-Windows/\"),\
    (\"/mnt/00AE2C6B5AC8D335/\", \"/mnt/404A81F44A81E74E/365GB-SSD/\"),\
    (\"/mnt/C67881AE78819DB5/PIXAR/\", \"/mnt/404A81F44A81E74E/PIXAR/\"),\
    (\"/home/emoi/Downloads/\", \"/mnt/404A81F44A81E74E/Downloads-Ubuntu/\"),\
    (\"/mnt/90848C74848C5F1A/4k/\", \"/mnt/404A81F44A81E74E/1TB-HDD/4K-videos\"),\
    (\"/mnt/90848C74848C5F1A/8k/\", \"/mnt/404A81F44A81E74E/1TB-HDD/8K-videos\")]; \
process_pair_in_pool(source_destination_pairs);'"
ExecReload=/usr/bin/kill -s HUP $MAINPID
Restart=always
# RestartSec=60

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl status auto-backup-storage.service
sudo journalctl -u auto-backup-storage.service

sudo systemctl start auto-backup-storage.service
sudo systemctl restart auto-backup-storage.service
sudo systemctl stop auto-backup-storage.service

sudo systemctl enable auto-backup-storage.service
sudo systemctl is-enabled auto-backup-storage.service
sudo systemctl disable auto-backup-storage.service
```

# Executable file

From v0.1.6 I can backup with executable file

```bash
auto_backup_storage /path/to/source /path/to/destination
```
