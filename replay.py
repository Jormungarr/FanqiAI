import json
from typing import List, Dict, Any


def serialize_board(board) -> List[str]:
    out = []
    for p in board:
        if p is None:
            out.append('.')
        else:
            out.append(f"{p.color}:{p.ptype}:{int(p.revealed)}")
    return out


def deserialize_board(arr):
    # not used for engine loading, kept for completeness
    board = []
    for cell in arr:
        if cell == '.':
            board.append(None)
        else:
            color, ptype, rev = cell.split(':')
            from engine import Piece
            pc = Piece(ptype, color)
            pc.revealed = bool(int(rev))
            board.append(pc)
    return board


def save_replay(path: str, replay: List[Dict[str, Any]]):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(replay, f, ensure_ascii=False, indent=2)


def load_replay(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


HTML_TEMPLATE = '''<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>Fanqi Replay</title>
<style>
  body{font-family: sans-serif}
  .board{display:grid;grid-template-columns:repeat(8,40px);gap:4px}
  .cell{width:40px;height:40px;display:flex;align-items:center;justify-content:center;border:1px solid #ccc}
  .R{background:#ffecec}
  .B{background:#ecf0ff}
  .empty{background:#fafafa;border-color:#eee}
  .hidden{background:#444;color:#888;border-color:#555}
</style>
</head>
<body>
<div>
  <button id="play">Play</button>
  <button id="pause">Pause</button>
  <label>Speed: <input id="speed" type="range" min="50" max="2000" value="500"></label>
  <span id="info"></span>
</div>
<div id="board" class="board"></div>
<script>
const states = REPLAY_STATES;
const rows = 4, cols = 8;
const boardEl = document.getElementById('board');
const info = document.getElementById('info');
let idx = 0, timer=null, delay=500;

function render(state){
  boardEl.innerHTML='';
  state.board.forEach(cell=>{
    const d=document.createElement('div'); d.className='cell';
    if(cell=='.'){ d.textContent=''; d.classList.add('empty'); }
    else{
      const parts=cell.split(':'); const color=parts[0], p=parts[1], rev=parts[2];
      d.textContent = rev=='1'? (color+p) : '■';
      d.classList.add(color);
      if(rev=='0') d.classList.add('hidden');
    }
    boardEl.appendChild(d);
  });
  info.textContent = `step ${state.step} ${state.player} ${state.action} scores R/B:${state.scores.R}/${state.scores.B}`;
}

function step(){
  if(idx>=states.length){ clearInterval(timer); timer=null; info.textContent = '播放完毕，共 '+states.length+' 步。再点 Play 可重新播放'; return; }
  render(states[idx]); idx++;
}

document.getElementById('play').onclick=()=>{ if(timer) clearInterval(timer); if(idx>=states.length){ idx=0; } timer=setInterval(step,delay); };
document.getElementById('pause').onclick=()=>{ if(timer) clearInterval(timer); timer=null; };
document.getElementById('speed').oninput=function(){ delay=parseInt(this.value); if(timer){ clearInterval(timer); timer=setInterval(step,delay); }};

render(states[0]);
</script>
</body>
</html>
'''


def export_html(path: str, replay: List[Dict[str, Any]]):
    # prepare JS-serializable states
    states = []
    for i, s in enumerate(replay):
        states.append({
            'step': i,
            'player': s.get('player'),
            'action': s.get('action'),
            'scores': s.get('scores'),
            'board': s.get('board')
        })
    html = HTML_TEMPLATE.replace('REPLAY_STATES', json.dumps(states))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)


def save_kifu(path: str, replay: List[Dict[str, Any]], meta: Dict[str, Any] = None):
    """Save a simple kifu (棋谱) JSON. Format:
    {
      "meta": {...},
      "initial_board": [...],
      "moves": [ {player, action, reason, scores, board}, ... ]
    }
    """
    if meta is None:
        meta = {}
    k = {
        'meta': meta,
        'initial_board': replay[0].get('board') if len(replay) > 0 else [],
        'moves': []
    }
    for s in replay:
        k['moves'].append({
            'player': s.get('player'),
            'action': s.get('action'),
            'reason': s.get('reason'),
            'scores': s.get('scores'),
            'board': s.get('board')
        })
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(k, f, ensure_ascii=False, indent=2)


def load_kifu(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
