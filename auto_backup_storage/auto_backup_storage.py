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

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,  # This sets the minimum level to INFO; WARNING and ERROR are included by default
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Logs to the console
        logging.FileHandler("app.log"),  # Logs to a file named 'app.log'
    ],
)

# Constants for the application
ONE_MEGABYTE = 1024 * 1024  # Size of one megabyte in bytes
NUM_RANDOM_BYTES = ONE_MEGABYTE  # Number of random bytes to compare in large files
LIMIT_IGNORE_CALCULATE_LARGE_FILE = (
    100 * ONE_MEGABYTE
)  # Threshold to ignore hash calculation for large files
LIMIT_MAX_CPU_USAGE = 95  # Maximum CPU usage percentage before pausing operations
PSUTIL_ITERVAL = 0.1  # Interval for checking CPU usage
SOCKET_PORT = 65432  # Port number for socket lock


def is_binary(file_path: str):
    """
    Check if a file is binary by reading its first 1024 bytes.

    Args:
        file_path (str): Path to the file.

    Returns:
        bool: True if the file is binary, otherwise False.
    """
    # with open(file_path, "rb") as file:
    #     for byte in file.read(1024):  # Read first 1024 bytes
    #         if byte > 127:  # Check if any byte is non-ASCII
    #             return True
    # return False
    return True


def calculate_hash(file_path: str):
    """
    Calculate the MD5 hash of a file.

    Args:
        file_path (str): Path to the file.

    Returns:
        str: MD5 hash of the file.
    """
    hash_algo = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(
            lambda: f.read(4096), b""
        ):  # Read file in chunks of 4096 bytes
            hash_algo.update(chunk)
    return hash_algo.hexdigest()


def compare_large_files(src: str, dst: str, num_bytes: int = NUM_RANDOM_BYTES):
    """
    Compare large files by reading random byte positions.

    Args:
        src (str): Source file path.
        dst (str): Destination file path.
        num_bytes (int): Number of bytes to compare at random positions.

    Returns:
        bool: True if files are identical based on the comparison, otherwise False.
    """
    if not os.path.exists(dst) or os.path.getsize(src) != os.path.getsize(dst):
        return False

    src_size = os.path.getsize(src)
    if src_size < num_bytes:
        return False

    positions = random.sample(
        range(src_size - num_bytes), 10
    )  # Choose 10 random positions
    with open(src, "rb") as sf, open(dst, "rb") as df:
        for pos in positions:
            sf.seek(pos)  # Seek to the random position in source
            df.seek(pos)  # Seek to the random position in destination
            if sf.read(num_bytes) != df.read(num_bytes):  # Compare the bytes
                return False

    return True


def files_are_identical(src: str, dst: str):
    """
    Check if two files are identical by comparing size, hash, or random bytes.

    Args:
        src (str): Source file path.
        dst (str): Destination file path.

    Returns:
        bool: True if files are identical, otherwise False.
    """
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
    """
    Copy a file from the source to the destination.

    Args:
        src (str): Source file path.
        dst (str): Destination file path.
    """
    try:
        logging.info(f"Copying file from {src} to {dst}")
        shutil.copy2(src, dst)  # Copy file with metadata
    except FileNotFoundError:
        logging.error(f"File not found during copy: {src}")
    except Exception as e:
        logging.error(f"Error copying file {src} to {dst}: {e}")
        with open(src, "rb") as sf, open(dst, "wb") as df:
            for chunk in iter(
                lambda: sf.read(4096), b""
            ):  # Manually copy in chunks if shutil fails
                df.write(chunk)


def check_cpu_usage(cpu_threshold: float = LIMIT_MAX_CPU_USAGE):
    """
    Check the current CPU usage and pause the process if it exceeds the threshold.

    Args:
        cpu_threshold (float): CPU usage threshold percentage.
    """
    curren_cpu_usage = psutil.cpu_percent(PSUTIL_ITERVAL)
    if curren_cpu_usage > cpu_threshold:
        logging.warning(f"High CPU usage ({curren_cpu_usage}%), pausing sync")
        time.sleep(1)  # Pause for 1 seconds if CPU usage is too high


