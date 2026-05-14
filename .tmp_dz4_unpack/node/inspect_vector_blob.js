const fs=require('fs');
const zlib=require('zlib');
const {decodeBinarySchema,compileSchema}=require('kiwi-schema');
const {ZstdCodec}=require('zstd-codec');
function readCanvasFig(path){const buf=fs.readFileSync(path);let off=12;const chunks=[];while(off<buf.length){const len=buf.readUInt32LE(off);off+=4;chunks.push(buf.subarray(off,off+len));off+=len;}return chunks;}
function inflateRaw(u8){return zlib.inflateRawSync(u8);} 
async function decode(path){const ch=readCanvasFig(path);const schema=decodeBinarySchema(new Uint8Array(inflateRaw(ch[0])));const compiled=compileSchema(schema);const zstd=await new Promise(r=>ZstdCodec.run(z=>r(z)));const mc=ch[1];const isZ=mc[0]==0x28&&mc[1]==0xB5&&mc[2]==0x2F&&mc[3]==0xFD;const mr=isZ?Buffer.from(new zstd.Simple().decompress(mc)):inflateRaw(mc);return compiled.decodeMessage(new Uint8Array(mr));}
function findWithBlob(obj, path='', out=[]){
  if(obj==null||typeof obj!=='object') return out;
  for(const [k,v] of Object.entries(obj)){
    const p=path?path+'.'+k:k;
    if(/blob/i.test(k)) out.push({path:p, value:v});
    if(Array.isArray(v)){
      for(let i=0;i<v.length;i++) findWithBlob(v[i], p+'['+i+']', out);
    } else if(v && typeof v==='object') {
      findWithBlob(v, p, out);
    }
  }
  return out;
}
(async()=>{
 const msg=await decode(process.argv[2]);
 const nodes=msg.nodeChanges||[];
 const v=nodes.find(n=>n.type==='VECTOR');
 if(!v){console.log('no vector'); return;}
 const blobFields=findWithBlob(v);
 fs.writeFileSync('vector_blob_fields.json', JSON.stringify({name:v.name,guid:v.guid,blobFields,vectorNode:v},null,2),'utf8');
 console.log('wrote vector_blob_fields.json');
})();
