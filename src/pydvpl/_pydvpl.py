import argparse
import time
import os
import lz4.block
import zlib
import threading
import sys
import multiprocessing
import queue
from pathlib import Path
from functools import partial

PYDVPL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(PYDVPL_DIR))

from pydvpl.version import __version__, __description__, __title__, __date__, __repo__, __author__
from pydvpl.dvpl import compress_dvpl, decompress_dvpl, read_dvpl_footer, DVPL_FOOTER_SIZE, DVPL_TYPE_NONE, DVPL_TYPE_LZ4
from pydvpl.color import Color


class Meta:
    NAME = __title__
    VERSION = __version__
    DATE = __date__
    DEV = __author__
    REPO = __repo__
    INFO = __description__


output_lock = threading.Lock()

# Define a thread-safe queue to store processed files
processed_queue = queue.Queue()


def print_progress_bar_with_time(processed_files, total_files, start_time):
    with output_lock:
        progress = min(processed_files.value / total_files, 1.0)  # Ensure progress doesn't exceed 100%
        bar_length = 50
        filled_length = int(bar_length * progress)
        bar = '=' * filled_length + '-' * (bar_length - filled_length)
        percentage = progress * 100
        sys.stdout.write('\rProcessing: [{:<50}] {:.2f}%'.format(bar, percentage))
        sys.stdout.flush()

        # Calculate remaining time
        if progress > 0:
            elapsed_time = time.time() - start_time
            remaining_files = total_files - processed_files.value
            if processed_files.value > 0:
                avg_time_per_file = elapsed_time / processed_files.value
                remaining_time = remaining_files * avg_time_per_file
                if remaining_time < 60:
                    remaining_time_str = f"{int(remaining_time)} s"
                elif remaining_time < 3600:
                    remaining_time_str = f"{int(remaining_time / 60)} min"
                else:
                    remaining_time_str = f"{int(remaining_time / 3600)} h"
                sys.stdout.write(f' | Remaining time: {remaining_time_str}')
                sys.stdout.flush()


def count_total_files(directory):
    total_files = 0
    for path in Path(directory).rglob('*'):
        if path.is_file():
            total_files += 1
    return total_files


def convert_dvpl(directory_or_file, config, total_files=None, processed_files=None, start_time=None):
    if total_files is None:
        total_files = count_total_files(directory_or_file)
    if processed_files is None:
        processed_files = multiprocessing.Value('i', 0)
    if start_time is None:
        start_time = time.time()

    success_count = 0
    failure_count = 0
    ignored_count = 0

    if not os.path.exists(directory_or_file):
        raise FileNotFoundError(f"File or directory '{directory_or_file}' not found.")

    if Path(directory_or_file).is_dir():
        for file_path in Path(directory_or_file).rglob('*'):
            if file_path.is_file():
                succ, fail, ignored = convert_dvpl(str(file_path), config, total_files, processed_files, start_time)  # Convert WindowsPath to string
                success_count += succ
                failure_count += fail
                ignored_count += ignored
                with processed_files.get_lock():
                    processed_files.value += 1
                print_progress_bar_with_time(processed_files, total_files, start_time)
    else:
        is_decompression = config.mode == "decompress" and str(directory_or_file).endswith(".dvpl")  # Convert WindowsPath to string
        is_compression = config.mode == "compress" and not str(directory_or_file).endswith(".dvpl")  # Convert WindowsPath to string

        ignore_extensions = config.ignore.split(",") if config.ignore else []
        should_ignore = any(str(directory_or_file).endswith(ext) for ext in ignore_extensions)  # Convert WindowsPath to string

        if not should_ignore and (is_decompression or is_compression):
            file_path = str(directory_or_file)  # Convert WindowsPath to string
            try:
                # Check if the file exists before attempting to open it
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        file_data = f.read()

                    if is_compression:
                        if config.compression == "fast":
                            processed_block = compress_dvpl(file_data, "fast")
                        elif config.compression == "hc":
                            processed_block = compress_dvpl(file_data, "hc")
                        else:
                            processed_block = compress_dvpl(file_data)
                        new_name = file_path + ".dvpl"
                    else:
                        processed_block = decompress_dvpl(file_data)
                        new_name = os.path.splitext(file_path)[0]

                    with open(new_name, "wb") as f:
                        f.write(processed_block)

                    if not config.keep_originals:
                        os.remove(file_path)

                    success_count += 1
                    if config.verbose:
                        with output_lock:
                            print(f"{Color.GREEN}\nFile{Color.RESET} {file_path} has been successfully {Color.GREEN}{'compressed' if is_compression else 'decompressed'}{Color.RESET} into {Color.GREEN}{new_name}{Color.RESET}")
                else:
                    if config.verbose:
                        with output_lock:
                            print(f"{Color.RED}\nError{Color.RESET}: File {file_path} does not exist.")
                    failure_count += 1
            except Exception as e:
                failure_count += 1
                if config.verbose:
                    with output_lock:
                        print(f"{Color.RED}\nError{Color.RESET} processing file {file_path}: {e}")
        else:
            ignored_count += 1
            if config.verbose:
                with output_lock:
                    print(f"{Color.YELLOW}\nIgnoring{Color.RESET} file {directory_or_file}")

    return success_count, failure_count, ignored_count

