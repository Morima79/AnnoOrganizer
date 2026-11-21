'Readers for RDA archives and FileDB data.'
import struct as st
import zlib

def members(path, wanted):
    with path.open('rb') as f:
        def read(pos, n):
            f.seek(pos)
            result = f.read(n)
            if len(result) != n:
                raise ValueError('Unvollständiger RDA-Block')
            return result
        if read(0,18) != b'Resource File V2.2':
            raise ValueError('Kein RDA V2.2')
        off, = st.unpack('<Q', read(0x310,8))
        seen = set()
        while off not in seen and 0 < off < path.stat().st_size:
            seen.add(off)
            flags,n,packed,plain,nxt = st.unpack('<IIQQQ',read(off,32))
            if flags & 2:
                raise ValueError('Verschlüsselter RDA-Block')
            directory = read(off-packed,packed)
            if flags & 1:
                directory = zlib.decompress(directory)
            if len(directory) != plain or n * 560 != plain:
                raise ValueError('Ungültiges RDA-Verzeichnis')
            for i in range(n):
                p = i*560
                name = directory[p:p+520].decode('utf-16le','replace').split('\0',1)[0]
                if name in wanted:
                    pos, length = st.unpack_from('<QQ',directory,p+520)
                    raw = read(pos,length)
                    yield name, inflate(zlib.decompress(raw) if flags & 1 else raw)
            off = nxt

def inflate(raw):
    out = bytearray()
    while raw:
        dec = zlib.decompressobj()
        piece = dec.decompress(raw)
        if not dec.eof:
            raise ValueError('Unvollständiger zlib-Stream')
        raw = dec.unused_data
        if not piece:
            if len(raw) < 4 or st.unpack_from('<I',raw)[0] != len(out):
                raise ValueError('Falsche Länge des inneren Streams')
            return out
        out.extend(piece)
    raise ValueError('Fehlender zlib-Endmarker')

def legacy_fields(data):
    end, = st.unpack_from('<I',data,len(data)-4)
    if not 0 < end < len(data)-4:
        raise ValueError('Ungültiges FileDB-V1-Verzeichnis')
    def varint(p):
        n = 0
        for shift in range(0,35,7):
            b = data[p]
            p += 1
            n |= (b&127)<<shift
            if not b&128: return n,p
        raise ValueError('Ungültige FileDB-V1-Länge')
    names = {1:'[]',0x8000:'[]'}
    p = end
    for _ in range(2):
        n,p = varint(p)
        for _ in range(n):
            stop=data.index(0,p)
            code, = st.unpack_from('<H',data,stop+1)
            names[code] = data[p:stop].decode('utf-8','replace')
            p=stop+3
    if p != len(data)-4: raise ValueError('Unbekannte FileDB-Version')
    p=0
    stack=[]
    view=memoryview(data)
    while p+2 <= end:
        code,=st.unpack_from('<H',data,p)
        p+=2
        if code==0:
            if not stack: break
            stack.pop()
        elif code&0x8000:
            size,p=varint(p)
            if p+size>end: raise ValueError('Unvollständiges FileDB-V1-Feld')
            yield (*stack,names.get(code,str(code))),view[p:p+size]
            p+=size
        else:
            stack.append(names.get(code,str(code)))


def fields(data, keep=None):
    _,tags,attrs,_,magic = st.unpack_from('<5I',data,len(data)-20)
    if magic not in (0xfffffffd,0xfffffffe):
        yield from legacy_fields(data)
        return
    names = {1:'[]',0x8000:'[]'}
    for pos in (tags,attrs):
        n, = st.unpack_from('<I',data,pos)
        ids = st.unpack_from(f'<{n}H',data,pos+4)
        p = pos+4+2*n
        for code in ids:
            end = data.index(0,p)
            names[code] = data[p:end].decode('utf-8','replace')
            p = end+1
    stack = []
    p = 0
    view = memoryview(data)
    while p+8 <= tags:
        size,code = st.unpack_from('<IH',data,p)
        p += 8
        if code == 0:
            if not stack:
                break
            stack.pop()
        elif code & 0x8000:
            name = names.get(code, str(code))
            if keep is None or name in keep or any(t in keep for t in stack):
                yield (*stack,name), view[p:p+size]
            p += (size+7)&~7
        else:
            stack.append(names.get(code,str(code)))

def val(v):
    v = bytes(v)
    if len(v) in (1,2,4,8):
        return int.from_bytes(v,'little')
    if len(v)%2==0 and v[1::2].count(0) > len(v)//4:
        s = v.decode('utf-16le','replace').rstrip('\0')
        if s.isprintable(): return s
    s = v.rstrip(b'\0').decode('utf-8','replace')
    return s if s.isprintable() and '\ufffd' not in s else v.hex()

def rda_index(path):
    with path.open('rb') as f:
        f.seek(0x310)
        off,=st.unpack('<Q',f.read(8))
        size=path.stat().st_size
        seen=set()
        while 0<off<size and off not in seen:
            seen.add(off)
            f.seek(off)
            flags,n,packed,plain,nxt=st.unpack('<IIQQQ',f.read(32))
            f.seek(off-packed)
            buf=f.read(packed)
            if flags&1: buf=zlib.decompress(buf)
            if flags&8:
                # Memory-resident blocks have a 16-byte size footer before the directory.
                f.seek(off-packed-16)
                packed_data,raw_data=st.unpack('<QQ',f.read(16))
                base=off-packed-16-packed_data
            else:
                base=0
                packed_data=0
            for i in range(0,n*560,560):
                name=buf[i:i+520].decode('utf-16le','replace').split('\0',1)[0].lower()
                pos,length,raw=st.unpack_from('<QQQ',buf,i+520)
                yield name,(str(path),flags,base,packed_data,pos,length,raw)
            off=nxt

def read_asset(rec):
    path,flags,base,packed_data,pos,n,plain=rec
    if flags&2: raise ValueError('Verschlüsseltes Spielasset')
    with open(path,'rb') as f:
        if flags&8:
            f.seek(base)
            block=f.read(packed_data)
            if flags&1: block=zlib.decompress(block)
            return block[pos:pos+plain]
        f.seek(pos)
        data=f.read(n)
        return zlib.decompress(data) if flags&1 else data
