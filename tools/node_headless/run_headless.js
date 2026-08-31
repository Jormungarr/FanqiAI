const fs = require('fs');
const path = require('path');
const {JSDOM} = require('jsdom');

const htmlPath = path.resolve(__dirname, '..', '..', 'web_ui', 'index.html');
const baseDir = path.dirname(htmlPath);
const html = fs.readFileSync(htmlPath, 'utf8');

const dom = new JSDOM(html, {
  runScripts: 'dangerously',
  resources: 'usable',
  url: 'http://localhost/',
  beforeParse(window) {
    // polyfill fetch to read local files relative to web_ui
    window.fetch = function(p){
      // resolve relative to baseDir
      const resolved = path.resolve(baseDir, p);
      try{
        const text = fs.readFileSync(resolved, 'utf8');
        return Promise.resolve({ ok: true, text: async ()=> text, json: async ()=> JSON.parse(text) });
      }catch(err){
        return Promise.resolve({ ok: false, status: 404, text: async ()=> '', json: async ()=> {throw err;} });
      }
    };
    // minimal FileReader polyfill for fileInput usage (not needed here)
    class FileReader {
      constructor(){ this.onload=null; }
      readAsText(file){
        const data = fs.readFileSync(file.path || file, 'utf8');
        if(this.onload) this.onload({ target: { result: data }});
      }
    }
    window.FileReader = FileReader;

    // capture console
    const origLog = window.console.log.bind(window.console);
    window.__collectedLogs = [];
    ['log','error','warn','info'].forEach(k=>{
      const orig = window.console[k].bind(window.console);
      window.console[k] = function(){ window.__collectedLogs.push({level:k, args: Array.from(arguments)}); orig.apply(null, arguments); };
    });
  }
});

// wait for scripts to run
setTimeout(()=>{
  const win = dom.window;
  console.log('--- collected logs ---');
  (win.__collectedLogs || []).forEach(l=> console.log(l.level, ...l.args));
  try{
    const dbg = win.document.getElementById('debug');
    if(dbg) console.log('DEBUG PANEL:\n' + dbg.textContent);
    const board = win.document.getElementById('board');
    console.log('BOARD CHILD COUNT:', board ? board.children.length : 'no-board');
  }catch(e){
    console.error('error reading DOM', e);
  }
  process.exit(0);
}, 800);