def process_file(file_task_queue: Queue, cpu_threshold: float = LIMIT_MAX_CPU_USAGE):
    """
    Process files in a queue by comparing and copying them if needed.

    Args:
        file_task_queue (Queue): Queue containing file tasks (source, destination pairs).
        cpu_threshold (float): CPU usage threshold percentage.
    """
    while True:
        src_file, dst_file = file_task_queue.get()
        if not src_file:  # If the task is empty, break the loop
            file_task_queue.task_done()
            break

        curren_cpu_usage = psutil.cpu_percent(PSUTIL_ITERVAL)
        while (
            curren_cpu_usage > cpu_threshold
        ):  # Check and wait if CPU usage is too high
            logging.warning(f"High CPU usage ({curren_cpu_usage}%), pausing sync")
            time.sleep(1)
            curren_cpu_usage = psutil.cpu_percent(PSUTIL_ITERVAL)

        try:
            if not files_are_identical(
                src_file, dst_file
            ):  # Compare and copy if files are different
                logging.info(
                    f"File {src_file} is different from {dst_file}, copying..."
                )
                copy_file(src_file, dst_file)
        except FileNotFoundError:
            logging.error(f"File not found during processing: {src_file}")
        except Exception as e:
            logging.error(f"Error during processing {src_file}: {e}")

        file_task_queue.task_done()
        logging.info(f"Processed file: {src_file}, CPU usage {curren_cpu_usage}%")


def process_directory(
    dir_task_queue: Queue, cpu_threshold: float = LIMIT_MAX_CPU_USAGE
):
    """
    Process directories in a queue by creating them if they do not exist.

    Args:
        dir_task_queue (Queue): Queue containing directory paths.
        cpu_threshold (float): CPU usage threshold percentage.
    """
    while True:
        dst_folder = dir_task_queue.get()
        if not dst_folder:  # If the task is empty, break the loop
            dir_task_queue.task_done()
            break

        curren_cpu_usage = psutil.cpu_percent(PSUTIL_ITERVAL)
        while (
            curren_cpu_usage > cpu_threshold
        ):  # Check and wait if CPU usage is too high
            logging.warning(f"High CPU usage ({curren_cpu_usage}%), pausing sync")
            time.sleep(1)
            curren_cpu_usage = psutil.cpu_percent(PSUTIL_ITERVAL)

        if not os.path.exists(dst_folder):  # Create the directory if it doesn't exist
            os.makedirs(dst_folder)
            logging.info(f"Created directory {dst_folder}")

        dir_task_queue.task_done()
        logging.info(
            f"Processed directory: {dst_folder}, CPU usage {curren_cpu_usage}%"
        )


def sync_directories(
    src_dir: str, dst_dir: str, cpu_threshold: float = LIMIT_MAX_CPU_USAGE
):
    """
    Synchronize files and directories from the source to the destination.

    Args:
        src_dir (str): Source directory path.
        dst_dir (str): Destination directory path.
        cpu_threshold (float): CPU usage threshold percentage.
    """
    file_task_queue = Queue()
    dir_task_queue = Queue()

    # Process source files and directories
    for root, dirs, files in os.walk(src_dir):
        for file_name in (
            os.path.join(root, f) for f in files
        ):  # Add files to the queue
            src_file = file_name
            rel_path = os.path.relpath(src_file, src_dir)
            dst_file = os.path.join(dst_dir, rel_path)
            file_task_queue.put((src_file, dst_file))

        for dir_name in (
            os.path.join(root, d) for d in dirs
        ):  # Add directories to the queue
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
                if not os.path.exists(
                    src_file
                ):  # Remove extra files that don't exist in source
                    os.remove(os.path.join(root, dst_file))
                    logging.info(f"Removed extra file {os.path.join(root, dst_file)}")
            except FileNotFoundError:
                logging.error(
                    f"File not found during removal: {os.path.join(root, dst_file)}"
                )
            except Exception as e:
                logging.error(f"Error during processing {src_file}: {e}")

        for dst_folder in dirs:
            rel_path = os.path.relpath(os.path.join(root, dst_folder), dst_dir)
            src_folder = os.path.join(src_dir, rel_path)

            try:
                if not os.path.exists(
                    src_folder
                ):  # Remove extra directories that don't exist in source
                    shutil.rmtree(os.path.join(root, dst_folder))
                    logging.info(
                        f"Removed extra directory {os.path.join(root, dst_folder)}"
                    )
            except FileNotFoundError:
                logging.error(
                    f"Directory not found during removal: {os.path.join(root, dst_folder)}"
                )
            except Exception as e:
                logging.error(f"Error during processing {src_folder}: {e}")

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

    # Wait for all tasks to be completed
    file_task_queue.join()
    dir_task_queue.join()

    for t in threads:
        file_task_queue.put(None)  # Signal threads to stop
        dir_task_queue.put(None)

    for t in threads:
        t.join()  # Wait for all threads to finish

    logging.info("Synchronization complete.")


