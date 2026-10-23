#!/usr/bin/env python3
"""The game's graphics/data compression (decompressor $80:D907): unpack and pack.

  kpack.py unpack ROM OFFSET OUT.bin      decompress the block at a file offset
  kpack.py info ROM OFFSET                method, packed size, unpacked size

Block: method byte (even: an index into the jump table at $80:D917), then a u16 packed length
counted from after it (method $0E: the unpacked length), then the data. Methods (from the code):
  $00 raw words                 $02 byte runs: control byte, 8 items (bit set: count byte), value
  $04 byte pairs: control byte, 4 items of 2 bits (count present; second byte = first)
  $06 word runs: control word, 16 items (bit set: count byte), word value
  $08 word pairs, like $04 with words, 8 items
  $0A bytes: control byte, bit set = a new byte, clear = the last one again (0 at each control byte)
  $0C words: the same with a control word and 16 words  $0E tree code (not implemented)
  $10 incrementing word runs                        $12 word runs with a signed byte step
pack() writes method $00 (raw words) or $0A/$0C (repeat suppression), whichever is shortest: the
game reads any method, so English data never has to match the original packer.
"""
import struct
import sys


def unpack(data, off):
    """Returns (bytes, packed length including the 3-byte header)."""
    m = data[off]
    n = struct.unpack_from('<H', data, off + 1)[0]
    p = off + 3
    end = p + n
    out = bytearray()

    def b():
        nonlocal p
        p += 1
        return data[p - 1]

    def w():
        nonlocal p
        p += 2
        return struct.unpack_from('<H', data, p - 2)[0]

    if m == 0x00:
        while p < end:
            out += struct.pack('<H', w())
    elif m == 0x02:
        while p < end:
            c = b()
            for _ in range(8):
                if p >= end:
                    break
                cnt = b() if c & 0x80 else 1
                c = (c << 1) & 0xff
                out += bytes([b()]) * (cnt or 256)
    elif m == 0x04:
        last2 = 0
        while p < end:
            c = b()
            for _ in range(4):
                if p >= end:
                    break
                cnt = b() if c & 0x80 else 1
                c = (c << 1) & 0xff
                v1 = b()
                last2 = v1 if c & 0x80 else b()
                c = (c << 1) & 0xff
                out += bytes([v1, last2]) * (cnt or 256)
    elif m in (0x06, 0x10, 0x12):
        while p < end:
            c = w()
            for _ in range(16):
                if p >= end:
                    break
                step, cnt = 0, 1
                bit = c & 0x8000
                c = (c << 1) & 0xffff
                if m == 0x12:
                    if bit:
                        cnt = b()
                        s = b()
                        step = s - 256 if s & 0x80 else s
                else:
                    if bit:
                        cnt = b()
                    step = 1 if m == 0x10 else 0
                v = w()
                for _ in range(cnt or 256):
                    out += struct.pack('<H', v & 0xffff)
                    v += step
    elif m == 0x08:
        last2 = 0
        while p < end:
            c = w()
            for _ in range(8):
                if p >= end:
                    break
                cnt = b() if c & 0x8000 else 1
                c = (c << 1) & 0xffff
                v1 = w()
                last2 = v1 if c & 0x8000 else w()
                c = (c << 1) & 0xffff
                out += struct.pack('<HH', v1, last2) * cnt
    elif m == 0x0A:
        while p < end:
            c = b()
            v = 0                         # a clear bit repeats the last value of the group
            for _ in range(8):
                if c & 0x80:
                    v = b()
                out.append(v)
                c = (c << 1) & 0xff
    elif m == 0x0C:
        while p < end:
            c = w()
            v = 0
            for _ in range(16):
                if c & 0x8000:
                    v = w()
                out += struct.pack('<H', v)
                c = (c << 1) & 0xffff
    else:
        raise ValueError(f'{off:#x}: method {m:#04x} not supported')
    return bytes(out), p - off


def pack(raw):
    """Shortest of raw words ($00), zero-suppressed bytes ($0A) and words ($0C)."""
    if len(raw) % 2:
        raw += b'\0'
    cands = [b'\x00' + struct.pack('<H', len(raw)) + raw]
    body = bytearray()
    for i in range(0, len(raw), 8):
        g = raw[i:i + 8].ljust(8, b'\0')
        prev, bits, vals = 0, 0, bytearray()
        for k in range(8):
            if g[k] != prev:
                bits |= 0x80 >> k
                vals.append(g[k])
                prev = g[k]
        body.append(bits)
        body += vals
    if len(raw) % 8 == 0:
        cands.append(b'\x0a' + struct.pack('<H', len(body)) + body)
    body = bytearray()
    if len(raw) % 32 == 0:
        for i in range(0, len(raw), 32):
            ws = struct.unpack_from('<16H', raw, i)
            prev, bits, vals = 0, 0, bytearray()
            for k in range(16):
                if ws[k] != prev:
                    bits |= 0x8000 >> k
                    vals += struct.pack('<H', ws[k])
                    prev = ws[k]
            body += struct.pack('<H', bits) + vals
        cands.append(b'\x0c' + struct.pack('<H', len(body)) + body)
    return min(cands, key=len)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 3 or argv[0] not in ('unpack', 'info'):
        sys.exit(__doc__)
    data = open(argv[1], 'rb').read()
    off = int(argv[2], 0)
    out, n = unpack(data, off)
    if argv[0] == 'info':
        print(f'{off:#x}: method {data[off]:#04x}, packed {n:#x}, unpacked {len(out):#x}')
    else:
        open(argv[3], 'wb').write(out)
        print(f'{argv[3]}: {len(out):#x} bytes (packed {n:#x})')


if __name__ == '__main__':
    main()
