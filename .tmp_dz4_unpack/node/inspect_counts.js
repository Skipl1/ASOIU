const fs = require('fs');
const zlib = require('zlib');
const { decodeBinarySchema, compileSchema } = require('kiwi-schema');
const { ZstdCodec } = require('zstd-codec');

function readCanvasFig(path) {
  const buf = fs.readFileSync(path);
  const version = buf.readUInt32LE(8);
  let off = 12;
  const chunks = [];
  while (off < buf.length) {
    const len = buf.readUInt32LE(off);
    off += 4;
    chunks.push(buf.subarray(off, off + len));
    off += len;
  }
  return { version, chunks };
}

function inflateRaw(u8) {
  return zlib.inflateRawSync(u8);
}

async function decode(path) {
  const { version, chunks } = readCanvasFig(path);
  const schema = decodeBinarySchema(new Uint8Array(inflateRaw(chunks[0])));
  const compiled = compileSchema(schema);
  const zstd = await new Promise((resolve) => ZstdCodec.run((z) => resolve(z)));

  const mc = chunks[1];
  const isZ = mc[0] === 0x28 && mc[1] === 0xB5 && mc[2] === 0x2F && mc[3] === 0xFD;
  const mr = isZ ? Buffer.from(new zstd.Simple().decompress(mc)) : inflateRaw(mc);
  const msg = compiled.decodeMessage(new Uint8Array(mr));

  return { version, schema, compiled, msg, schemaCompressed: chunks[0] };
}

function maxLocalIdSession(msg, sessionID) {
  let m = 0;
  for (const n of msg.nodeChanges || []) {
    if (n.guid && n.guid.sessionID === sessionID && typeof n.guid.localID === 'number') {
      m = Math.max(m, n.guid.localID);
    }
  }
  return m;
}

(async () => {
  const mePath = process.argv[2];
  const exPath = process.argv[3];
  const me = await decode(mePath);
  const ex = await decode(exPath);

  const out = {
    me: {
      nodes: (me.msg.nodeChanges || []).length,
      blobs: (me.msg.blobs || []).length,
      maxLocalIdSession1: maxLocalIdSession(me.msg, 1),
      maxLocalIdSession0: maxLocalIdSession(me.msg, 0),
    },
    example: {
      nodes: (ex.msg.nodeChanges || []).length,
      blobs: (ex.msg.blobs || []).length,
      maxLocalIdSession1: maxLocalIdSession(ex.msg, 1),
      maxLocalIdSession0: maxLocalIdSession(ex.msg, 0),
    },
  };

  console.log(JSON.stringify(out, null, 2));
})();
