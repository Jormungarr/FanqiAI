"""Fanqi 人机对战 HTTP 服务器。

复用 engine.py 的规则引擎与 ai.py 的 Agent,为 web_ui/play.html 提供对局 API:
  POST /api/new    创建新对局(玩家颜色与先手颜色随机,符合规则)
  POST /api/legal  查询某枚己方明棋的合法走法(用于前端高亮)
  POST /api/move   执行玩家一步;若未结束,AI 立即回应一步
  GET  /api/state  获取当前对局状态(公开信息)
同时以静态文件方式提供 web_ui/ 下的页面。

运行: python game_server.py [--port 8000]
"""

import argparse
import json
import os
import random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

try:
    from engine import GameState
    from ai import RandomAgent, PreferHighValueAgent
    from ai_mcts import MCTSAgent, evaluate_moves
except ImportError:
    from game.fanqi.engine import GameState
    from game.fanqi.ai import RandomAgent, PreferHighValueAgent
    from game.fanqi.ai_mcts import MCTSAgent, evaluate_moves

ROOT = os.path.dirname(os.path.abspath(__file__))

COLOR_CN = {'R': '红方', 'B': '黑方'}


def action_text(action, color):
    """把引擎动作转成人类可读文本,如「红方 炮击 (0,0)→(0,3)」"""
    kind = action[0]

    def rc(i):
        return f"({i // 8},{i % 8})"

    name = COLOR_CN.get(color, color)
    if kind == 'flip':
        return f"{name} 翻 {rc(action[1])}"
    if kind == 'move':
        return f"{name} 移 {rc(action[1])}→{rc(action[2])}"
    if kind == 'capture':
        return f"{name} 吃 {rc(action[1])}→{rc(action[2])}"
    if kind == 'cannon':
        return f"{name} 炮击 {rc(action[1])}→{rc(action[2])}"
    return str(action)


def public_board(game):
    """对外只暴露公开信息:暗棋一律显示 'H',明棋 'R:S:1',空格 '.'"""
    out = []
    for p in game.board:
        if p is None:
            out.append('.')
        elif not p.revealed:
            out.append('H')
        else:
            out.append(f"{p.color}:{p.ptype}:1")
    return out


class Session:
    """单局人机对弈会话。"""

    def __init__(self, seed=None, agent='prefer'):
        self.seed = seed
        self.agent_name = agent
        self.reset()

    def reset(self):
        self.game = GameState(seed=self.seed)
        self.human_color = random.choice(('R', 'B'))
        self.ai_color = 'B' if self.human_color == 'R' else 'R'
        if self.agent_name == 'mcts':
            self.agent = MCTSAgent(self.ai_color, time_budget=1.5)
        elif self.agent_name == 'random':
            self.agent = RandomAgent(self.ai_color, seed=self.seed)
        else:
            self.agent = PreferHighValueAgent(self.ai_color, seed=self.seed)
        # 定制规则:红方先走
        self.turn = 'R'
        self.history = []
        self.over = False
        self.winner = None
        self.end_reason = None
        if self.turn == self.ai_color:
            self._ai_step()

    def _apply_step(self, color, action):
        """执行一步并记录;翻棋/炮盲狙时记录被翻开的棋子,供前端展示「翻开得到什么」"""
        tgt = None
        was_hidden = False
        if action[0] in ('flip', 'cannon'):
            idx = action[1] if action[0] == 'flip' else action[2]
            tgt = self.game.board[idx]
            # 必须在执行前判断:执行后棋子已被翻开
            was_hidden = tgt is not None and not tgt.revealed
        ok, reason = self.game.apply_action(action)
        entry = {'player': color, 'action': action, 'reason': reason}
        if was_hidden:
            entry['revealed'] = f"{tgt.color}:{tgt.ptype}"
        self.history.append(entry)
        return ok, reason

    def _ai_step(self):
        action = self.agent.select(self.game)
        if action is None:
            self.over = True
            self.winner = self.game.winner() or 'DRAW'
            self.end_reason = 'no legal move'
            return
        ok, reason = self._apply_step(self.ai_color, action)
        if ok:
            self.over = True
            self.winner = self.game.winner()
            self.end_reason = reason
        else:
            self.turn = self.human_color

    def player_move(self, action):
        if self.over:
            return False, 'game over'
        if self.turn != self.human_color:
            return False, 'not your turn'
        # apply_action 返回 (ok, reason):ok=True 表示游戏结束,reason 以 'invalid' 开头表示非法走法
        ok, reason = self._apply_step(self.human_color, action)
        if ok:
            self.over = True
            self.winner = self.game.winner()
            self.end_reason = reason
            return True, None
        if reason.startswith('invalid'):
            self.history.pop()
            return False, reason
        self.turn = self.ai_color
        self._ai_step()
        return True, None

    def legal_for_src(self, src):
        p = self.game.board[src]
        if p is None or not p.revealed or p.color != self.human_color:
            return []
        moves = []
        for a in self.game.get_legal_actions(self.human_color):
            if a[0] != 'flip' and a[1] == src:
                moves.append({'dst': a[2], 'type': a[0]})
        return moves

    def state_json(self, last=None):
        return {
            'board': public_board(self.game),
            'human_color': self.human_color,
            'turn': self.turn,
            'scores': dict(self.game.scores),
            'over': self.over,
            'winner': self.winner,
            'end_reason': self.end_reason,
            'history': [
                {'player': h['player'], 'action': h['action'],
                 'text': action_text(h['action'], h['player']), 'reason': h['reason'],
                 'revealed': h.get('revealed')}
                for h in self.history
            ],
            'last': last,
        }


