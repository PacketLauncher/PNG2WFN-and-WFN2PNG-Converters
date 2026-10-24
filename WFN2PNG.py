#!/usr/bin/env python3
"""Convert legacy 1-bit and extended 4-bit WFN fonts to original-size PNG glyph sheets.

Usage: py WFNtoPNG.py font.wfn [more.wfn ...]
Requires: Pillow (py -m pip install pillow)
"""
import struct
import sys
import re
from pathlib import Path
from PIL import Image

MAGENTA = (255, 0, 255, 255)
GLYPHS_PER_ROW = 16
MAX_GLYPH_SIZE = 64
PLACEHOLDER_SIZE = (8, 9)


def u16(data, offset):
    if offset < 0 or offset + 2 > len(data):
        raise ValueError('Truncated 16-bit field')
    return struct.unpack_from('<H', data, offset)[0]


def read_glyph(data, position, limit, depth):
    if position < 0 or position + 4 > limit:
        raise ValueError('Glyph record outside glyph data')
    width, height = struct.unpack_from('<HH', data, position)
    if width > MAX_GLYPH_SIZE or height > MAX_GLYPH_SIZE:
        raise ValueError(f'Glyph exceeds {MAX_GLYPH_SIZE}x{MAX_GLYPH_SIZE}: {width}x{height}')
    stride = (width + 7) // 8 if depth == 1 else (width + 1) // 2
    size = stride * height
    if position + 4 + size > limit:
        raise ValueError('Truncated glyph bitmap')
    return width, height, data[position + 4:position + 4 + size]


def read_wfn(path):
    data = path.read_bytes()
    if len(data) < 17:
        raise ValueError('File is too short')
    signature = data[:15]
    glyphs = {}
    if signature == b'WGT Font File  ':
        depth = 1
        table = u16(data, 15)
        if table < 17 or table > len(data) or (len(data) - table) % 2:
            raise ValueError('Invalid legacy offset table')
        count = (len(data) - table) // 2
        if count > 65536:
            raise ValueError('Too many character slots')
        for index in range(count):
            position = u16(data, table + 2 * index)
            if position:
                if position < 17 or position >= table:
                    raise ValueError(f'Invalid glyph offset at index {index}')
                glyphs[index] = read_glyph(data, position, table, depth)
    elif signature == b'WGT Font File 2':
        depth = 4
        if len(data) < 43:
            raise ValueError('Truncated WFN File 2 header')
        header_size, flags, bpp, glyph_start, glyph_size, map_start, map_size = struct.unpack_from('<7I', data, 15)
        header_end = 15 + header_size
        glyph_end, map_end = glyph_start + glyph_size, map_start + map_size
        if header_size < 28 or header_end > len(data) or flags != 0 or bpp != 4:
            raise ValueError('Unsupported WFN File 2 header')
        if (glyph_start < header_end or map_start < header_end or glyph_end > len(data)
                or map_end > len(data) or map_size % 8 or
                (glyph_start < map_end and map_start < glyph_end)):
            raise ValueError('Invalid WFN File 2 table boundaries')
        previous = -1
        for offset in range(map_start, map_end, 8):
            index, relative = struct.unpack_from('<II', data, offset)
            if index > 65535 or index <= previous or relative >= glyph_size:
                raise ValueError('Invalid or unsorted WFN File 2 character mapping')
            previous = index
            glyphs[index] = read_glyph(data, glyph_start + relative, glyph_end, depth)
    else:
        raise ValueError('Unsupported WFN signature')
    # Zero-sized mapped glyphs have no visible pixels and cannot be represented
    # faithfully as image cells; omit them from the PNG sheets.
    glyphs = {i: g for i, g in glyphs.items() if g[0] > 0 and g[1] > 0}
    return depth, glyphs


def ranges_of(glyphs):
    indices = sorted(glyphs)
    if not indices:
        return
    start = previous = indices[0]
    for index in indices[1:]:
        if index != previous + 1:
            yield start, previous
            start = index
        previous = index
    yield start, previous


