const fs = require('fs');
const zlib = require('zlib');
const { decodeBinarySchema, compileSchema } = require('kiwi-schema');
const { ZstdCodec } = require('zstd-codec');

function readCanvasFig(path) {
  const buf = fs.readFileSync(path);
  const prelude = buf.subarray(0, 8).toString('ascii');
  const version = buf.readUInt32LE(8);
  let off = 12;
  const chunks = [];
  while (off < buf.length) {
    const len = buf.readUInt32LE(off);
    off += 4;
    chunks.push(buf.subarray(off, off + len));
    off += len;
  }
  return { prelude, version, chunks };
}

function inflateRaw(u8) {
  return zlib.inflateRawSync(u8);
}

async function decodeFig(canvasPath) {
  const { prelude, version, chunks } = readCanvasFig(canvasPath);
  const schemaRaw = inflateRaw(chunks[0]);
  const schema = decodeBinarySchema(new Uint8Array(schemaRaw));
  const compiled = compileSchema(schema);
  const zstd = await new Promise((resolve) => ZstdCodec.run((zstd) => resolve(zstd)));

  const messageCompressed = chunks[1];
  const magic = messageCompressed.subarray(0, 4);
  const isZstd = magic[0] === 0x28 && magic[1] === 0xB5 && magic[2] === 0x2F && magic[3] === 0xFD;
  const messageRaw = isZstd
    ? Buffer.from(new zstd.Simple().decompress(messageCompressed))
    : inflateRaw(messageCompressed);

  const message = compiled.decodeMessage(new Uint8Array(messageRaw));
  return { prelude, version, schema, compiled, message, schemaCompressed: chunks[0], messageCompressed };
}

function listFrames(message) {
  const nodes = message.nodeChanges || [];
  return nodes
    .filter(n => n.type === 'FRAME')
    .map(n => ({ name: n.name ?? '', guid: n.guid, parentIndex: n.parentIndex }))
}

function norm(s) {
  return (typeof s === 'string' ? s : '').trim();
}

(async () => {
  const mePath = process.argv[2];
  const exPath = process.argv[3];
  const me = await decodeFig(mePath);
  const ex = await decodeFig(exPath);

  const meFrames = listFrames(me.message);
  const exFrames = listFrames(ex.message);

  const meSet = new Set(meFrames.map(f => norm(f.name)).filter(Boolean));
  const exSet = new Set(exFrames.map(f => norm(f.name)).filter(Boolean));

  const missing = [...exSet].filter(n => !meSet.has(n)).sort((a,b)=>a.localeCompare(b,'ru'));
  const extra = [...meSet].filter(n => !exSet.has(n)).sort((a,b)=>a.localeCompare(b,'ru'));

  fs.writeFileSync('frames_diff.json', JSON.stringify({
    meCount: meFrames.length,
    exCount: exFrames.length,
    missingFromMe: missing,
    extraInMe: extra
  }, null, 2), 'utf8');

  console.log('wrote frames_diff.json', 'missing', missing.length, 'extra', extra.length);
})();