def verify_dvpl(directory_or_file, config, total_files=None, processed_files=None, start_time=None):
    if total_files is None:
        total_files = count_total_files(directory_or_file)
    if processed_files is None:
        processed_files = multiprocessing.Value('i', 0)
    if start_time is None:
        start_time = time.time()

    success_count = 0
    failure_count = 0
    ignored_count = 0

    if not os.path.exists(directory_or_file):
        raise FileNotFoundError(f"File or directory '{directory_or_file}' not found.")

    if Path(directory_or_file).is_dir():
        for file_path in Path(directory_or_file).rglob('*'):
            if file_path.is_file() and file_path.suffix == '.dvpl':
                succ, fail, ignored = verify_dvpl(str(file_path), config, total_files, processed_files, start_time)  # Convert WindowsPath to string
                success_count += succ
                failure_count += fail
                ignored_count += ignored
                with processed_files.get_lock():
                    processed_files.value += 1
                print_progress_bar_with_time(processed_files, total_files, start_time)
    else:
        is_dvpl_file = str(directory_or_file).endswith(".dvpl")  # Convert WindowsPath to string

        ignore_extensions = config.ignore.split(",") if config.ignore else []
        should_ignore = any(str(directory_or_file).endswith(ext) for ext in ignore_extensions)  # Convert WindowsPath to string

        if not should_ignore and is_dvpl_file:
            file_path = str(directory_or_file)  # Convert WindowsPath to string
            try:
                with open(file_path, "rb") as f:
                    file_data = f.read()

                footer_data = read_dvpl_footer(file_data)

                target_block = file_data[:-DVPL_FOOTER_SIZE]

                if len(target_block) != footer_data.compressed_size:
                    raise ValueError(Color.RED + "DVPLSizeMismatch" + Color.RESET)

                if zlib.crc32(target_block) != footer_data.crc32:
                    raise ValueError(Color.RED + "DVPLCRC32Mismatch" + Color.RESET)

                if footer_data.type == DVPL_TYPE_NONE:
                    if footer_data.original_size != footer_data.compressed_size or footer_data.type != DVPL_TYPE_NONE:
                        raise ValueError(Color.RED + "DVPLTypeSizeMismatch" + Color.RESET)
                elif footer_data.type == DVPL_TYPE_LZ4:
                    de_dvpl_block = lz4.block.decompress(target_block, uncompressed_size=footer_data.original_size)
                    if len(de_dvpl_block) != footer_data.original_size:
                        raise ValueError(Color.RED + "DVPLDecodeSizeMismatch" + Color.RESET)
                else:
                    raise ValueError(Color.RED + "UNKNOWN DVPL FORMAT" + Color.RESET)

                if config.verbose:
                    with output_lock:
                        print(
                            f"{Color.GREEN}\nFile{Color.RESET} {file_path} has been successfully {Color.GREEN}verified.{Color.RESET}")

                success_count += 1
            except Exception as e:
                failure_count += 1
                if config.verbose:
                    with output_lock:
                        print(f"{Color.RED}\nError{Color.RESET} verifying file {file_path}: {e}")
        else:
            ignored_count += 1
            if config.verbose:
                with output_lock:
                    print(f"{Color.YELLOW}\nIgnoring{Color.RESET} file {directory_or_file}")

    return success_count, failure_count, ignored_count


