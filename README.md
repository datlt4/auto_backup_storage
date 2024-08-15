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
        (\
            '/home/emoi/Downloads/',\
            '/mnt/404A81F44A81E74E/Linux/Downloads/',\
        ),\
        (\
            '/mnt/C67881AE78819DB5/DISNEY/',\
            '/mnt/404A81F44A81E74E/DISNEY/',\
        ),\
        (\
            '/mnt/C67881AE78819DB5/Downloads-Windows/',\
            '/mnt/404A81F44A81E74E/Downloads-Windows/',\
        ),\
        (\
            '/mnt/00AE2C6B5AC8D335/',\
            '/mnt/404A81F44A81E74E/365GB-SSD/',\
        ),\
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

```yaml
[Unit]
Description=Daemon for serving auto-backup-storage
After=network.target

[Service]
User=1000
Group=1000
ExecStart=/bin/bash -c '/home/emoi/anaconda3/bin/python3 -m pip install --upgrade auto-backup-storage && /home/emoi/anaconda3/bin/python3 -c "from auto_backup_storage import auto_backup_storage; auto_backup_storage()"'
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
