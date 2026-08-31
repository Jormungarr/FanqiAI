"""MCTS(蒙特卡洛树搜索)强 AI。

暗棋是高随机性游戏,规则价值很难手工建模;MCTS 通过大量随机模拟对局,
统计每个候选动作的最终胜率,天然适配暗棋,并能输出全部动作的胜率评估
(支撑「决策建议/教练」功能)。

搜索视角:以全信息视角(引擎知道所有暗棋内容)做树搜索,模拟中
flip/capture/cannon/误伤全部按规则自然发生,评估自动包含风险。

用法:
    from ai_mcts import MCTSAgent, evaluate_moves
    agent = MCTSAgent('B', time_budget=1.5)
    action = agent.select(state)              # 选最优动作
    info = evaluate_moves(state, 'B')         # 全部动作胜率排名
"""
import math
import random
import time

try:
    from .engine import GameState
except ImportError:
    from engine import GameState


def _other(color: str) -> str:
    return 'B' if color == 'R' else 'R'


class _Node:
    __slots__ = ('action', 'parent', 'children', 'visits', 'wins', 'untried', 'turn')

    def __init__(self, action=None, parent=None, turn=None):
        self.action = action      # 到达该节点的动作(root 为 None)
        self.parent = parent
        self.children = []
        self.visits = 0
        self.wins = 0.0           # 以「轮到本节点的玩家」视角统计(含 0.5 平局)
        self.untried = None       # 尚未展开的动作列表(None 表示未初始化)
        self.turn = turn          # 该节点轮到谁走


def _uct(child: _Node, parent_visits: int, c: float = 1.5) -> float:
    """UCT 值,越小越优先,与 min 选择配合。

    child.wins 统计的是「轮到 child 行动方(对手)」的胜率,己方胜率 = 1 - 对手胜率,
    argmin(对手胜率 - 探索) 等价于标准 argmax(己方胜率 + 探索)(常数 1 不影响比较);
    探索项取负号,使「访问少」的分支 UCT 值更小,从而被 min 优先选中。
    """
    if child.visits == 0:
        return float('-inf')
    exploit = child.wins / child.visits
    explore = c * math.sqrt(math.log(max(1, parent_visits)) / child.visits)
    return exploit - explore


def _rollout(state: GameState, turn: str, max_steps: int = 80, policy: str = 'prefer',
             rng=None):
    """模拟到终局;超出步数时按剩余分数差启发式截断。

    policy:
      'random' - 纯随机动作(标准 MCTS)
      'prefer' - 吃子/炮击优先(70%),否则优先翻棋,最后才移动(领域知识 rollout)
    rng: 随机源(传入 Random 实例可复现,None 用模块级 random)
    """
    if rng is None:
        rng = random
    steps = 0
    while steps < max_steps:
        w = state.winner()
        if w is not None:
            return w
        acts = state.get_legal_actions(turn)
        if not acts:
            return state.winner()
        if policy == 'prefer':
            eat = [a for a in acts if a[0] in ('capture', 'cannon')]
            if eat and rng.random() < 0.7:
                a = rng.choice(eat)
            else:
                flips = [a for a in acts if a[0] == 'flip']
                if flips and (not eat or rng.random() < 0.8):
                    a = rng.choice(flips)
                elif eat:
                    a = rng.choice(eat)
                else:
                    a = rng.choice(acts)
        else:
            a = rng.choice(acts)
        state.apply_action(a)
        turn = _other(turn)
        steps += 1
    w = state.winner()
    if w is not None:
        return w
    diff = state.scores['R'] - state.scores['B']
    return 'R' if diff > 0 else ('B' if diff < 0 else 'DRAW')


