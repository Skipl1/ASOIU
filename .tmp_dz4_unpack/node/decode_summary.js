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
    const data = buf.subarray(off, off + len);
    off += len;
    chunks.push(data);
  }
  return { prelude, version, chunks };
}

function inflateRaw(u8) {
  return zlib.inflateRawSync(u8);
}

async function decodeFig(canvasPath) {
  const { prelude, version, chunks } = readCanvasFig(canvasPath);
  const schemaCompressed = chunks[0];
  const messageCompressed = chunks[1];

  const schemaRaw = inflateRaw(schemaCompressed);
  const schema = decodeBinarySchema(new Uint8Array(schemaRaw));
  const compiled = compileSchema(schema);

  const zstd = await new Promise((resolve) => {
    ZstdCodec.run((zstd) => resolve(zstd));
  });

  let messageRaw;
  const magic = messageCompressed.subarray(0, 4);
  const isZstd = magic[0] === 0x28 && magic[1] === 0xB5 && magic[2] === 0x2F && magic[3] === 0xFD;
  if (isZstd) {
    const simple = new zstd.Simple();
    messageRaw = Buffer.from(simple.decompress(messageCompressed));
  } else {
    messageRaw = inflateRaw(messageCompressed);
  }

  const message = compiled.decodeMessage(new Uint8Array(messageRaw));
  return { prelude, version, message };
}

function summarize(message) {
  const nodes = message.nodeChanges || [];
  const byType = new Map();
  for (const n of nodes) byType.set(n.type, (byType.get(n.type) || 0) + 1);
  const top = [...byType.entries()].sort((a,b)=>b[1]-a[1]).slice(0,20);

  const namedFrames = nodes
    .filter(n => (n.type === 'FRAME' || n.type === 'CANVAS' || n.type === 'DOCUMENT') && typeof n.name === 'string')
    .map(n => ({ type: n.type, name: n.name }))
    .slice(0, 80);

  return { totalNodes: nodes.length, topTypes: top, sampleNamed: namedFrames };
}

(async () => {
  const me = process.argv[2];
  const ex = process.argv[3];
  const a = await decodeFig(me);
  const b = await decodeFig(ex);

  const sa = summarize(a.message);
  const sb = summarize(b.message);

  console.log(JSON.stringify({
    me: { prelude: a.prelude, version: a.version, ...sa },
    example: { prelude: b.prelude, version: b.version, ...sb },
  }, null, 2));
})();
