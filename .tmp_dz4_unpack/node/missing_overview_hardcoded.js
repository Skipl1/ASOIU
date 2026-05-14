const fs=require('fs');
const zlib=require('zlib');
const {decodeBinarySchema,compileSchema}=require('kiwi-schema');
const {ZstdCodec}=require('zstd-codec');
function readCanvasFig(path){const buf=fs.readFileSync(path);let off=12;const chunks=[];while(off<buf.length){const len=buf.readUInt32LE(off);off+=4;chunks.push(buf.subarray(off,off+len));off+=len;}return chunks;}
function inflateRaw(u8){return zlib.inflateRawSync(u8);} 
async function decode(path){const ch=readCanvasFig(path);const schema=decodeBinarySchema(new Uint8Array(inflateRaw(ch[0])));const compiled=compileSchema(schema);const zstd=await new Promise(r=>ZstdCodec.run(z=>r(z)));const mc=ch[1];const isZ=mc[0]==0x28&&mc[1]==0xB5&&mc[2]==0x2F&&mc[3]==0xFD;const mr=isZ?Buffer.from(new zstd.Simple().decompress(mc)):inflateRaw(mc);return {msg:compiled.decodeMessage(new Uint8Array(mr))};}
function key(g){return g?`${g.sessionID}:${g.localID}`:''}
function buildChildren(nodes){const children=new Map();for(const n of nodes){const pg=n.parentIndex&&n.parentIndex.guid; if(!pg) continue; const k=key(pg); if(!children.has(k)) children.set(k,[]); children.get(k).push(n);}return children;}
function collectSubtree(nodes, rootGuid){const byGuid=new Map(nodes.filter(n=>n.guid).map(n=>[key(n.guid),n]));
 const children=buildChildren(nodes);
 const out=[]; const stack=[key(rootGuid)]; const seen=new Set();
 while(stack.length){const k=stack.pop(); if(seen.has(k)) continue; seen.add(k);
 const node=byGuid.get(k); if(node) out.push(node);
 const kids=children.get(k)||[];
 for(const c of kids){if(c.guid) stack.push(key(c.guid));}
 }
 return out;
}
function blobRefs(obj, refs){
  if(obj==null) return;
  if(typeof obj!=='object') return;
  for(const [k,v] of Object.entries(obj)){
    if(v==null) continue;
    if(typeof v==='number'){
      if(/blob/i.test(k)) refs.add(v);
    } else if(Array.isArray(v)){
      for(const it of v) blobRefs(it, refs);
    } else if(typeof v==='object'){
      blobRefs(v, refs);
    }
  }
}
(async()=>{
 const exPath=process.argv[2];
 const names=[
  'Врачи. Настройки параметров поиска',
  'Врачи. Просмотр данных врача',
  'Мои записи. Ввод OTP',
  'Мои записи. Данные пользователя',
  'Мои записи. Данные записи на прием'
 ];
 const {msg}=await decode(exPath);
 const nodes=msg.nodeChanges||[];
 const out={};
 for(const name of names){
   const frame=nodes.find(n=>n.type==='FRAME' && n.name===name);
   if(!frame){out[name]={error:'not found'}; continue;}
   const subtree=collectSubtree(nodes, frame.guid);
   const types={};
   const refs=new Set();
   for(const n of subtree){types[n.type]=(types[n.type]||0)+1; blobRefs(n, refs);} 
   out[name]={count:subtree.length, types, approxBlobIndexRefs:[...refs].sort((a,b)=>a-b).slice(0,50)};
 }
 fs.writeFileSync('missing_subtrees_overview.json', JSON.stringify(out,null,2),'utf8');
 console.log('wrote missing_subtrees_overview.json');
})();