def search(state: GameState, color: str, time_budget: float = 2.0,
           max_iterations: int = 3000, rollout_steps: int = 80,
           rollout_policy: str = 'prefer', seed=None):
    """UCT 树搜索,返回根节点(所有子节点即各候选动作的统计)。

    seed: 播种 rollout 随机源,同 seed 可复现搜索结果(默认 None 不固定)。
    """
    rng = random.Random(seed) if seed is not None else None
    root = _Node(turn=color)
    root.untried = state.get_legal_actions(color)
    if not root.untried:
        return root
    deadline = time.time() + time_budget
    iterations = 0
    while iterations < max_iterations and time.time() < deadline:
        node = root
        s = state.clone()
        turn = color
        # 1) selection:已完全展开的节点沿 UCT 下探(取对手胜率最小的分支)
        while node.untried is not None and not node.untried and node.children:
            node = min(node.children, key=lambda ch: _uct(ch, node.visits))
            s.apply_action(node.action)
            turn = _other(turn)
        # 2) expansion:展开一个未尝试动作
        if node.untried:
            a = node.untried.pop()
            s.apply_action(a)
            turn = _other(turn)
            child = _Node(action=a, parent=node, turn=turn)
            child.untried = s.get_legal_actions(turn)
            node.children.append(child)
            node = child
        # 3) rollout:模拟到终局
        winner = _rollout(s, turn, rollout_steps, rollout_policy, rng)
        # 4) backprop:沿途更新统计
        while node is not None:
            node.visits += 1
            if winner == 'DRAW':
                node.wins += 0.5
            elif winner is not None and winner == node.turn:
                node.wins += 1.0
            node = node.parent
        iterations += 1
    return root


def evaluate_moves(state: GameState, color: str, time_budget: float = 2.0,
                   max_iterations: int = 3000, rollout_steps: int = 80,
                   rollout_policy: str = 'prefer', seed=None):
    """搜索并对每个候选动作给出胜率评估,按胜率降序。

    返回 {'moves': [{'action', 'win_rate', 'visits'}...], 'total': 根节点总访问数}
    seed: 透传给 search,同 seed 可复现评估。
    """
    root = search(state, color, time_budget, max_iterations, rollout_steps,
                  rollout_policy, seed)
    moves = []
    for ch in root.children:
        if ch.visits > 0:
            # 子节点统计的是轮到对手时的胜率,翻转成搜索方(玩家)视角
            opp_rate = ch.wins / ch.visits
            moves.append({'action': ch.action,
                          'win_rate': 1.0 - opp_rate,
                          'visits': ch.visits})
    moves.sort(key=lambda m: -m['win_rate'])
    # turn_win_rate: 根节点视角,即「当前轮到 color 行动时 color 的胜率」
    return {'moves': moves, 'total': root.visits,
            'turn_win_rate': root.wins / root.visits if root.visits else None}


class MCTSAgent:
    """基于 MCTS 的强 AI:每次决策做一次树搜索,选胜率最高且访问量达标的动作"""

    def __init__(self, color: str, time_budget: float = 2.0,
                 max_iterations: int = 3000, rollout_steps: int = 80,
                 rollout_policy: str = 'prefer'):
        self.color = color
        self.time_budget = time_budget
        self.max_iterations = max_iterations
        self.rollout_steps = rollout_steps
        self.rollout_policy = rollout_policy

    def select(self, state: GameState):
        info = evaluate_moves(state, self.color, self.time_budget,
                              self.max_iterations, self.rollout_steps,
                              self.rollout_policy)
        moves = info['moves']
        if not moves:
            return None
        # 在访问量达标的动作里选胜率最高的;都不达标则选访问量最多的(最可信)
        threshold = max(8, int(info['total'] * 0.05))
        for m in moves:
            if m['visits'] >= threshold:
                return m['action']
        return max(moves, key=lambda m: m['visits'])['action']


if __name__ == '__main__':
    # 性能基准:统计 1 秒内能完成的模拟次数
    gs = GameState(seed=7)
    t0 = time.time()
    info = evaluate_moves(gs, 'R', time_budget=1.0)
    dt = time.time() - t0
    print(f'基准: {dt:.2f}s 完成 {info["total"]} 次模拟, {len(info["moves"])} 个候选动作')
    for m in info['moves'][:5]:
        print(f'  {m["action"]} 胜率 {m["win_rate"]:.2%} ({m["visits"]}次)')
