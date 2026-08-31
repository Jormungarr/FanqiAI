"""验证炮击规则:盲狙先翻开展示、炮移动到目标格、误伤不计分"""
import sys

sys.path.insert(0, r'd:\workspace\game\fanqi')
from engine import GameState, Piece


def make_scene():
    g = GameState(seed=0)
    g.board = [None] * 32
    cannon = Piece('C', 'R')
    cannon.revealed = True
    g.board[0] = cannon          # 红炮在 (0,0)
    g.board[1] = Piece('P', 'R')  # 炮架 (0,1)
    return g, cannon


# 场景1:盲狙对方暗棋(黑士) -> 对方扣分 + 炮移动到目标格
g, cannon = make_scene()
tgt = Piece('S', 'B')            # 暗棋黑士
g.board[2] = tgt
acts = [a for a in g.get_legal_actions('R') if a[0] == 'cannon']
assert acts, 'should have cannon action'
ok, reason = g.apply_action(acts[0])
assert ok is False and reason == 'cannon'
assert g.board[0] is None, 'src must be empty after cannon'
assert g.board[2] is cannon, 'cannon must move to target cell'
assert g.scores['R'] == 60 and g.scores['B'] == 50, f'scores: {g.scores}'
assert tgt.revealed, 'blind target must be revealed before removal'
print('场景1 OK: 盲狙对方暗棋 -> 黑方剩50, 炮移至目标格, 目标先翻开展示')

# 场景2:误伤己方暗棋 -> 翻开展示并自扣分, 炮仍移动
g, cannon = make_scene()
own = Piece('N', 'R')            # 己方暗棋马(5分)
g.board[2] = own
acts = [a for a in g.get_legal_actions('R') if a[0] == 'cannon']
ok, reason = g.apply_action(acts[0])
assert g.board[0] is None and g.board[2] is cannon
assert g.scores['R'] == 55 and g.scores['B'] == 60, f'friendly fire must deduct own score: {g.scores}'
assert own.revealed
print('场景2 OK: 误伤己方暗棋 -> 先翻开展示, 红方自扣5分, 炮仍移动到目标格')

# 场景3:炮击对方明棋 -> 对方扣分 + 移动
g, cannon = make_scene()
enemy = Piece('X', 'B')
enemy.revealed = True
g.board[2] = enemy
acts = [a for a in g.get_legal_actions('R') if a[0] == 'cannon']
ok, reason = g.apply_action(acts[0])
assert g.board[0] is None and g.board[2] is cannon
assert g.scores['R'] == 60 and g.scores['B'] == 55, f'scores: {g.scores}'
print('场景3 OK: 炮击对方明棋 -> 黑方剩55, 炮移动到目标格')

# 场景4:将帅不能吃兵卒,兵可吃将
jiang = Piece('J', 'R'); jiang.revealed = True
bing = Piece('P', 'B'); bing.revealed = True
for seed in range(10):
    g = GameState(seed=seed)
    g.board = [None] * 32
    g.board[0] = jiang
    g.board[1] = bing
    ok, reason = g.apply_action(('capture', 0, 1))
    assert not ok, 'jiang must not capture bing'
    acts = [a for a in g.get_legal_actions('R') if a[0] == 'capture']
    assert not acts, 'generator must not offer jiang->bing capture'
g = GameState(seed=0)
g.board = [None] * 32
j2 = Piece('J', 'B'); j2.revealed = True
b2 = Piece('P', 'R'); b2.revealed = True
g.board[0] = j2
g.board[1] = b2
ok, reason = g.apply_action(('capture', 1, 0))
assert ok is False and reason == 'capture', reason
assert g.board[0] is b2 and g.board[1] is None, 'bing moves onto jiang cell'
assert g.scores['B'] == 30, f'jiang captured, B score: {g.scores}'
print('场景4 OK: 将帅不能吃兵, 兵可吃将(黑方被扣30分)')

# 场景5:炮不能普通移动/吃子,只能炮击
g = GameState(seed=0)
g.board = [None] * 32
c2 = Piece('C', 'R'); c2.revealed = True
g.board[0] = c2
g.board[1] = Piece('P', 'B')  # 相邻对方明棋
acts = [a for a in g.get_legal_actions('R') if a[0] in ('move', 'capture')]
assert not acts, f'cannon must not have normal moves: {acts}'
ok, reason = g.apply_action(('move', 0, 2))
assert not ok, 'cannon must not move directly'
ok, reason = g.apply_action(('capture', 0, 1))
assert not ok, 'cannon must not capture directly'
print('场景5 OK: 炮不能普通移动/吃子, 只能炮击')

# 场景6:同级相吃,谁先吃谁存活
# 红车先吃黑车:红车存活并占据目标格,黑方扣分
g = GameState(seed=0)
g.board = [None] * 32
r1 = Piece('R', 'R'); r1.revealed = True   # 红车
b1 = Piece('R', 'B'); b1.revealed = True   # 黑车(同级)
g.board[0] = r1
g.board[1] = b1
ok, reason = g.apply_action(('capture', 0, 1))
assert ok is False and reason == 'capture'
assert g.board[0] is None and g.board[1] is r1, 'red attacker survives on target cell'
assert g.scores['R'] == 60 and g.scores['B'] == 55, f'scores: {g.scores}'
# 反向:黑车先吃红车,黑车存活
g2 = GameState(seed=0)
g2.board = [None] * 32
r2 = Piece('R', 'R'); r2.revealed = True
b2 = Piece('R', 'B'); b2.revealed = True
g2.board[0] = r2
g2.board[1] = b2
ok, reason = g2.apply_action(('capture', 1, 0))
assert ok is False and reason == 'capture'
assert g2.board[1] is None and g2.board[0] is b2, 'black attacker survives'
assert g2.scores['R'] == 55 and g2.scores['B'] == 60, f'scores: {g2.scores}'
print('场景6 OK: 同级相吃谁先吃谁存活(红吃黑/黑吃红), 对方扣分')

# 回归:50 局自我对弈无异常
wins = {'R': 0, 'B': 0, 'DRAW': 0}
invalid = 0
for seed in range(50):
    g = GameState(seed=seed)
    from ai import RandomAgent
    agents = {'R': RandomAgent('R', seed), 'B': RandomAgent('B', seed + 1)}
    turn = 'R'
    while True:
        a = agents[turn].select(g)
        if a is None:
            break
        ok, reason = g.apply_action(a)
        if reason.startswith('invalid'):
            invalid += 1
        if ok:
            wins[g.winner()] += 1
            break
        turn = 'B' if turn == 'R' else 'R'
print('回归 50 局:', wins, 'invalid:', invalid)
assert invalid == 0

print('ALL CANNON TESTS PASSED')