def render_glyph(canvas, glyph, x0, y0, depth):
    width, height, packed = glyph
    stride = (width + 7) // 8 if depth == 1 else (width + 1) // 2
    pixels = canvas.load()
    for y in range(height):
        for x in range(width):
            byte = packed[y * stride + (x // 8 if depth == 1 else x // 2)]
            if depth == 1:
                shade = 15 if byte & (0x80 >> (x % 8)) else 0
            else:
                shade = (byte >> 4) if x % 2 == 0 else (byte & 15)
            value = shade * 17
            pixels[x0 + x, y0 + y] = (value, value, value, 255)


def parse_color(value):
    if value == '-1':
        return (0, 0, 0, 0)
    if re.fullmatch(r'[0-9a-fA-F]{6}', value):
        return tuple(bytes.fromhex(value)) + (255,)
    if re.fullmatch(r'\d{1,3},\d{1,3},\d{1,3}', value):
        channels = tuple(map(int, value.split(',')))
        if all(0 <= n <= 255 for n in channels):
            return channels + (255,)
    raise ValueError("Separator must be RRGGBB, R,G,B, or -1 for transparency")


def parse_options(arguments):
    """Positional options: [glyphs_per_row] [original|fixed] [separator] [placeholders] [placeholder_size]."""
    if len(arguments) > 5:
        raise ValueError("Too many options; expected: rows mode separator placeholders placeholder_size")
    rows = int(arguments[0]) if len(arguments) >= 1 else GLYPHS_PER_ROW
    if not 1 <= rows <= 256:
        raise ValueError("Glyphs per row must be between 1 and 256")
    mode = arguments[1].lower() if len(arguments) >= 2 else 'original'
    if mode not in ('original', 'fixed'):
        raise ValueError("Layout must be 'original' or 'fixed'")
    separator = parse_color(arguments[2]) if len(arguments) >= 3 else MAGENTA
    placeholders = arguments[3].strip().lower() if len(arguments) >= 4 else '0'
    if placeholders not in ('0', '1', 'false', 'true', ''):
        raise ValueError("Export placeholders must be 0, 1, false, or true")
    size = arguments[4] if len(arguments) >= 5 else ''
    if size:
        match = re.fullmatch(r'(\d+)[xX](\d+)', size)
        if not match:
            raise ValueError("Placeholder size must be WIDTHxHEIGHT (for example 8x9)")
        placeholder_size = (int(match[1]), int(match[2]))
        if not all(1 <= n <= 64 for n in placeholder_size):
            raise ValueError("Placeholder width and height must each be 1–64")
    else:
        placeholder_size = PLACEHOLDER_SIZE
    return rows, mode, separator, placeholders in ('1', 'true'), placeholder_size


def export_range(glyphs, start, end, depth, target, rowsize, mode, separator, fixed_dimensions):
    count = end - start + 1
    rows = (count + rowsize - 1) // rowsize
    row_heights = []
    row_widths = []
    for row in range(rows):
        indices = range(start + row * rowsize, min(end + 1, start + (row + 1) * rowsize))
        items = [glyphs[i] for i in indices]
        if mode == 'fixed':
            cell_w, cell_h = fixed_dimensions
            row_widths.append(len(items) * (cell_w + 1))
            row_heights.append(cell_h)
        else:
            row_widths.append(sum(g[0] for g in items) + len(items))
            row_heights.append(max(g[1] for g in items))
    image = Image.new('RGBA', (max(row_widths), sum(row_heights) + rows), separator)
    y = 0
    for row, row_height in enumerate(row_heights):
        x = 0
        for index in range(start + row * rowsize, min(end + 1, start + (row + 1) * rowsize)):
            glyph = glyphs[index]
            w, h, _ = glyph
            # Draw the glyph's original pixels, retaining 1-bit or 4-bit values.
            # The unused part of a fixed-size cell is opaque black.
            if mode == 'fixed':
                cw, ch = fixed_dimensions
                image.paste((0, 0, 0, 255), (x, y, x + cw, y + ch))
                step = cw + 1
            else:
                image.paste((0, 0, 0, 255), (x, y, x + w, y + h))
                step = w + 1
            if w and h:
                render_glyph(image, glyph, x, y, depth)
            x += step
        y += row_height + 1
    image.save(target)


def convert(path, rowsize, mode, separator, placeholders, placeholder_size):
    depth, glyphs = read_wfn(path)
    if not glyphs:
        raise ValueError('No nonempty glyphs to export')
    if placeholders:
        # Missing slots use the editor's default placeholder dimensions.
        # Export one contiguous sheet from character 0 through the last glyph.
        glyphs = dict(glyphs)
        for index in range(max(glyphs) + 1):
            if index not in glyphs:
                w, h = placeholder_size
                stride = (w + 7) // 8 if depth == 1 else (w + 1) // 2
                glyphs[index] = (w, h, bytes(stride * h))
        ranges = [(0, max(glyphs))]
    else:
        ranges = list(ranges_of(glyphs))
    fixed_dimensions = (max(g[0] for g in glyphs.values()), max(g[1] for g in glyphs.values()))
    output_folder = path.parent / f'{depth}-bit'
    targets = [output_folder / f'{path.stem}_{start}-{end}.png' for start, end in ranges]
    existing = [p for p in targets if p.exists()]
    if existing:
        raise ValueError('Output already exists: ' + ', '.join(p.name for p in existing))
    output_folder.mkdir(parents=True, exist_ok=True)
    for (start, end), target in zip(ranges, targets):
        export_range(glyphs, start, end, depth, target, rowsize, mode, separator, fixed_dimensions)
        print(f'  {target.name}: {end - start + 1} glyph(s)')
    print(f'Converted {path.name}: {len(glyphs)} slots, {depth}-bit, {len(targets)} PNG(s)')


def main():
    args = sys.argv[1:]
    if not args:
        command = Path(sys.executable).name if getattr(sys, 'frozen', False) else f'py {Path(__file__).name}'
        print(f'Usage: {command} font.wfn [glyphs_per_row] [original|fixed] [RRGGBB|R,G,B|-1] [0|1|false|true] [WIDTHxHEIGHT]')
        print('\nThe default arguments are: 16 original FF00FF 0 8x9')
        print('\nMultiple WFN files may be supplied without options for drag-and-drop.')
        return 1
    # Keep the original multi-file drag-and-drop behavior if every argument is a WFN.
    if all(a.lower().endswith('.wfn') for a in args):
        paths = args
        options = (GLYPHS_PER_ROW, 'original', MAGENTA, False, PLACEHOLDER_SIZE)
    else:
        paths = [args[0]]
        try:
            options = parse_options(args[1:])
        except (ValueError, TypeError) as exc:
            print('ERROR:', exc, file=sys.stderr)
            return 1
    errors = 0
    for arg in paths:
        path = Path(arg).resolve()
        try:
            if not path.is_file() or path.suffix.lower() != '.wfn':
                raise ValueError('Not a WFN file')
            convert(path, *options)
        except (OSError, ValueError, struct.error) as exc:
            errors += 1
            print(f'ERROR [{path.name}]: {exc}', file=sys.stderr)
    return 1 if errors else 0


if __name__ == '__main__':
    result = main()
    if getattr(sys, 'frozen', False):
        try:
            input('\nPress Enter to close...')
        except EOFError:
            pass
    sys.exit(result)
