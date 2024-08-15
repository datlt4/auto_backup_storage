import sys
import os
import shutil
import random
import hashlib
import psutil
import time
import threading
import logging
import multiprocessing
import socket
from queue import Queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

ONE_MEGABYTE = 1024 * 1024
NUM_RANDOM_BYTES = ONE_MEGABYTE
LIMIT_IGNORE_CALCULATE_LARGE_FILE = 100 * ONE_MEGABYTE
LIMIT_MAX_CPU_USAGE = 80  # %
PSUTIL_ITERVAL = 0.1
SOCKET_PORT = 65432


def is_binary(file_path: str):
    with open(file_path, "rb") as file:
        for byte in file.read(1024):  # Check the first 1024 bytes
            if byte > 127:
                return True
    return False


def calculate_hash(file_path: str):
    hash_algo = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_algo.update(chunk)
    return hash_algo.hexdigest()


def compare_large_files(src: str, dst: str, num_bytes: int = NUM_RANDOM_BYTES):
    if not os.path.exists(dst) or os.path.getsize(src) != os.path.getsize(dst):
        return False

    src_size = os.path.getsize(src)
    if src_size < num_bytes:
        return False

    positions = random.sample(range(src_size - num_bytes), 10)
    with open(src, "rb") as sf, open(dst, "rb") as df:
        for pos in positions:
            sf.seek(pos)
            df.seek(pos)
            if sf.read(num_bytes) != df.read(num_bytes):
                return False

    return True


def files_are_identical(src: str, dst: str):
    if not os.path.exists(dst):
        return False

    src_size = os.path.getsize(src)
    dst_size = os.path.getsize(dst)

    if src_size != dst_size:
        return False

    if is_binary(src) and src_size > LIMIT_IGNORE_CALCULATE_LARGE_FILE:
        return compare_large_files(src, dst)
    else:
        return calculate_hash(src) == calculate_hash(dst)


def copy_file(src: str, dst: str):
    try:
        logging.info(f"Copying file from {src} to {dst}")
        shutil.copy2(src, dst)
    except FileNotFoundError:
        logging.error(f"File not found during copy: {src}")
    except Exception as e:
        logging.error(f"Error copying file {src} to {dst}: {e}")
        with open(src, "rb") as sf, open(dst, "wb") as df:
            for chunk in iter(lambda: sf.read(4096), b""):
                df.write(chunk)


def check_cpu_usage(cpu_threshold: float = LIMIT_MAX_CPU_USAGE):
    curren_cpu_usage = psutil.cpu_percent(PSUTIL_ITERVAL)
    if curren_cpu_usage > cpu_threshold:
        logging.warning(f"High CPU usage ({curren_cpu_usage}%), pausing sync")
        time.sleep(3)


def process_file(file_task_queue: Queue, cpu_threshold: float = LIMIT_MAX_CPU_USAGE):
    while True:
        src_file, dst_file = file_task_queue.get()
        if not src_file:
            file_task_queue.task_done()
            break

        curren_cpu_usage = psutil.cpu_percent(PSUTIL_ITERVAL)
        while curren_cpu_usage > cpu_threshold:
            logging.warning(f"High CPU usage ({curren_cpu_usage}%), pausing sync")
            time.sleep(3)
            curren_cpu_usage = psutil.cpu_percent(PSUTIL_ITERVAL)

        try:
            if not files_are_identical(src_file, dst_file):
                logging.info(
                    f"File {src_file} is different from {dst_file}, copying..."
                )
                copy_file(src_file, dst_file)
        except FileNotFoundError:
            logging.error(f"File not found during processing: {src_file}")

        file_task_queue.task_done()
        logging.info(f"Processed file: {src_file}, CPU usage {curren_cpu_usage}%")


def process_directory(
    dir_task_queue: Queue, cpu_threshold: float = LIMIT_MAX_CPU_USAGE
):
    while True:
        dst_folder = dir_task_queue.get()
        if not dst_folder:
            dir_task_queue.task_done()
            break

        curren_cpu_usage = psutil.cpu_percent(PSUTIL_ITERVAL)
        while curren_cpu_usage > cpu_threshold:
            logging.warning(f"High CPU usage ({curren_cpu_usage}%), pausing sync")
            time.sleep(3)
            curren_cpu_usage = psutil.cpu_percent(PSUTIL_ITERVAL)

        if not os.path.exists(dst_folder):
            os.makedirs(dst_folder)
            logging.info(f"Created directory {dst_folder}")

        dir_task_queue.task_done()
        logging.info(
            f"Processed directory: {dst_folder}, CPU usage {curren_cpu_usage}%"
        )