session = Session()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print('[http]', fmt % args)

    def _send_json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode('utf-8'))
        except Exception:
            return {}

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/state':
            self._send_json(session.state_json())
            return
        if path in ('/', '/web_ui/'):
            self.send_response(302)
            self.send_header('Location', '/web_ui/play.html')
            self.end_headers()
            return
        # 静态文件(仅限项目目录内,防路径穿越)
        rel = path.lstrip('/')
        full = os.path.normpath(os.path.join(ROOT, rel))
        if not full.startswith(ROOT) or not os.path.isfile(full):
            self.send_response(404)
            self.end_headers()
            return
        ctype = 'text/html; charset=utf-8'
        if full.endswith('.js'):
            ctype = 'application/javascript; charset=utf-8'
        elif full.endswith('.css'):
            ctype = 'text/css; charset=utf-8'
        elif full.endswith('.json'):
            ctype = 'application/json; charset=utf-8'
        with open(full, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()
        if path == '/api/new':
            global session
            session = Session(seed=body.get('seed'), agent=body.get('agent', 'prefer'))
            self._send_json(session.state_json())
        elif path == '/api/legal':
            src = body.get('src')
            if src is None or not isinstance(src, int):
                self._send_json({'error': 'bad src'}, 400)
                return
            self._send_json({'ok': True, 'src': src, 'moves': session.legal_for_src(src)})
        elif path == '/api/move':
            action = body.get('action')
            if not isinstance(action, list) or not action:
                self._send_json({'error': 'bad action'}, 400)
                return
            ok, err = session.player_move(action)
            if not ok:
                self._send_json({'error': err or 'invalid move'}, 400)
                return
            self._send_json(session.state_json(last=action_text(action, session.human_color)))
        elif path == '/api/advise':
            # 决策建议:对当前玩家局面做 MCTS 搜索,输出每个动作的模拟胜率
            if session.over:
                self._send_json({'error': '对局已结束'}, 400)
                return
            if session.turn != session.human_color:
                self._send_json({'error': '还没轮到你走子'}, 400)
                return
            info = evaluate_moves(session.game, session.human_color, time_budget=2.0)
            moves = [
                {'action': m['action'],
                 'text': action_text(m['action'], session.human_color),
                 'win_rate': round(m['win_rate'], 4),
                 'visits': m['visits']}
                for m in info['moves']
            ]
            self._send_json({'ok': True, 'moves': moves, 'total': info['total']})
        elif path == '/api/coach/analyze':
            # 指导模式:对任意编辑局面做 MCTS 搜索,输出局面胜率与每个动作的胜率
            board = body.get('board')
            if not isinstance(board, list) or len(board) != 32:
                self._send_json({'error': 'board must be a 32-cell list'}, 400)
                return
            turn = body.get('turn', 'R')
            if turn not in ('R', 'B'):
                self._send_json({'error': 'bad turn'}, 400)
                return
            scores = body.get('scores')
            if scores is not None and (not isinstance(scores, dict)
                                       or 'R' not in scores or 'B' not in scores):
                self._send_json({'error': 'bad scores'}, 400)
                return
            seed = body.get('seed')
            try:
                time_budget = float(body.get('time_budget', 2.5))
            except (TypeError, ValueError):
                time_budget = 2.5
            try:
                game = GameState.from_setup(board, scores=scores, seed=seed)
            except ValueError as e:
                self._send_json({'error': str(e)}, 400)
                return
            acts = game.get_legal_actions(turn)
            if not acts:
                self._send_json({'ok': True, 'turn': turn, 'eval_win_rate': None,
                                 'total': 0, 'moves': [],
                                 'note': '该局面无合法动作(已终局)'})
                return
            info = evaluate_moves(game, turn, time_budget=time_budget)
            moves = [
                {'action': m['action'],
                 'text': action_text(m['action'], turn),
                 'win_rate': round(m['win_rate'], 4),
                 'visits': m['visits']}
                for m in info['moves']
            ]
            self._send_json({'ok': True, 'turn': turn,
                             'eval_win_rate': round(info['turn_win_rate'], 4)
                             if info['turn_win_rate'] is not None else None,
                             'total': info['total'], 'moves': moves})
        else:
            self._send_json({'error': 'not found'}, 404)


def main():
    parser = argparse.ArgumentParser(description='Fanqi 人机对战服务器')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f'Fanqi 人机对战服务器已启动: http://{args.host}:{args.port}/web_ui/play.html')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('已停止')


if __name__ == '__main__':
    main()
