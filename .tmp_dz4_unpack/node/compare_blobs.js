const fs=require('fs');
const zlib=require('zlib');
const crypto=require('crypto');
const {decodeBinarySchema,compileSchema}=require('kiwi-schema');
const {ZstdCodec}=require('zstd-codec');
function readCanvasFig(path){const buf=fs.readFileSync(path);let off=12;const chunks=[];while(off<buf.length){const len=buf.readUInt32LE(off);off+=4;chunks.push(buf.subarray(off,off+len));off+=len;}return chunks;}
function inflateRaw(u8){return zlib.inflateRawSync(u8);} 
async function decode(path){const ch=readCanvasFig(path);const schema=decodeBinarySchema(new Uint8Array(inflateRaw(ch[0])));const compiled=compileSchema(schema);const zstd=await new Promise(r=>ZstdCodec.run(z=>r(z)));const mc=ch[1];const isZ=mc[0]==0x28&&mc[1]==0xB5&&mc[2]==0x2F&&mc[3]==0xFD;const mr=isZ?Buffer.from(new zstd.Simple().decompress(mc)):inflateRaw(mc);return compiled.decodeMessage(new Uint8Array(mr));}
function blobHash(b){return crypto.createHash('sha1').update(Buffer.from(b.bytes)).digest('hex');}
(async()=>{
 const me=await decode(process.argv[2]);
 const ex=await decode(process.argv[3]);
 const m=me.blobs||[]; const e=ex.blobs||[];
 const min=Math.min(m.length,e.length);
 let same=0; let firstDiff=-1;
 for(let i=0;i<min;i++){
   const hm=blobHash(m[i]);
   const he=blobHash(e[i]);
   if(hm===he) same++; else {firstDiff=i; break;}
 }
 console.log(JSON.stringify({meBlobs:m.length,exBlobs:e.length,prefixSame:same,firstDiff},null,2));
})();
