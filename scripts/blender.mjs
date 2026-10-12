// Blender をコマンドラインで動かしてアセットを生成・書き出す
//   node scripts/blender.mjs export   … blender/world.blend をそのまま書き出す（Blender で手作業した変更を反映）
//   node scripts/blender.mjs rebuild  … スクリプトから世界を作り直して書き出す（world.blend は上書きされる）
import { spawnSync } from 'node:child_process';
import { existsSync, readdirSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const bdir = join(root, 'blender');

function findBlender() {
  if (process.env.BLENDER && existsSync(process.env.BLENDER)) return process.env.BLENDER;
  const base = 'C:\\Program Files\\Blender Foundation';
  if (existsSync(base)) {
    const vers = readdirSync(base).filter((d) => d.startsWith('Blender')).sort().reverse();
    for (const v of vers) {
      const exe = join(base, v, 'blender.exe');
      if (existsSync(exe)) return exe;
    }
  }
  for (const p of ['/Applications/Blender.app/Contents/MacOS/Blender', '/usr/bin/blender', '/snap/bin/blender']) if (existsSync(p)) return p;
  return 'blender';
}

function run(args) {
  const exe = findBlender();
  console.log(`> ${exe} ${args.join(' ')}`);
  const r = spawnSync(exe, args, { cwd: bdir, stdio: 'inherit' });
  if (r.status !== 0) process.exit(r.status || 1);
}

const mode = process.argv[2] || 'export';
const blend = join(bdir, 'world.blend');
if (mode === 'rebuild') {
  run(['-b', '--factory-startup',
    '--python', 'build_world.py', '--python', 'build_characters.py', '--python', 'build_monsters.py',
    '--python-expr', `import bpy; bpy.ops.wm.save_as_mainfile(filepath=r"${blend}")`]);
}
run(['-b', blend, '--python', 'export_game.py']);
console.log('アセットを public/assets に書き出しました');