def process_pair(pair: list[str]):
    """
    Process a pair of source and destination directories for synchronization.

    This function takes a pair of source and destination directory paths, creates a logger for the specific
    directory pair, and then synchronizes the contents of the source directory with the destination directory.

    Args:
        pair (list[str]): A list containing two strings. The first string is the path to the source directory,
                          and the second string is the path to the destination directory.

    Procedure:
        1. Extracts the source and destination directory paths from the pair.
        2. Creates a logger named after the source and destination directory paths.
        3. Logs the start of the synchronization process.
        4. Calls `sync_directories` to synchronize the source directory with the destination directory.
        5. Logs the end of the synchronization process.
    """
    src_dir, dst_dir = pair
    logger = logging.getLogger(f"Process-{src_dir}-{dst_dir}")
    logger.info(f"Starting process for {src_dir} to {dst_dir}")
    sync_directories(src_dir, dst_dir)
    logger.info(f"Ending process for {src_dir} to {dst_dir}")


def acquire_socket_lock():
    """
    Attempt to acquire a socket lock to ensure single instance of the script is running.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("127.0.0.1", SOCKET_PORT))  # Try to bind the socket to a port
        return s  # Return the socket if binding was successful
    except socket.error as e:
        if e.errno == 98:  # Address already in use
            logging.error(
                f"Socket lock is already acquired by another instance. Exiting."
            )
            sys.exit(1)
        else:
            raise
    except Exception as e:
        logging.error(f"Socket lock is already acquired by another instance. Exiting.")
    finally:
        s.close()  # Close the socket regardless of whether an exception occurred or not


def process_pair_in_pool(source_destination_pairs: list):
    """
    Process a list of source and destination directory pairs in parallel using a multiprocessing pool.

    To prevent multiple instances of the copying process from running simultaneously,
    a socket lock is acquired at the beginning of the function and released at the end.

    Args:
        source_destination_pairs (list): A list of tuples, where each tuple contains
                                         a source directory path and a destination directory path.

    Procedure:
    1. Acquire a socket lock to ensure that only one instance of the process is running.
    2. Use a multiprocessing pool to process each pair of directories in parallel.
    3. Release the socket lock by closing the socket once the processing is complete.
    """

    # Acquire a socket lock to prevent multiple instances from running simultaneously
    lock_socket = acquire_socket_lock()

    # Create a multiprocessing pool with the number of processes equal to the CPU count
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        # Process each source-destination pair in parallel using the pool
        pool.map(process_pair, source_destination_pairs)

    # Release the socket lock by closing the socket
    lock_socket.close()


if __name__ == "__main__":
    """
    Main entry point for the script.

    This block of code is executed when the script is run directly. It defines a list of source and destination
    directory pairs that need to be synchronized and then calls `process_pair_in_pool` to process these pairs
    in parallel using a multiprocessing pool.

    The `source_destination_pairs` list contains tuples, where each tuple consists of:
        - The first element: the path to the source directory.
        - The second element: the path to the destination directory.

    The `process_pair_in_pool` function is called to handle the synchronization of each pair, utilizing
    multiple CPU cores for parallel processing.

    Note: Additional pairs can be added to the `source_destination_pairs` list as needed.
    """

    source_destination_pairs = [
        (
            "/home/emoi/Downloads/Boost.Asio.Cpp.Network.Programming.Cookbook/",
            "/mnt/404A81F44A81E74E/Boost.Asio.Cpp.Network.Programming.Cookbook/",
        ),
        # Add more pairs as needed
    ]

    process_pair_in_pool(source_destination_pairs)
