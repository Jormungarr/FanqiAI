"""MCTS 强 AI 对战基准:分别对阵随机 AI 与偏好 AI,统计胜负。

用法: python tools/bench_mcts.py [时间预算/步] [每对手局数]
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from engine import GameState
    from ai import RandomAgent, PreferHighValueAgent
    from ai_mcts import MCTSAgent
except ImportError:
    from game.fanqi.engine import GameState
    from game.fanqi.ai import RandomAgent, PreferHighValueAgent
    from game.fanqi.ai_mcts import MCTSAgent


def play(agent_r, agent_b, seed):
    gs = GameState(seed=seed)
    turn = 'R'
    while True:
        agent = agent_r if turn == 'R' else agent_b
        acts = gs.get_legal_actions(turn)
        if not acts:
            return gs.winner() or 'DRAW'
        a = agent.select(gs)
        if a is None:
            a = acts[0]
        gs.apply_action(a)
        w = gs.winner()
        if w is not None:
            return w
        turn = 'B' if turn == 'R' else 'R'


def run(label, mk_opp, rounds, budget, policy):
    wins = {'MCTS': 0, 'opp': 0, 'DRAW': 0}
    t0 = time.time()
    for i in range(rounds):
        # MCTS 执红
        w = play(MCTSAgent('R', time_budget=budget, rollout_policy=policy), mk_opp('B'), 100 + i)
        wins['MCTS' if w == 'R' else ('opp' if w == 'B' else 'DRAW')] += 1
        # MCTS 执黑
        w = play(mk_opp('R'), MCTSAgent('B', time_budget=budget, rollout_policy=policy), 2000 + i)
        wins['MCTS' if w == 'B' else ('opp' if w == 'R' else 'DRAW')] += 1
        print(f'  {label} 第{i+1}轮完成,累计 {wins}', flush=True)
    print(f'{label}: MCTS {wins["MCTS"]} - 对手 {wins["opp"]} - 和 {wins["DRAW"]} | 耗时 {time.time()-t0:.0f}s')


if __name__ == '__main__':
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 0.4
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    policy = sys.argv[3] if len(sys.argv) > 3 else 'prefer'
    opp = sys.argv[4] if len(sys.argv) > 4 else 'both'
    print(f'MCTS 预算 {budget}s/步 rollout={policy}, 每对手 {rounds} 轮')
    if opp in ('both', 'random'):
        run('vs 随机AI', lambda c: RandomAgent(c), rounds, budget, policy)
    if opp in ('both', 'prefer'):
        run('vs 偏好AI', lambda c: PreferHighValueAgent(c), rounds, budget, policy)
