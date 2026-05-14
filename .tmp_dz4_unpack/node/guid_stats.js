const fs=require('fs');
const zlib=require('zlib');
const {decodeBinarySchema,compileSchema}=require('kiwi-schema');
const {ZstdCodec}=require('zstd-codec');
function readCanvasFig(path){const buf=fs.readFileSync(path);let off=12;const version=buf.readUInt32LE(8);const chunks=[];while(off<buf.length){const len=buf.readUInt32LE(off);off+=4;chunks.push(buf.subarray(off,off+len));off+=len;}return{version,chunks};}
function inflateRaw(u8){return zlib.inflateRawSync(u8);} 
async function decode(path){const {chunks}=readCanvasFig(path);const schema=decodeBinarySchema(new Uint8Array(inflateRaw(chunks[0])));const compiled=compileSchema(schema);const zstd=await new Promise(r=>ZstdCodec.run(z=>r(z)));const mc=chunks[1];const isZ=mc[0]==0x28&&mc[1]==0xB5&&mc[2]==0x2F&&mc[3]==0xFD;const mr=isZ?Buffer.from(new zstd.Simple().decompress(mc)):inflateRaw(mc);return compiled.decodeMessage(new Uint8Array(mr));}
function stats(msg){const max=new Map();const cnt=new Map();for(const n of msg.nodeChanges||[]){const g=n.guid;if(!g||typeof g.sessionID!=='number'||typeof g.localID!=='number')continue;cnt.set(g.sessionID,(cnt.get(g.sessionID)||0)+1);max.set(g.sessionID,Math.max(max.get(g.sessionID)||0,g.localID));}
return {sessions:[...cnt.keys()].sort((a,b)=>a-b),counts:Object.fromEntries(cnt),maxLocal:Object.fromEntries(max)};}
(async()=>{const msg=await decode(process.argv[2]);console.log(JSON.stringify(stats(msg),null,2));
const first=(msg.nodeChanges||[]).slice(0,5).map(n=>({type:n.type,name:n.name,guid:n.guid}));
console.log('first5',JSON.stringify(first,null,2));})();
