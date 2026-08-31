"""MCTS 逐层诊断:对称性测试 + 单局逐步跟踪,定位全输根因。

1) 对称测试:同预算 MCTS 自对弈,胜率应 ~50%;强预算 vs 弱预算,强者应占优
2) 逐步跟踪:MCTS vs Prefer 一局,打印 MCTS 每步评估
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import GameState
from ai import PreferHighValueAgent
from ai_mcts import MCTSAgent, evaluate_moves


def play(agent_r, agent_b, seed, trace=False):
    gs = GameState(seed=seed)
    turn = 'R'
    ply = 0
    while True:
        agent = agent_r if turn == 'R' else agent_b
        acts = gs.get_legal_actions(turn)
        if not acts:
            return gs.winner() or 'DRAW', ply, gs.scores
        a = agent.select(gs)
        if a is None:
            a = acts[0]
        if trace and isinstance(agent, MCTSAgent):
            info = None
        gs.apply_action(a)
        ply += 1
        w = gs.winner()
        if w is not None:
            return w, ply, gs.scores
        turn = 'B' if turn == 'R' else 'R'


def sym_test():
    print('== 对称测试: MCTS(0.8s) vs MCTS(0.8s) ==', flush=True)
    wins = {'R': 0, 'B': 0, 'DRAW': 0}
    for i in range(2):
        w, ply, sc = play(MCTSAgent('R', time_budget=0.8, rollout_policy='prefer'),
                          MCTSAgent('B', time_budget=0.8, rollout_policy='prefer'),
                          300 + i)
        wins[w] += 1
        print(f'  局{i}: winner={w} ply={ply} scores={sc}', flush=True)
    print('  结果:', wins, flush=True)

    print('== 强弱测试: MCTS(1.2s) vs MCTS(0.15s) ==', flush=True)
    wins = {'strong': 0, 'weak': 0, 'DRAW': 0}
    for i in range(2):
        w, ply, sc = play(MCTSAgent('R', time_budget=1.2, rollout_policy='prefer'),
                          MCTSAgent('B', time_budget=0.15, rollout_policy='prefer'),
                          400 + i)
        wins['strong' if w == 'R' else ('weak' if w == 'B' else 'DRAW')] += 1
        print(f'  局{i}: winner={w} ply={ply} scores={sc}', flush=True)
    print('  结果:', wins, flush=True)


def trace_game(seed=777):
    print(f'== 逐步跟踪: MCTS(1.0s, prefer) vs Prefer, seed={seed} ==', flush=True)
    gs = GameState(seed=seed)
    mcts = MCTSAgent('R', time_budget=1.0, rollout_policy='prefer')
    pref = PreferHighValueAgent('B')
    turn = 'R'
    ply = 0
    while True:
        agent = mcts if turn == 'R' else pref
        acts = gs.get_legal_actions(turn)
        if not acts:
            print('无合法动作,终局', flush=True)
            break
        if turn == 'R':
            info = evaluate_moves(gs, 'R', time_budget=1.0, rollout_policy='prefer')
            top = info['moves'][:3]
            print(f'  [{ply}] R 评估: 模拟{info["total"]}次', flush=True)
            for t in top:
                print(f'      {t["action"]} 胜率{t["win_rate"]:.1%} ({t["visits"]}次)', flush=True)
            a = mcts.select(gs)
        else:
            a = pref.select(gs)
        gs.apply_action(a)
        ply += 1
        w = gs.winner()
        if w is not None:
            print(f'  终局: winner={w} ply={ply} scores={gs.scores}', flush=True)
            return
        turn = 'B' if turn == 'R' else 'R'


if __name__ == '__main__':
    sym_test()
    trace_game()
