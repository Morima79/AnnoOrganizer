'Read graphics and IFO files embedded in Anno 1800 file.db using mmap.'
import mmap,struct as st,json,zlib
from pathlib import Path

def index_resident(game,cache):
    path=game/'file.db';signature=[path.stat().st_size,path.stat().st_mtime_ns]
    target=cache/'resident-index.json'
    if target.exists():
        old=json.loads(target.read_text(encoding='utf-8'))
        if old.get('signature')==signature:return old
    files={};buffers=[]
    with path.open('rb') as f:
        raw=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
        _,tags,attrs,_,magic=st.unpack_from('<5I',raw,len(raw)-20);assert magic==0xfffffffd
        names={1:'[]',0x8000:'[]'}
        for off in (tags,attrs):
            n,=st.unpack_from('<I',raw,off);ids=st.unpack_from('<'+'H'*n,raw,off+4);p=off+4+2*n
            for code in ids:
                end=raw.find(b'\0',p);names[code]=raw[p:end].decode();p=end+1
        p=0;stack=[];entry=None
        while p<tags:
            size,code=st.unpack_from('<IH',raw,p);p+=8
            if not code:
                if stack[-2:]==['FileMap','[]']:
                    if entry is not None:files[entry.pop('FileName')]=entry
                    entry=None
                if stack:stack.pop()
            elif code&0x8000:
                key=names[code]
                if key=='FileName':
                    filename=raw[p:p+size].decode('utf-16le').rstrip('\0').lower()
                    entry={'FileName':filename} if filename.endswith('.ifo') else None
                elif entry is not None and size<=8:entry[key]=int.from_bytes(raw[p:p+size],'little')
                if key=='Buffer' and 'ResidentBuffers' in stack:buffers.append([p,size])
                p+=(size+7)&~7
            else:stack.append(names[code])
        raw.close()
    result={'signature':signature,'files':files,'buffers':buffers}
    target.write_text(json.dumps(result),encoding='utf-8');return result

def read_resident(game,index,name):
    rec=index['files'].get(name)
    if rec is None or not rec.get('Flags',0)&4:return None
    position,size=index['buffers'][rec['ResidentBufferIndex']]
    start=rec.get('Position',0);length=rec['CompressedSize']
    assert start+length<=size
    with (game/'file.db').open('rb') as f:f.seek(position+start);data=f.read(length)
    if rec['Flags']&1:data=zlib.decompress(data)
    assert len(data)==rec['UncompressedSize']
    return data
