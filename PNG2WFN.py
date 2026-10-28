import sys, re, struct
from pathlib import Path
from PIL import Image

PATTERN = re.compile(r'^(.*)_(\d+)-(\d+)$')

def info(path):
    m = PATTERN.fullmatch(path.stem)
    if not m: return path.stem, 0, None
    a, b = int(m[2]), int(m[3])
    if not m[1] or a > b or b > 65535: raise ValueError('Invalid filename range: ' + path.name)
    return m[1], a, b

def extract(path):
    base, start, end = info(path)
    with Image.open(path) as source: im = source.convert('RGBA')
    w, h = im.size
    p = im.load()
    sep = p[w-1, h-1]
    def is_sep(x,y):
        c = p[x,y]
        return c[3] == 0 if sep[3] == 0 else c == sep
    bounds = [-1] + [y for y in range(h) if all(is_sep(x,y) for x in range(w))] + [h]
    cells = []
    for prev, stop in zip(bounds,bounds[1:]):
        top = prev+1
        if top >= stop: continue
        left = 0
        for x in range(w+1):
            if x == w or all(is_sep(x,y) for y in range(top,stop)):
                if x > left:
                    if x-left > 64 or stop-top > 64: raise ValueError(f'{path.name}: glyph exceeds 64x64')
                    cell = im.crop((left,top,x,stop))
                    pixels = list(cell.get_flattened_data())
                    cell.putdata([(0, 0, 0, 0) if (c[3] == 0 if sep[3] == 0 else c == sep) else c for c in pixels])
                    cells.append(cell)
                left = x+1
    if not cells: raise ValueError(f'{path.name}: no glyphs detected')
    if end is not None and len(cells) != end-start+1: raise ValueError(f'{path.name}: found {len(cells)} glyphs, expected {end-start+1}')
    if start+len(cells)>65536: raise ValueError('Glyph index exceeds 65535')
    print(f'{path.name}: {len(cells)} glyph(s); separator RGBA {sep}')
    return {start+i: im for i,im in enumerate(cells)}

def bright(c): return .299*c[0]+.587*c[1]+.114*c[2]

def is_4bit(glyphs):
    # Separator pixels have already been removed from the extracted glyphs.
    # Fully transparent pixels are empty; all other pixels must be strictly
    # opaque black or white for the font to qualify as 1-bit.
    for im in glyphs.values():
        for r, g, b, a in im.get_flattened_data():
            if a == 0:
                continue
            if a != 255 or (r, g, b) not in ((0, 0, 0), (255, 255, 255)):
                return True
    return False

def record(im, depth):
    w,h = im.size
    stride = (w+7)//8 if depth==1 else (w+1)//2
    buf = bytearray(stride*h)
    p = im.load()
    for y in range(h):
        for x in range(w):
            c=p[x,y]
            if depth==1:
                if c[3] and bright(c)>=128: buf[y*stride+x//8] |= 0x80>>(x%8)
            else:
                shade = 0 if c[3]==0 or c[:3]==(0,0,0) else max(1,min(15,int(bright(c)/17+.5)))
                buf[y*stride+x//2] |= shade << (4 if x%2==0 else 0)
    return struct.pack('<HH',w,h)+buf

def build(glyphs, depth, base_shade=8):
    if depth==1:
        data=bytearray(b'WGT Font File  '+b'\0\0')
        offsets=[0]*(max(glyphs)+1)
        for index, im in sorted(glyphs.items()):
            offsets[index]=len(data)
            data.extend(record(im,1))
        table=len(data)
        if table>65535 or table+2*len(offsets)>65535: raise ValueError('1-bit WFN exceeds 65,535 bytes')
        data.extend(struct.pack('<'+'H'*len(offsets),*offsets))
        if len(data)>65535 or table>65535: raise ValueError('1-bit WFN exceeds 65,535 bytes')
        struct.pack_into('<H',data,15,table)
    else:
        data=bytearray(b'WGT Font File 2'+bytes(32))
        start=len(data)
        mapping=[]
        for index,im in sorted(glyphs.items()):
            mapping.append((index,len(data)-start))
            data.extend(record(im,4))
        map_start=len(data)
        for index,offset in mapping: data.extend(struct.pack('<II',index,offset))
        struct.pack_into('<8I',data,15,32,0,4,start,map_start-start,map_start,len(mapping)*8,base_shade)
    return data

def main(argv):
    if not argv:
        command = Path(sys.executable).name if getattr(sys, 'frozen', False) else f'py {Path(__file__).name}'
        print(f'Drag PNG files onto {Path(sys.executable).name if getattr(sys, "frozen", False) else Path(__file__).name}, or pass PNG paths on the command line.')
        print(f'\nUsage: {command} file.png [more.png ...] [--base-shade 1-15]')
        return 1
    base_shade = 8
    if '--base-shade' in argv:
        if argv.count('--base-shade') != 1:
            raise ValueError('--base-shade may only be specified once')
        pos = argv.index('--base-shade')
        if pos + 1 >= len(argv):
            raise ValueError('--base-shade requires a value from 1 to 15')
        try:
            base_shade = int(argv[pos + 1])
        except ValueError:
            raise ValueError('--base-shade must be an integer from 1 to 15')
        if not 1 <= base_shade <= 15:
            raise ValueError('--base-shade must be between 1 and 15')
        argv = argv[:pos] + argv[pos + 2:]
    if not argv:
        raise ValueError('No PNG files specified')
    groups={}
    for arg in argv:
        path=Path(arg).resolve()
        if not path.is_file() or path.suffix.lower()!='.png': raise ValueError('Not a PNG: '+str(path))
        base,start,end=info(path)
        key=(path.parent,base.lower())
        group=groups.setdefault(key,{'base':base,'files':set()})
        group['files'].add(path)
        if end is not None:
            for sibling in path.parent.iterdir():
                if sibling.is_file() and sibling.suffix.lower()=='.png':
                    m=PATTERN.fullmatch(sibling.stem)
                    if m and m[1].lower()==base.lower(): group['files'].add(sibling)
    for (folder,_),group in groups.items():
        glyphs={}
        for path in sorted(group['files'],key=lambda p:(info(p)[1],p.name.lower())):
            new=extract(path)
            overlap=glyphs.keys() & new.keys()
            if overlap: raise ValueError(f'{path.name}: overlapping index {min(overlap)}')
            glyphs.update(new)
        depth=4 if is_4bit(glyphs) else 1
        result=build(glyphs,depth,base_shade)
        output_folder = folder / f'{depth}-bit'
        output = output_folder / (group['base'] + '.wfn')
        if output.exists(): raise ValueError('Output already exists: '+str(output))
        output_folder.mkdir(parents=True, exist_ok=True)
        output.write_bytes(result)
        print(f'Created {output} ({len(glyphs)} glyphs, {depth}-bit, {len(result)} bytes' + (f', base shade {base_shade}' if depth == 4 else '') + ')')
    return 0

if __name__=='__main__':
    try: code=main(sys.argv[1:])
    except Exception as exc:
        print('ERROR:',exc,file=sys.stderr)
        code=1
    if getattr(sys,'frozen',False):
        try: input('\nPress Enter to close...')
        except EOFError: pass
    sys.exit(code)
