const fs = require('fs');
const zlib = require('zlib');
const path = require('path');
const { decodeBinarySchema, compileSchema } = require('kiwi-schema');
const { ZstdCodec } = require('zstd-codec');

function readCanvasFig(pathStr) {
  const buf = fs.readFileSync(pathStr);
  const prelude = buf.subarray(0, 8);
  const version = buf.readUInt32LE(8);
  let off = 12;
  const chunks = [];
  while (off < buf.length) {
    const len = buf.readUInt32LE(off);
    off += 4;
    chunks.push(buf.subarray(off, off + len));
    off += len;
  }
  return { buf, prelude, version, chunks };
}

function inflateRaw(u8) {
  return zlib.inflateRawSync(u8);
}

async function decode(pathStr) {
  const { prelude, version, chunks } = readCanvasFig(pathStr);
  const schemaRaw = inflateRaw(chunks[0]);
  const schema = decodeBinarySchema(new Uint8Array(schemaRaw));
  const compiled = compileSchema(schema);

  const zstd = await new Promise((resolve) => ZstdCodec.run((z) => resolve(z)));
  const mc = chunks[1];
  const isZ = mc[0] === 0x28 && mc[1] === 0xB5 && mc[2] === 0x2F && mc[3] === 0xFD;
  const mr = isZ ? Buffer.from(new zstd.Simple().decompress(mc)) : inflateRaw(mc);
  const msg = compiled.decodeMessage(new Uint8Array(mr));

  return { prelude, version, chunks, schema, compiled, msg, zstd };
}

function keyGuid(g) {
  return g ? `${g.sessionID}:${g.localID}` : '';
}

function buildGuidMap(nodes) {
  const m = new Map();
  for (const n of nodes) {
    if (n.guid) m.set(keyGuid(n.guid), n);
  }
  return m;
}

function buildChildren(nodes) {
  const children = new Map();
  for (const n of nodes) {
    const pg = n.parentIndex && n.parentIndex.guid;
    if (!pg || !n.guid) continue;
    const k = keyGuid(pg);
    if (!children.has(k)) children.set(k, []);
    children.get(k).push(n);
  }
  return children;
}

function collectSubtree(nodes, rootGuid) {
  const byGuid = buildGuidMap(nodes);
  const children = buildChildren(nodes);
  const out = [];
  const stack = [keyGuid(rootGuid)];
  const seen = new Set();
  while (stack.length) {
    const k = stack.pop();
    if (seen.has(k)) continue;
    seen.add(k);
    const node = byGuid.get(k);
    if (!node) continue;
    out.push(node);
    const kids = children.get(k) || [];
    for (const c of kids) {
      if (c.guid) stack.push(keyGuid(c.guid));
    }
  }
  return out;
}

function collectBlobIndices(obj, outSet) {
  if (obj == null) return;
  if (Array.isArray(obj)) {
    for (const it of obj) collectBlobIndices(it, outSet);
    return;
  }
  if (typeof obj !== 'object') return;
  for (const [k, v] of Object.entries(obj)) {
    if (typeof v === 'number') {
      if (/Blob$/.test(k) || /blob/.test(k)) outSet.add(v);
    } else if (v && typeof v === 'object') {
      collectBlobIndices(v, outSet);
    }
  }
}

function remapBlobIndices(obj, blobMap) {
  if (obj == null) return;
  if (Array.isArray(obj)) {
    for (const it of obj) remapBlobIndices(it, blobMap);
    return;
  }
  if (typeof obj !== 'object') return;
  for (const [k, v] of Object.entries(obj)) {
    if (typeof v === 'number') {
      if ((/Blob$/.test(k) || /blob/.test(k)) && blobMap.has(v)) {
        obj[k] = blobMap.get(v);
      }
    } else if (v && typeof v === 'object') {
      remapBlobIndices(v, blobMap);
    }
  }
}

function deepClone(x) {
  if (x == null) return x;
  if (Array.isArray(x)) return x.map(deepClone);
  if (x instanceof Uint8Array) return new Uint8Array(x);
  if (typeof x === 'object') {
    const o = {};
    for (const [k, v] of Object.entries(x)) o[k] = deepClone(v);
    return o;
  }
  return x;
}

