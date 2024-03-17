# PyDVPL Cli Converter
- A Cli Tool Coded In Python3 To Convert WoTB ( Dava ) SmartDLC DVPL File Based On LZ4 Compression.

Package & Module Structure :

    .
    ├── pydvpl
    │   ├── color
    │   │   ├── __init__.py
    │   │   └── _color.py
    │   ├── dvpl
    │   │   ├── __init__.py
    │   │   └── _dvpl.py
    │   ├── version
    │   │   ├── __init__.py
    │   │   └── _version.py
    │   ├── __init__.py
    │   └── _pydvpl.py
    └──────────────────────────

Usage :

    $ pydvpl [--mode] [--keep-originals] [--path] [--verbose] [--ignore] [--threads]

    • flags can be one of the following:

        -m, --mode: required flag to select modes for processing.
        -k, --keep-originals: keeps the original files after compression/decompression.
        -p, --path: specifies the directory/files path to process. Default is the current directory.
        -i, --ignore: specifies comma-separated file extensions to ignore during compression.
        -v, --verbose: shows verbose information for all processed files.
        -t, --threads: specifies the number of threads to use for processing. Default is 1.
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

        $ pydvpl --mode dcompress --keep-originals --path /path/to/decompress/compress.yaml

        $ pydvpl --mode compress --path /path/to/decompress --ignore .exe,.dll

        $ pydvpl --mode compress --path /path/to/decompress --ignore exe,dll

        $ pydvpl --mode compress --path /path/to/decompress --ignore test.exe,test.txt

        $ pydvpl --mode verify -path /path/to/verify

        $ pydvpl --mode verify -path /path/to/verify/verify.yaml.dvpl
        
        $ pydvpl --mode decompress --path /path/to/decompress/compress.yaml.dvpl --threads 10

        $ pydvpl --mode compress --path /path/to/decompress/compress.yaml --threads 10

        $ pydvpl --mode compress --path /path/to/decompress/compress.yaml --compression hc
        
        $ pydvpl --mode compress --path /path/to/decompress/ --compression fast

Requirements :

>python 3.10+

>pip 23.0+

Auto installation :
```
pip install pydvpl
```

Manual installation :

```
$ git clone https://github.com/rifsxd/pydvpl.git
```

```
$ cd pydvpl
```

```
$ pip install ./
```
