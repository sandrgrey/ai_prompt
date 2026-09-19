const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function setup() {
  const listeners = [];
  class Transfer {
    constructor() {
      this.files = [];
      this.items = {add: file => this.files.push(file)};
    }
  }
  const document = {documentElement:{classList:{add(){}}}, addEventListener(type, fn, capture) { listeners.push({type, fn, capture}); }};
  const source = fs.existsSync('assets/app.js') ? fs.readFileSync('assets/app.js','utf8') : '() => document.documentElement.classList.add("dark")';
  vm.runInNewContext(`(${source})()`, {document, DataTransfer:Transfer});
  return listeners;
}
test('replacement drop survives browser clearing the native file store after dispatch', async () => {
  const listeners = setup();
  const native = {files:[{name:'replacement.png'}]};
  const event = {dataTransfer:native, composedPath:()=>[{id:'source-image'}]};
  for (const l of listeners) if(l.type==='drop') l.fn(event);
  // Gradio clears the old image, awaits tick(), then reads this same event.
  native.files = [];
  await Promise.resolve();
  assert.equal(event.dataTransfer.files.length, 1);
  assert.equal(event.dataTransfer.files[0].name, 'replacement.png');
});
test('does not alter other drop targets or non-file drags', () => {
  for (const event of [
    {dataTransfer:{files:[{name:'other.png'}]}, composedPath:()=>[{id:'other'}]},
    {dataTransfer:{files:[]}, composedPath:()=>[{id:'source-image'}]},
  ]) {
    const original = event.dataTransfer;
    for (const l of setup()) if(l.type==='drop') l.fn(event);
    assert.equal(event.dataTransfer, original);
  }
});
