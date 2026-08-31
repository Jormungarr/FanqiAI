# -*- coding: utf-8 -*-
"""用当前引擎重放 replay_samples,逐步骤对比 board 与样本记录是否一致"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import GameState, Piece
from replay import deserialize_board

SAMPLES = [
    Path(__file__).resolve().parent.parent / 'replay_samples' / 'test_replay.json',
    Path(__file__).resolve().parent.parent / 'replay_samples' / 'generated_replay.json',
    Path(__file__).resolve().parent.parent / 'replay_samples' / 'generated_kifu.json',
]

def load_moves(p):
    data = json.loads(p.read_text(encoding='utf-8'))
    if isinstance(data, dict) and 'moves' in data:
        return data['moves']
    return data

def main():
    any_fail = False
    for p in SAMPLES:
        if not p.exists():
            print(f'SKIP missing: {p.name}')
            continue
        moves = load_moves(p)
        if not moves:
            print(f'{p.name}: empty, skip')
            continue
        g = GameState()
        g.board = deserialize_board(moves[0]['board'])
        g.scores = dict(moves[0].get('scores') or {'R': 60, 'B': 60})
        g.moves_since_capture = 0
        # 样本语义:每个 step 的 board 是动作执行后的局面,board0 已含 action_0 的结果
        # 因此从 board0 出发,依次应用 action_1..action_{n-1},每步应与 moves[i]['board']/scores 一致
        failures = []
        for i in range(1, len(moves)):
            ok, reason = g.apply_action(tuple(moves[i]['action']))
            # apply_action 返回 (game_over, reason),reason 为动作类型表示合法,否则为错误消息
            if reason not in ('move', 'flip', 'capture', 'cannon'):
                failures.append((i, moves[i].get('action'), 'ENGINE_REJECTED: ' + reason, None, None))
                break
            exp = moves[i]['board']
            exp_s = moves[i].get('scores')
            got = ['.' if c is None else f'{c.color}:{c.ptype}:{int(c.revealed)}' for c in g.board]
            if got != exp or (exp_s and g.scores != dict(exp_s)):
                failures.append((i, moves[i].get('action'), moves[i].get('reason'), exp, got, exp_s, dict(g.scores)))
                break
        if failures:
            any_fail = True
            print(f'[MISMATCH] {p.name}: step {failures[0][0]} action={failures[0][1]} reason={failures[0][2]}')
            if failures[0][3] is not None:
                for j, (a, b) in enumerate(zip(failures[0][3], failures[0][4])):
                    if a != b:
                        print(f'    cell {j}: sample={a!r} engine={b!r}')
                        if j > 8:
                            break
            else:
                print('    detail:', failures[0][2])
        else:
            print(f'[OK] {p.name}: {len(moves)} steps replay consistently with current engine')
    print('ALL_PASS' if not any_fail else 'HAS_MISMATCH')

if __name__ == '__main__':
    main()