def sync_directories(
    src_dir: str, dst_dir: str, cpu_threshold: float = LIMIT_MAX_CPU_USAGE
):
    file_task_queue = Queue()
    dir_task_queue = Queue()

    # Process source files and directories
    for root, dirs, files in os.walk(src_dir):
        for file_name in (os.path.join(root, f) for f in files):
            src_file = file_name
            rel_path = os.path.relpath(src_file, src_dir)
            dst_file = os.path.join(dst_dir, rel_path)
            file_task_queue.put((src_file, dst_file))

        for dir_name in (os.path.join(root, d) for d in dirs):
            src_folder = dir_name
            rel_path = os.path.relpath(src_folder, src_dir)
            dst_folder = os.path.join(dst_dir, rel_path)
            dir_task_queue.put(dst_folder)

    # Check and remove extra files and directories in the destination
    for root, dirs, files in os.walk(dst_dir):
        for dst_file in files:
            rel_path = os.path.relpath(os.path.join(root, dst_file), dst_dir)
            src_file = os.path.join(src_dir, rel_path)

            try:
                if not os.path.exists(src_file):
                    os.remove(os.path.join(root, dst_file))
                    logging.info(f"Removed extra file {os.path.join(root, dst_file)}")
            except FileNotFoundError:
                logging.error(
                    f"File not found during removal: {os.path.join(root, dst_file)}"
                )

        for dst_folder in dirs:
            rel_path = os.path.relpath(os.path.join(root, dst_folder), dst_dir)
            src_folder = os.path.join(src_dir, rel_path)

            try:
                if not os.path.exists(src_folder):
                    shutil.rmtree(os.path.join(root, dst_folder))
                    logging.info(
                        f"Removed extra directory {os.path.join(root, dst_folder)}"
                    )
            except FileNotFoundError:
                logging.error(
                    f"Directory not found during removal: {os.path.join(root, dst_folder)}"
                )

    # Start file and directory processing threads
    for _ in range(multiprocessing.cpu_count()):
        file_task_queue.put((None, None))
        dir_task_queue.put(None)

    threads = []
    for _ in range(multiprocessing.cpu_count()):
        t_file = threading.Thread(
            target=process_file, args=(file_task_queue, cpu_threshold)
        )
        t_dir = threading.Thread(
            target=process_directory, args=(dir_task_queue, cpu_threshold)
        )
        t_file.start()
        t_dir.start()
        threads.extend([t_file, t_dir])

    file_task_queue.join()
    dir_task_queue.join()

    for t in threads:
        t.join()


def process_pair(pair: list[str]):
    src_dir, dst_dir = pair
    logger = logging.getLogger(f"Process-{src_dir}-{dst_dir}")
    logger.info(f"Starting process for {src_dir} to {dst_dir}")
    sync_directories(src_dir, dst_dir)
    logger.info(f"Ending process for {src_dir} to {dst_dir}")


def create_socket_lock(port: int):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("localhost", port))
        logging.info(f"Acquired socket lock on port {port}")
        return s
    except socket.error as e:
        logging.error(f"Socket lock failed: {e}")
        sys.exit(1)  # Exit if unable to acquire the lock


def process_pair_in_pool(source_destination_pairs: list):
    # Acquire a socket lock to prevent multiple instances
    lock_socket = create_socket_lock(SOCKET_PORT)

    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        pool.map(process_pair, source_destination_pairs)

    # Release the socket lock by closing the socket
    lock_socket.close()


if __name__ == "__main__":
    source_destination_pairs = [
        (
            "/home/emoi/Downloads/Miscellaneous/",
            "/mnt/90848C74848C5F1A/backup_miscellaneous",
        ),
        (
            "/mnt/C67881AE78819DB5/PIXAR/Vizgard/vizgard2",
            "/mnt/90848C74848C5F1A/backup_vizgard2/",
        ),
        # Add more pairs as needed
    ]

    process_pair_in_pool(source_destination_pairs)
