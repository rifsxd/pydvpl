import argparse
import time
import os
import sys
import requests
from pathlib import Path
from functools import partial
from packaging import version

PYDVPL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(PYDVPL_DIR))

from pydvpl.version import __version__, __description__, __title__, __repo__, __author__, __license__
from pydvpl.dvpl import compress_dvpl, decompress_dvpl
from pydvpl.color import Color


def meta_info():
    NAME = __title__
    VERSION = __version__
    DEV = __author__
    REPO = __repo__
    INFO = __description__
    LICENSE = __license__

    print()

    # Loading animation while checking for updates
    animation = "|/-\\"
    idx = 0
    while True:
        print(f"\rChecking for updates... {animation[idx % len(animation)]}", end='', flush=True)
        idx += 1
        if idx == 20:  # Number of animation iterations
            break
        time.sleep(0.05)  # Adjust sleep time for faster animation

    try:
        response = requests.get(f"https://pypi.org/pypi/{NAME}/json", timeout=3)
        response.raise_for_status()  # Raise exception for non-200 status codes
        data = response.json()
        latest_version = data["info"]["version"]
    except requests.RequestException as e:
        print("\nError occurred while checking for updates:", e)
        return
    except Exception as e:
        print("\nUnexpected error occurred:", e)
        return

    if latest_version:
        installed_version = version.parse(VERSION)
        latest_pypi_version = version.parse(latest_version)

        if latest_pypi_version > installed_version:
            print(f"\n\n{Color.BLUE}• Version:{Color.RESET} {VERSION} (New version {latest_version} is available. Run `pydvpl --upgrade` to install latest version)")
        elif installed_version > latest_pypi_version:
            print(f"\n\n{Color.BLUE}• Version:{Color.RESET} {VERSION} (Whoa are you from the future? Cuz you have a newer version {VERSION} than available on PyPI {latest_version})")
        else:
            print(f"\n\n{Color.BLUE}• Version:{Color.RESET} {VERSION} (You have the latest version.)")
    else:
        print(f"\n\n{Color.BLUE}• Version:{Color.RESET} {VERSION} (Failed to retrieve latest version from PyPI)")

    print(f"{Color.BLUE}• Name:{Color.RESET} {NAME}")
    print(f"{Color.BLUE}• Dev:{Color.RESET} {DEV}")
    print(f"{Color.BLUE}• Repo:{Color.RESET} {REPO}")
    print(f"{Color.BLUE}• LICENSE:{Color.RESET} {LICENSE}")
    print(f"{Color.BLUE}• Info:{Color.RESET} {INFO}\n")


def brand_ascii():
    print(f'{Color.BLUE}')
    print('                                                  ')
    print('██████╗ ██╗   ██╗██████╗ ██╗   ██╗██████╗ ██╗     ')
    print('██╔══██╗╚██╗ ██╔╝██╔══██╗██║   ██║██╔══██╗██║     ')
    print('██████╔╝ ╚████╔╝ ██║  ██║██║   ██║██████╔╝██║     ')
    print('██╔═══╝   ╚██╔╝  ██║  ██║╚██╗ ██╔╝██╔═══╝ ██║     ')
    print('██║        ██║   ██████╔╝ ╚████╔╝ ██║     ███████╗')
    print('╚═╝        ╚═╝   ╚═════╝   ╚═══╝  ╚═╝     ╚══════╝')
    print('                                                  ')
    print(f'{__description__}')
    print('                                                  ')
    print(f'{Color.RESET}')


def print_remaining_time(processed_files, total_files, start_time):
    elapsed_time = time.time() - start_time
    if processed_files > 0:
        avg_processing_time_per_file = elapsed_time / processed_files
        remaining_files = total_files - processed_files
        remaining_time = remaining_files * avg_processing_time_per_file
        if remaining_time < 1:
            print(f" | Remaining time: {Color.GREEN}{int(remaining_time * 1000)} ms{Color.RESET}", end='')
        elif remaining_time < 60:
            print(f" | Remaining time: {Color.YELLOW}{int(remaining_time)} s{Color.RESET}", end='')
        elif remaining_time < 3600:
            print(f" | Remaining time: {Color.ORANGE}{int(remaining_time / 60)} min(s){Color.RESET}\r", end='')
        else:
            print(f" | Remaining time: {Color.RED}{int(remaining_time / 3600)} hour(s){Color.RESET}", end='')