function assembleCanvasFig({ prelude, version, schemaCompressed, messageCompressed, extraChunks }) {
  const header = Buffer.alloc(12);
  prelude.copy(header, 0);
  header.writeUInt32LE(version, 8);

  const parts = [header];
  const chunks = [schemaCompressed, messageCompressed, ...(extraChunks || [])];
  for (const ch of chunks) {
    const lenBuf = Buffer.alloc(4);
    lenBuf.writeUInt32LE(ch.length, 0);
    parts.push(lenBuf, Buffer.from(ch));
  }
  return Buffer.concat(parts);
}

(async () => {
  const mePath = process.argv[2];
  const exPath = process.argv[3];
  const outPath = process.argv[4];

  const names = [
    'Врачи. Настройки параметров поиска',
    'Врачи. Просмотр данных врача',
    'Мои записи. Ввод OTP',
    'Мои записи. Данные пользователя',
    'Мои записи. Данные записи на прием',
    'Group 2300',
  ];

  const me = await decode(mePath);
  const ex = await decode(exPath);

  const meNodes = me.msg.nodeChanges || [];
  const exNodes = ex.msg.nodeChanges || [];
  const meGuidSet = new Set(meNodes.filter(n => n.guid).map(n => keyGuid(n.guid)));

  const exFrames = exNodes.filter(n => n.type === 'FRAME');

  const roots = [];
  for (const name of names) {
    const r = exFrames.find(f => f.name === name);
    if (!r) {
      console.error('Missing root in example:', name);
      process.exit(2);
    }
    roots.push(r);
  }

  // Collect nodes to add
  const nodesToAdd = [];
  const addGuidSet = new Set();

  for (const r of roots) {
    const subtree = collectSubtree(exNodes, r.guid);
    for (const n of subtree) {
      const kg = n.guid ? keyGuid(n.guid) : '';
      if (!kg) continue;
      if (meGuidSet.has(kg)) continue; // already exists
      if (addGuidSet.has(kg)) continue;
      addGuidSet.add(kg);
      nodesToAdd.push(deepClone(n));
    }
  }

  // Fix parent of root frames if their parent doesn't exist in my doc
  const page1 = meNodes.find(n => n.type === 'CANVAS' && n.name === 'Page 1');
  const pageGuid = page1 && page1.guid;
  if (!pageGuid) {
    console.error('Could not find Page 1 in target');
    process.exit(3);
  }

  for (const n of nodesToAdd) {
    // Only adjust top-level imported frames (the roots) if their parent missing.
    if (n.type !== 'FRAME') continue;
    if (!names.includes(n.name)) continue;
    const pg = n.parentIndex && n.parentIndex.guid;
    if (!pg) continue;
    if (!meGuidSet.has(keyGuid(pg))) {
      n.parentIndex = { guid: deepClone(pageGuid), position: 'a' };
    }
  }

  // Blob remap for imported nodes
  const exBlobs = ex.msg.blobs || [];
  const meBlobs = me.msg.blobs || [];

  const needed = new Set();
  for (const n of nodesToAdd) collectBlobIndices(n, needed);

  // Only keep indices that are actually in range
  const neededSorted = [...needed].filter(i => Number.isInteger(i) && i >= 0 && i < exBlobs.length).sort((a,b)=>a-b);

  const blobMap = new Map();
  for (const idx of neededSorted) {
    const newIdx = meBlobs.length;
    meBlobs.push(deepClone(exBlobs[idx]));
    blobMap.set(idx, newIdx);
  }

  for (const n of nodesToAdd) remapBlobIndices(n, blobMap);

  // Append nodes
  meNodes.push(...nodesToAdd);
  me.msg.nodeChanges = meNodes;
  me.msg.blobs = meBlobs;

  // Encode and compress
  const encoded = Buffer.from(me.compiled.encodeMessage(me.msg));
  const simple = new me.zstd.Simple();
  const messageCompressed = Buffer.from(simple.compress(encoded, 3));

  const schemaCompressed = me.chunks[0];
  const extraChunks = me.chunks.slice(2); // pass-through

  const canvas = assembleCanvasFig({
    prelude: Buffer.from(me.prelude),
    version: me.version,
    schemaCompressed,
    messageCompressed,
    extraChunks,
  });

  fs.writeFileSync(outPath, canvas);

  fs.writeFileSync('merge_report.json', JSON.stringify({
    addedNodes: nodesToAdd.length,
    addedBlobs: neededSorted.length,
    outCanvas: outPath,
  }, null, 2), 'utf8');

  console.log('OK', 'addedNodes', nodesToAdd.length, 'addedBlobs', neededSorted.length);
})();
