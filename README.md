# PyDVPL Cli Converter
- A Cli Tool Coded In Python3 To Convert WoTB ( Dava ) SmartDLC DVPL File Based On LZ4 High Compression.

Usage :

    pydvpl [--mode] [--keep-originals] [--path] [--verbose] [--ignore]

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

Running :

- python 3.10+ required!

```
$ git clone https://github.com/rifsxd/pydvpl.git
```

```
$ cd pydvpl/src/pydvpl
```

```
$ py ./pydvpl.py -h
```