def print_progress_bar_with_time(processed_files, total_files, start_time):

        progress = min(processed_files / total_files, 1.0)  # Ensure progress doesn't exceed 100%
        bar_length = 50
        filled_length = int(bar_length * progress)
        gap_length = 1  # Adjust gap length as needed
        if filled_length < bar_length:  # If progress is less than 100%
            gap_bar = f'{Color.GREY} {Color.RESET}' * gap_length
        else:
            gap_bar = ''
        filled_bar = f'{Color.GREEN}━{Color.RESET}' * filled_length
        unfilled_bar = f'{Color.GREY}━{Color.RESET}' * (bar_length - filled_length - gap_length)
        bar = filled_bar + gap_bar + unfilled_bar
        percentage = progress * 100
        sys.stdout.write('\rProcessing: [{:<50}] {:.2f}%'.format(bar, percentage))
        sys.stdout.flush()
        print_remaining_time(processed_files, total_files, start_time)


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
        processed_files = 0
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
                processed_files += 1
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
                            print(f"{Color.GREEN}\nFile{Color.RESET} {file_path} has been successfully {Color.GREEN}{'compressed' if is_compression else 'decompressed'}{Color.RESET} into {Color.GREEN}{new_name}{Color.RESET}")
                else:
                    if config.verbose:
                            print(f"{Color.RED}\nError{Color.RESET}: File {file_path} does not exist.")
                    failure_count += 1
            except Exception as e:
                failure_count += 1
                if config.verbose:
                        print(f"{Color.RED}\nError{Color.RESET} processing file {file_path}: {e}")
        else:
            ignored_count += 1
            if config.verbose:
                    print(f"{Color.YELLOW}\nIgnoring{Color.RESET} file {directory_or_file}")

    return success_count, failure_count, ignored_count

def verify_dvpl(directory_or_file, config, total_files=None, processed_files=None, start_time=None):
    if total_files is None:
        total_files = count_total_files(directory_or_file)
    if processed_files is None:
        processed_files = 0
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
                succ, fail, ignored = verify_dvpl(str(file_path), config, total_files, processed_files, start_time)  # Convert WindowsPath to string
                success_count += succ
                failure_count += fail
                ignored_count += ignored
                processed_files += 1
                print_progress_bar_with_time(processed_files, total_files, start_time)
    else:
        is_dvpl_file = str(directory_or_file).endswith(".dvpl")  # Convert WindowsPath to string
        ignore_extensions = config.ignore.split(",") if config.ignore else []
        should_ignore = any(str(directory_or_file).endswith(ext) for ext in ignore_extensions)  # Convert WindowsPath to string

        if not should_ignore and is_dvpl_file:
            file_path = str(directory_or_file)  # Convert WindowsPath to string
            try:
                # Check if the file exists before attempting to open it
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        file_data = f.read()

                    try:
                        success_count += 1
                        if config.verbose:
                                print(f"{Color.GREEN}\nVerified{Color.RESET} file {file_path} as a valid .dvpl file.")
                    except Exception as e:
                        failure_count += 1
                        if config.verbose:
                                print(f"{Color.RED}\nError{Color.RESET} verifying file {file_path}: {e}")
                else:
                    if config.verbose:
                            print(f"{Color.RED}\nError{Color.RESET}: File {file_path} does not exist.")
                    failure_count += 1
            except Exception as e:
                failure_count += 1
                if config.verbose:
                        print(f"{Color.RED}\nError{Color.RESET} processing file {file_path}: {e}")
        else:
            ignored_count += 1
            if config.verbose:
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


