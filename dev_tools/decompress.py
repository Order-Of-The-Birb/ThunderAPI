import argparse
import bz2
import struct
import sys

def read_input_bytes(input_file):
    with open(input_file, 'rb') as f:
        raw_data = f.read()

    stripped = b''.join(raw_data.split())
    try:
        decoded = bytes.fromhex(stripped.decode('ascii'))
    except (ValueError, UnicodeDecodeError):
        return raw_data

    return decoded

def decompress_lz4(data, force=False):
    try:
        import lz4.block
    except ModuleNotFoundError:
        print("[-] Missing dependency: run this with .venv/bin/python or install it with 'pip install lz4'")
        return None

    if len(data) < 4:
        print("[-] LZ4 data is too short to contain a size header.")
        return None

    candidates = []
    if data[:1] == b'\x4c':
        if len(data) < 5:
            print("[-] LZ4 marker found, but the file is too short to contain a size header.")
            return None

        # First byte is the compression marker. The next 4 bytes are the expected size.
        candidates.append(("marker+size", struct.unpack('>I', data[1:5])[0], data[5:]))
    elif force:
        # Forced LZ4 handles files without the 4C marker by treating the first 4 bytes
        # as the expected decompressed size.
        candidates.append(("size-header", struct.unpack('>I', data[:4])[0], data[4:]))
    else:
        return None

    for label, uncompressed_size, compressed_payload in candidates:
        try:
            print(f"[*] Trying LZ4 {label}; potential uncompressed size: {uncompressed_size}")
            return lz4.block.decompress(compressed_payload, uncompressed_size=uncompressed_size)
        except Exception as e:
            print(f"[-] LZ4 {label} decompression failed: {e}")

    return None

def decompress_bzip(data, force=False):
    offset = data.find(b'BZh') if force else data[:20].find(b'BZh')
    if offset == -1:
        if not force:
            return None
        offset = 0

    try:
        print(f"[*] Found bzip stream at offset {offset}")
        return bz2.decompress(data[offset:])
    except OSError as e:
        print(f"[-] bzip decompression failed: {e}")
        return None

def decompress_file(input_file, output_file, force=None):
    all_data = read_input_bytes(input_file)

    decompressed = None
    if force == "lz4":
        print("[*] Forcing LZ4 decompression")
        decompressed = decompress_lz4(all_data, force=True)
    elif force == "bzip":
        print("[*] Forcing bzip decompression")
        decompressed = decompress_bzip(all_data, force=True)
    else:
        if b'BZh' in all_data[:20]:
            decompressed = decompress_bzip(all_data)
        if decompressed is None:
            decompressed = decompress_lz4(all_data, force=True)

    if decompressed is None:
        return False

    with open(output_file, 'wb') as f_out:
        f_out.write(decompressed)

    print(f"[+] Success! File saved to {output_file}")
    return True

def parse_args():
    parser = argparse.ArgumentParser(description="Decompress raw LZ4HC or bzip .blk data.")
    parser.add_argument("input_file", help="Path to the compressed .blk file or raw hex file")
    parser.add_argument(
        "-o",
        "--output",
        help="Path to write the decompressed file. Defaults to overwriting the input file.",
    )
    parser.add_argument(
        "--force",
        choices=("lz4", "bzip"),
        help="Force a decompression algorithm instead of auto-detecting from file markers.",
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    output_file = args.output or args.input_file
    sys.exit(0 if decompress_file(args.input_file, output_file, args.force) else 1)