def process_mode(directory_or_file, config):
    if config.mode in ["compress", "decompress"]:
        return convert_dvpl(directory_or_file, config)
    elif config.mode == "verify":
        return verify_dvpl(directory_or_file, config)
    elif config.mode == "help":
        print_help_message()
        return 0, 0, 0
    else:
        raise ValueError("Incorrect mode selected. Use '--help' for information.")


def parse_command_line_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--mode",
                        help="mode can be 'c' or 'compress' / 'd' or 'decompress' / 'v' or 'verify' / 'h' or 'help' (for an extended help guide).")
    parser.add_argument("-k", "--keep-originals", action="store_true",
                        help="keep original files after compression/decompression.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="shows verbose information for all processed files.")
    parser.add_argument("-p", "--path", help="directory/files path to process. Default is the current directory.")
    parser.add_argument("-i", "--ignore", default="",
                        help="Comma-separated list of file extensions to ignore during compression.")
    parser.add_argument("-t", "--threads", type=int, default=1,
                        help="Number of threads to use for processing. Default is 1.")
    parser.add_argument("-c", "--compression", choices=['default', 'fast', 'hc'],
                        help="Select compression level: 'default' for default compression, 'fast' for fast compression, 'hc' for high compression. Only available for 'compress' mode.")

    args = parser.parse_args()

    if not args.mode:
        parser.error("No mode selected. Use '--help' for usage information")

    if not args.path:
        args.path = os.getcwd()

    # Map short forms to full mode names
    mode_mapping = {
        'c': 'compress',
        'd': 'decompress',
        'v': 'verify',
        'h': 'help'
    }

    # If mode argument is provided, and it matches a short form, replace it with the full mode name
    if args.mode in mode_mapping:
        args.mode = mode_mapping[args.mode]

    # Check if compression option is used with incorrect modes
    if args.mode not in ['compress', 'c'] and args.compression is not None:
        parser.error("Compression option is only supported for 'compress' mode.")

    return args


def print_help_message():
    print('''$ pydvpl [--mode] [--keep-originals] [--path] [--verbose] [--ignore] [--threads]

    • flags can be one of the following:

        -m, --mode: required flag to select modes for processing.
        -k, --keep-originals: keeps the original files after compression/decompression.
        -p, --path: specifies the directory/files path to process. Default is the current directory.
        -i, --ignore: specifies comma-separated file extensions to ignore during compression.
        -v, --verbose: shows verbose information for all processed files.
        -t, --threads: specifies the number of threads to use for processing. Default is 1.

    • mode can be one of the following:

        c, compress: compresses files into dvpl.
        d, decompress: decompresses dvpl files into standard files.
        v, verify: verify compressed dvpl files to determine valid compression.
        h, help: show this help message.

    • usage can be one of the following examples:

        $ pydvpl --mode help

        $ pydvpl --mode decompress --path /path/to/decompress/compress

        $ pydvpl --mode compress --path /path/to/decompress/compress

        $ pydvpl --mode decompress --keep-originals -path /path/to/decompress/compress

        $ pydvpl --mode compress --keep-originals -path /path/to/decompress/compress

        $ pydvpl --mode decompress --path /path/to/decompress/compress.yaml.dvpl

        $ pydvpl --mode compress --path /path/to/decompress/compress.yaml

        $ pydvpl --mode decompress --keep-originals --path /path/to/decompress/compress.yaml.dvpl

        $ pydvpl --mode decompress --keep-originals --path /path/to/decompress/compress.yaml

        $ pydvpl --mode compress --path /path/to/decompress --ignore .exe,.dll

        $ pydvpl --mode compress --path /path/to/decompress --ignore exe,dll

        $ pydvpl --mode compress --path /path/to/decompress --ignore test.exe,test.txt

        $ pydvpl --mode verify -path /path/to/verify

        $ pydvpl --mode verify -path /path/to/verify/verify.yaml.dvpl
        
        $ pydvpl --mode decompress --path /path/to/decompress/compress.yaml.dvpl --threads 10

        $ pydvpl --mode compress --path /path/to/decompress/compress.yaml --threads 10
        
        $ pydvpl --mode compress --path /path/to/decompress/compress.yaml --compression hc
        
        $ pydvpl --mode compress --path /path/to/decompress/ --compression fast
    ''')


def print_elapsed_time(elapsed_time):
    if elapsed_time < 1:
        print(f"\nProcessing took {Color.GREEN}{int(elapsed_time * 1000)} ms{Color.RESET}\n")
    elif elapsed_time < 60:
        print(f"\nProcessing took {Color.YELLOW}{int(elapsed_time)} s{Color.RESET}\n")
    else:
        print(f"\nProcessing took {Color.RED}{int(elapsed_time / 60)} min{Color.RESET}\n")


def cli():
    print(f"\n{Color.BLUE}• Name:{Color.RESET} {Meta.NAME}")
    print(f"{Color.BLUE}• Version:{Color.RESET} {Meta.VERSION}")
    print(f"{Color.BLUE}• Commit:{Color.RESET} {Meta.DATE}")
    print(f"{Color.BLUE}• Dev:{Color.RESET} {Meta.DEV}")
    print(f"{Color.BLUE}• Repo:{Color.RESET} {Meta.REPO}")
    print(f"{Color.BLUE}• Info:{Color.RESET} {Meta.INFO}\n")

    start_time = time.time()
    config = parse_command_line_args()

    if config.threads <= 0:
        print(f"\n{Color.YELLOW}No threads specified.{Color.RESET} No processing will be done.\n")
        return

    try:
        process_func_partial = partial(process_mode, config=config)

        if config.threads > 1:
            with multiprocessing.Pool(config.threads) as pool:
                results = pool.map(process_func_partial, [config.path])
        else:
            results = [process_func_partial(config.path)]

        success_count = sum(result[0] for result in results)
        failure_count = sum(result[1] for result in results)
        ignored_count = sum(result[2] for result in results)

        if config.mode in ["compress", "decompress"]:
            print(
                f"\n\n{Color.GREEN}{config.mode.upper()} FINISHED{Color.RESET}. Successful conversions: {Color.GREEN}{success_count}{Color.RESET}, Failed conversions: {Color.RED}{failure_count}{Color.RESET}, Ignored files: {Color.YELLOW}{ignored_count}{Color.RESET}")
        elif config.mode == "verify":
            print(
                f"\n\n{Color.GREEN}{config.mode.upper()} FINISHED{Color.RESET}. Successful verifications: {Color.GREEN}{success_count}{Color.RESET}, Failed verifications: {Color.RED}{failure_count}{Color.RESET}, Ignored files: {Color.YELLOW}{ignored_count}{Color.RESET}")
    except Exception as e:
        print(f"\n\n{Color.RED}{config.mode.upper()} FAILED{Color.RESET}: {e}\n")

    elapsed_time = time.time() - start_time
    print_elapsed_time(elapsed_time)


if __name__ == "__main__":
    cli()
