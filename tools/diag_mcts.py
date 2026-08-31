"""MCTS 单步诊断:构造「红将一步吃黑将即获胜」的局面,验证搜索能选出必赢动作。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import GameState, Piece
from ai_mcts import evaluate_moves, MCTSAgent

# 局面:红将(0,0)、黑将(0,1)均明棋,黑方仅剩 30 分
# 红吃黑将 -> 黑 30-30=0 -> 红立即获胜;其余动作(翻暗棋)不会立即获胜
g = GameState(seed=1)
g.board = [None] * 32
rj = Piece('J', 'R'); rj.revealed = True
bj = Piece('J', 'B'); bj.revealed = True
g.board[0] = rj   # (0,0)
g.board[1] = bj   # (0,1)
g.scores = {'R': 60, 'B': 30}

info = evaluate_moves(g, 'R', time_budget=1.0)
print(f'模拟 {info["total"]} 次, {len(info["moves"])} 个候选:')
for m in info['moves'][:6]:
    print(f'  {m["action"]} 胜率 {m["win_rate"]:.1%} ({m["visits"]}次)')

best = info['moves'][0]
assert best['action'][0] == 'capture' and best['action'][1] == 0 and best['action'][2] == 1, \
    f'MCTS 未选出必赢的吃将动作: {best}'
assert best['win_rate'] > 0.9, f'吃将胜率应接近 100%: {best}'
print('诊断 OK: MCTS 选出必赢动作且胜率接近 100%')

# 反向:黑将先手同样能吃红将获胜
g2 = GameState(seed=1)
g2.board = [None] * 32
rj2 = Piece('J', 'R'); rj2.revealed = True
bj2 = Piece('J', 'B'); bj2.revealed = True
g2.board[0] = rj2
g2.board[1] = bj2
g2.scores = {'R': 30, 'B': 60}
info2 = evaluate_moves(g2, 'B', time_budget=1.0)
best2 = info2['moves'][0]
assert best2['action'] == ('capture', 1, 0), f'MCTS 未选出黑吃将: {best2}'
print('诊断 OK: 黑方同样能选出必赢动作')
