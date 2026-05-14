const fs=require('fs');
const zlib=require('zlib');
const {decodeBinarySchema,compileSchema}=require('kiwi-schema');
const {ZstdCodec}=require('zstd-codec');
function readCanvasFig(path){const buf=fs.readFileSync(path);let off=12;const chunks=[];while(off<buf.length){const len=buf.readUInt32LE(off);off+=4;chunks.push(buf.subarray(off,off+len));off+=len;}return chunks;}
function inflateRaw(u8){return zlib.inflateRawSync(u8);} 
async function decode(path){const ch=readCanvasFig(path);const schema=decodeBinarySchema(new Uint8Array(inflateRaw(ch[0])));const compiled=compileSchema(schema);const zstd=await new Promise(r=>ZstdCodec.run(z=>r(z)));const mc=ch[1];const isZ=mc[0]==0x28&&mc[1]==0xB5&&mc[2]==0x2F&&mc[3]==0xFD;const mr=isZ?Buffer.from(new zstd.Simple().decompress(mc)):inflateRaw(mc);return compiled.decodeMessage(new Uint8Array(mr));}
(async()=>{
  const msg=await decode(process.argv[2]);
  const names=new Set([
    'Врачи. Настройки параметров поиска',
    'Врачи. Просмотр данных врача',
    'Мои записи. Ввод OTP',
    'Мои записи. Данные пользователя',
    'Мои записи. Данные записи на прием'
  ]);
  const frames=(msg.nodeChanges||[]).filter(n=>n.type==='FRAME' && names.has(n.name)).map(n=>n.name);
  console.log(JSON.stringify({found:frames, missing:[...names].filter(n=>!frames.includes(n))},null,2));
})();
