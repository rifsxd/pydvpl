import lz4.block
import zlib
from ..color import Color


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


def create_dvpl_footer(input_size, compressed_size, crc32_val, type_val):
    result = bytearray(DVPL_FOOTER_SIZE)
    result[:4] = input_size.to_bytes(4, 'little')
    result[4:8] = compressed_size.to_bytes(4, 'little')
    result[8:12] = crc32_val.to_bytes(4, 'little')
    result[12:16] = type_val.to_bytes(4, 'little')
    result[16:] = DVPL_FOOTER
    return result


def read_dvpl_footer(buffer):
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


def compress_dvpl(buffer, compression_type="default"):
    if compression_type == "fast":
        mode = "fast"
    elif compression_type == "hc":
        mode = "high_compression"
    else:
        mode = "default"

    compressed_block = lz4.block.compress(buffer, store_size=False, mode=mode)
    footer_buffer = create_dvpl_footer(len(buffer), len(compressed_block), zlib.crc32(compressed_block), DVPL_TYPE_LZ4)
    return compressed_block + footer_buffer


def decompress_dvpl(buffer):
    footer_data = read_dvpl_footer(buffer)
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
        de_dvpl_block = lz4.block.decompress(target_block, uncompressed_size=footer_data.original_size)
        if len(de_dvpl_block) != footer_data.original_size:
            raise ValueError(Color.RED + "DVPLDecodeSizeMismatch" + Color.RESET)
        return de_dvpl_block
    else:
        raise ValueError(Color.RED + "UNKNOWN DVPL FORMAT" + Color.RESET)
