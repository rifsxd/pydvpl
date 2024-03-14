import argparse
import time
import os
import lz4.block
import zlib
import threading
import sys
import multiprocessing
import queue
from functools import partial


class Color:
    RED = '\033[31m'
    GREEN = '\033[32m'
    BLUE = '\033[34m'
    YELLOW = '\033[33m'
    RESET = '\033[0m'


class Meta:
    NAME = 'PyDVPL'
    VERSION = '0.2.0'
    DATE = '14/03/2024'
    DEV = 'RifsxD'
    REPO = 'https://github.com/rifsxd/pydvpl'
    INFO = 'A CLI Tool Coded In Python3 To Convert WoTB ( Dava ) SmartDLC DVPL File Based On LZ4 High Compression.'


output_lock = threading.Lock()

# Define a thread-safe queue to store processed files
processed_queue = queue.Queue()

DVPL_FOOTER_SIZE = 20
DVPL_TYPE_NONE = 0
DVPL_TYPE_LZ4 = 2
DVPL_FOOTER = b"DVPL"


class DVPLFooter:
    def __init__(self, original_size, compressed_size, crc32, type_val):
        self.original_size = original_size
        self.compressed_size = compressed_size
        self.crc32 = crc32
        self.type = type_val


def createDVPLFooter(input_size, compressed_size, crc32_val, type_val):
    result = bytearray(DVPL_FOOTER_SIZE)
    result[:4] = input_size.to_bytes(4, 'little')
    result[4:8] = compressed_size.to_bytes(4, 'little')
    result[8:12] = crc32_val.to_bytes(4, 'little')
    result[12:16] = type_val.to_bytes(4, 'little')
    result[16:] = DVPL_FOOTER
    return result


def readDVPLFooter(buffer):
    if len(buffer) < DVPL_FOOTER_SIZE:
        raise ValueError(Color.RED + "InvalidDVPLFooter: Buffer size is smaller than expected" + Color.RESET)

    footer_buffer = buffer[-DVPL_FOOTER_SIZE:]

    if footer_buffer[16:] != DVPL_FOOTER:
        raise ValueError(Color.RED + "InvalidDVPLFooter: Footer signature mismatch" + Color.RESET)

    original_size = int.from_bytes(footer_buffer[:4], 'little')
    compressed_size = int.from_bytes(footer_buffer[4:8], 'little')
    crc32_val = int.from_bytes(footer_buffer[8:12], 'little')
    type_val = int.from_bytes(footer_buffer[12:16], 'little')

    return DVPLFooter(original_size, compressed_size, crc32_val, type_val)


def CompressDVPL(buffer):
    compressed_block = lz4.block.compress(buffer, store_size=False)
    footer_buffer = createDVPLFooter(len(buffer), len(compressed_block), zlib.crc32(compressed_block), DVPL_TYPE_LZ4)
    return compressed_block + footer_buffer


def DecompressDVPL(buffer):
    footer_data = readDVPLFooter(buffer)
    target_block = buffer[:-DVPL_FOOTER_SIZE]

    if len(target_block) != footer_data.compressed_size:
        raise ValueError(Color.RED + "DVPLSizeMismatch" + Color.RESET)

    if zlib.crc32(target_block) != footer_data.crc32:
        raise ValueError(Color.RED + "DVPLCRC32Mismatch" + Color.RESET)

    if footer_data.type == DVPL_TYPE_NONE:
        if footer_data.original_size != footer_data.compressed_size or footer_data.type != DVPL_TYPE_NONE:
            raise ValueError(Color.RED + "DVPLTypeSizeMismatch" + Color.RESET)
        return target_block
    elif footer_data.type == DVPL_TYPE_LZ4:
        deDVPL_block = lz4.block.decompress(target_block, uncompressed_size=footer_data.original_size)
        if len(deDVPL_block) != footer_data.original_size:
            raise ValueError(Color.RED + "DVPLDecodeSizeMismatch" + Color.RESET)
        return deDVPL_block
    else:
        raise ValueError(Color.RED + "UNKNOWN DVPL FORMAT" + Color.RESET)


def print_progress_bar(processed_files, total_files):
    with output_lock:
        progress = min(processed_files.value / total_files, 1.0)  # Ensure progress doesn't exceed 100%
        bar_length = 50
        filled_length = int(bar_length * progress)
        bar = '=' * filled_length + '-' * (bar_length - filled_length)
        percentage = progress * 100
        sys.stdout.write('\rProcessing: [{:<50}] {:.2f}%'.format(bar, percentage))
        sys.stdout.flush()