def confirm_upgrade():
    while True:
        user_input = input("Are you sure you want to upgrade pydvpl? 'yes' (y) or 'no' (n): ").strip().lower()
        if user_input in ['yes', 'y']:
            return True
        elif user_input in ['no', 'n']:
            return False
        else:
            print("Invalid input. Please enter 'yes' (y) or 'no' (n).")
            sys.exit(1)

            

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
    parser.add_argument("-c", "--compression", choices=['default', 'fast', 'hc'],
                        help="Select compression level: 'default' for default compression, 'fast' for fast compression, 'hc' for high compression. Only available for 'compress' mode.")
    parser.add_argument("--version", action="store_true",
                        help="show version information and updates and exit.")
    parser.add_argument("--upgrade", action="store_true",
                        help="upgrade pydvpl to the latest version")

    args = parser.parse_args()

    if args.version:
        meta_info()
        sys.exit()

    if args.upgrade:
        if confirm_upgrade():
            os.system('pip install pydvpl --upgrade')
        else:
            print("Upgrade cancelled.")
        sys.exit()

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
        -i, --ignore: specifies comma-separated (file extensions/file names/matching extentions or file names) to ignore during compression.
        -v, --verbose: shows verbose information for all processed files.
        --version: check version info/update and meta info.
        --upgrade: update to the latest version.

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
          
        $ pydvpl --mode compress --path /path/to/decompress --ignore .exe.dvpl,.dll.dvpl

        $ pydvpl --mode compress --path /path/to/decompress --ignore exe.dvpl,dll.dvpl

        $ pydvpl --mode compress --path /path/to/decompress --ignore test_test.exe,test_test.txt

        $ pydvpl --mode verify -path /path/to/verify

        $ pydvpl --mode verify -path /path/to/verify/verify.yaml.dvpl
        
        $ pydvpl --mode compress --path /path/to/decompress/compress.yaml --compression hc
        
        $ pydvpl --mode compress --path /path/to/decompress/ --compression fast
    ''')


def print_elapsed_time(elapsed_time):
    if elapsed_time < 1:
        print(f"\n\nProcessing took {Color.GREEN}{int(elapsed_time * 1000)} ms{Color.RESET}\n")
    elif elapsed_time < 60:
        print(f"\n\nProcessing took {Color.YELLOW}{int(elapsed_time)} s{Color.RESET}\n")
    elif elapsed_time < 3600:
        print(f"\n\nProcessing took {Color.ORANGE}{int(elapsed_time / 60)} min(s){Color.RESET}\n")
    else:
        print(f"\n\nProcessing took {Color.RED}{int(elapsed_time / 3600)} hour(s){Color.RESET}\n")


def cli():
    start_time = time.time()
    config = parse_command_line_args()

    brand_ascii()

    try:
        process_func_partial = partial(process_mode, config=config)

        results = [process_func_partial(config.path)]

        success_count = sum(result[0] for result in results)
        failure_count = sum(result[1] for result in results)
        ignored_count = sum(result[2] for result in results)

        if config.mode in ["compress", "decompress"]:
            print_elapsed_time(time.time() - start_time)
            if config.mode == "compress":
                print(f"{Color.BLUE}Compressesion Finished!{Color.RESET}\n")
            elif config.mode == "decompress":
                print(f"{Color.BLUE}Decompression Finished!{Color.RESET}\n")
            print(f"{Color.GREEN}{'-' * 10}{Color.RESET} {Color.GREEN}Summary{Color.RESET} {Color.GREEN}{'-' * 10}{Color.RESET}\n")
            print(f"{'Processed:':<12} {Color.BLUE}{success_count + failure_count + ignored_count}{Color.RESET}")
            print(f"{'Succeeded:':<12} {Color.GREEN}{success_count}{Color.RESET}")
            print(f"{'Failed:':<12} {Color.RED}{failure_count}{Color.RESET}")
            print(f"{'Ignored:':<12} {Color.YELLOW}{ignored_count}{Color.RESET}\n")
        elif config.mode == "verify":
            print_elapsed_time(time.time() - start_time)
            print(f"{Color.BLUE}Verification Finished!{Color.RESET}\n")
            print(f"{Color.GREEN}{'-' * 10}{Color.RESET} {Color.GREEN}Summary{Color.RESET} {Color.GREEN}{'-' * 10}{Color.RESET}\n")
            print(f"{'Processed:':<12} {Color.BLUE}{success_count + failure_count + ignored_count}{Color.RESET}")
            print(f"{'Succeeded:':<12} {Color.GREEN}{success_count}{Color.RESET}")
            print(f"{'Failed:':<12} {Color.RED}{failure_count}{Color.RESET}")
            print(f"{'Ignored:':<12} {Color.YELLOW}{ignored_count}{Color.RESET}\n")

    except Exception as e:
        print(f"{Color.RED}\nError: {e}{Color.RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    cli()