def count_total_files(directory):
    total_files = 0
    for root, dirs, files in os.walk(directory):
        total_files += len(files)
    return total_files


def ConvertDVPLFiles(directory_or_file, config, total_files, processed_files):
    success_count = 0
    failure_count = 0
    ignored_count = 0

    if os.path.isdir(directory_or_file):
        dir_list = os.listdir(directory_or_file)
        for dir_item in dir_list:
            succ, fail, ignored = ConvertDVPLFiles(os.path.join(directory_or_file, dir_item), config, total_files, processed_files)
            success_count += succ
            failure_count += fail
            ignored_count += ignored
            processed_files.value += 1
            print_progress_bar(processed_files, total_files)
    else:
        is_decompression = config.mode == "decompress" and directory_or_file.endswith(".dvpl")
        is_compression = config.mode == "compress" and not directory_or_file.endswith(".dvpl")

        ignore_extensions = config.ignore.split(",") if config.ignore else []
        should_ignore = any(directory_or_file.endswith(ext) for ext in ignore_extensions)

        if not should_ignore and (is_decompression or is_compression):
            file_path = directory_or_file
            try:
                with open(file_path, "rb") as f:
                    file_data = f.read()

                if is_compression:
                    processed_block = CompressDVPL(file_data)
                    new_name = file_path + ".dvpl"
                else:
                    processed_block = DecompressDVPL(file_data)
                    new_name = os.path.splitext(file_path)[0]

                with open(new_name, "wb") as f:
                    f.write(processed_block)

                if not config.keep_originals:
                    os.remove(file_path)

                success_count += 1
                if config.verbose:
                    with output_lock:
                        print(f"{Color.GREEN}\nFile{Color.RESET} {file_path} has been successfully {Color.GREEN}{'compressed' if is_compression else 'decompressed'}{Color.RESET} into {Color.GREEN}{new_name}{Color.RESET}")
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



def VerifyDVPLFiles(directory_or_file, config, total_files, processed_files):
    success_count = 0
    failure_count = 0
    ignored_count = 0

    if os.path.isdir(directory_or_file):
        dir_list = os.listdir(directory_or_file)
        for dir_item in dir_list:
            succ, fail, ignored = VerifyDVPLFiles(os.path.join(directory_or_file, dir_item), config, total_files,
                                                  processed_files)
            success_count += succ
            failure_count += fail
            ignored_count += ignored
            if processed_files.value < total_files:  # Ensure processed files count does not exceed total files
                processed_files.value += 1
            print_progress_bar(processed_files, total_files)
    else:
        is_dvpl_file = directory_or_file.endswith(".dvpl")

        ignore_extensions = config.ignore.split(",") if config.ignore else []
        should_ignore = any(directory_or_file.endswith(ext) for ext in ignore_extensions)

        if not should_ignore and is_dvpl_file:
            file_path = directory_or_file
            try:
                with open(file_path, "rb") as f:
                    file_data = f.read()

                footer_data = readDVPLFooter(file_data)

                target_block = file_data[:-DVPL_FOOTER_SIZE]

                if len(target_block) != footer_data.compressed_size:
                    raise ValueError(Color.RED + "DVPLSizeMismatch" + Color.RESET)

                if zlib.crc32(target_block) != footer_data.crc32:
                    raise ValueError(Color.RED + "DVPLCRC32Mismatch" + Color.RESET)

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


def ParseCommandLineArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--mode",
                        help="mode can be 'compress' / 'decompress' / 'help' (for an extended help guide).")
    parser.add_argument("-k", "--keep-originals", action="store_true",
                        help="keep original files after compression/decompression.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="shows verbose information for all processed files.")
    parser.add_argument("-p", "--path", help="directory/files path to process. Default is the current directory.")
    parser.add_argument("-i", "--ignore", default="",
                        help="Comma-separated list of file extensions to ignore during compression.")
    args = parser.parse_args()

    if not args.mode:
        parser.error("No mode selected. Use '--help' for usage information")

    if not args.path:
        args.path = os.getcwd()

    return args


def PrintHelpMessage():
    print('''pydvpl [--mode] [--keep-originals] [--path]

    • flags can be one of the following:

        -m, --mode: required flag to select modes for processing.
        -k, --keep-originals: keeps the original files after compression/decompression.
        -p, --path: specifies the directory/files path to process. Default is the current directory.
        -i, --ignore: specifies comma-separated file extensions to ignore during compression.
        -v, --verbose: shows verbose information for all processed files.

    • mode can be one of the following:

        compress: compresses files into dvpl.
        decompress: decompresses dvpl files into standard files.
        verify: verify compressed dvpl files to determine valid compression.
        help: show this help message.

    • usage can be one of the following examples:

        $ pydvpl --mode help

        $ pydvpl --mode decompress --path /path/to/decompress/compress

        $ pydvpl --mode compress --path /path/to/decompress/compress

        $ pydvpl --mode decompress --keep-originals -path /path/to/decompress/compress

        $ pydvpl --mode compress --keep-originals -path /path/to/decompress/compress

        $ pydvpl --mode decompress --path /path/to/decompress/compress.yaml.dvpl

        $ pydvpl --mode compress --path /path/to/decompress/compress.yaml

        $ pydvpl --mode decompress --keep-originals --path /path/to/decompress/compress.yaml.dvpl

        $ pydvpl --mode dcompress --keep-originals --path /path/to/decompress/compress.yaml

        $ pydvpl --mode compress --path /path/to/decompress --ignore .exe,.dll

        $ pydvpl --mode compress --path /path/to/decompress --ignore exe,dll

        $ pydvpl --mode compress --path /path/to/decompress --ignore test.exe,test.txt

        $ pydvpl --mode verify -path /path/to/verify

        $ pydvpl --mode verify -path /path/to/verify/verify.yaml.dvpl
    ''')


def PrintElapsedTime(elapsed_time):
    if elapsed_time < 1:
        print(f"\nProcessing took {Color.GREEN}{int(elapsed_time * 1000)} ms{Color.RESET}\n")
    elif elapsed_time < 60:
        print(f"\nProcessing took {Color.YELLOW}{int(elapsed_time)} s{Color.RESET}\n")
    else:
        print(f"\nProcessing took {Color.RED}{int(elapsed_time / 60)} min{Color.RESET}\n")


def main():
    print(f"\n{Color.BLUE}• Name:{Color.RESET} {Meta.NAME}")
    print(f"{Color.BLUE}• Version:{Color.RESET} {Meta.VERSION}")
    print(f"{Color.BLUE}• Commit:{Color.RESET} {Meta.DATE}")
    print(f"{Color.BLUE}• Dev:{Color.RESET} {Meta.DEV}")
    print(f"{Color.BLUE}• Repo:{Color.RESET} {Meta.REPO}")
    print(f"{Color.BLUE}• Info:{Color.RESET} {Meta.INFO}\n")

    start_time = time.time()
    config = ParseCommandLineArgs()

    total_files = count_total_files(config.path)
    manager = multiprocessing.Manager()
    processed_files = manager.Value('i', 0)  # Define processed_files using a Manager

    try:
        if config.mode in ["compress", "decompress"]:
            process_func = partial(ConvertDVPLFiles, config=config, total_files=total_files,
                                   processed_files=processed_files)
        elif config.mode == "verify":
            process_func = partial(VerifyDVPLFiles, config=config, total_files=total_files,
                                   processed_files=processed_files)
        else:
            raise ValueError("Incorrect mode selected. Use '--help' for information.")

        with multiprocessing.Pool() as pool:
            results = pool.map(process_func, [config.path])

        success_count = sum(result[0] for result in results)
        failure_count = sum(result[1] for result in results)
        ignored_count = sum(result[2] for result in results)

        if config.mode in ["compress", "decompress"]:
            print(
                f"\n\n{Color.GREEN}{config.mode.upper()} FINISHED{Color.RESET}. Successful conversions: {Color.GREEN}{success_count}{Color.RESET}, Failed conversions: {Color.RED}{failure_count}{Color.RESET}, Ignored files: {Color.YELLOW}{ignored_count}{Color.RESET}")
        elif config.mode == "verify":
            print(
                f"\n\n{Color.GREEN}{config.mode.upper()} FINISHED{Color.RESET}. Successful verifications: {Color.GREEN}{success_count}{Color.RESET}, Failed verifications: {Color.RED}{failure_count}{Color.RESET}, Ignored files: {Color.YELLOW}{ignored_count}{Color.RESET}")
        elif config.mode == "help":
            PrintHelpMessage()
    except Exception as e:
        print(f"\n\n{Color.RED}{config.mode.upper()} FAILED{Color.RESET}: {e}\n")

    elapsed_time = time.time() - start_time
    PrintElapsedTime(elapsed_time)


if __name__ == "__main__":
    main()
