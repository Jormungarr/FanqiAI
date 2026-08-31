import random
from typing import List, Optional, Tuple

# Piece types: J(将/帅), S(仕), X(相), R(车), N(马), C(炮), P(兵)
VALUE = {
    'J': 30,
    'S': 10,
    'X': 5,
    'R': 5,
    'N': 5,
    'C': 5,
    'P': 2,
}

TYPE_ORDER = ['J', 'S', 'X', 'R', 'N', 'C', 'P']

# 每方标准棋子数量(用于 from_setup 的暗棋随机补全)
PIECE_COUNT = {'J': 1, 'S': 2, 'X': 2, 'R': 2, 'N': 2, 'C': 2, 'P': 5}

# 棋子中文名(用于错误提示)
TYPE_CN = {'J': '将/帅', 'S': '仕/士', 'X': '相/象', 'R': '车', 'N': '马', 'C': '炮', 'P': '兵/卒'}


class Piece:
    def __init__(self, ptype: str, color: str):
        self.ptype = ptype
        self.color = color  # 'R' or 'B'
        self.revealed = False

    def value(self):
        return VALUE[self.ptype]

    def rank(self):
        return TYPE_ORDER.index(self.ptype)

    def __repr__(self):
        if not self.revealed:
            return '■'
        return f"{self.color}{self.ptype}"


class GameState:
    ROWS = 4
    COLS = 8

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.board: List[Optional[Piece]] = [None] * (self.ROWS * self.COLS)
        # 剩余分数制:双方初始 60 分,吃子扣对方、误伤扣自己,先降到 0 的一方输
        self.scores = {'R': 60, 'B': 60}
        self.captured_counts = {'R': 0, 'B': 0}
        self.moves_since_capture = 0
        self._place_initial()

    def _place_initial(self):
        pieces = []
        # Red
        pieces += [Piece('J', 'R')]
        pieces += [Piece('S', 'R') for _ in range(2)]
        pieces += [Piece('X', 'R') for _ in range(2)]
        pieces += [Piece('R', 'R') for _ in range(2)]
        pieces += [Piece('N', 'R') for _ in range(2)]
        pieces += [Piece('C', 'R') for _ in range(2)]
        pieces += [Piece('P', 'R') for _ in range(5)]
        # Black
        pieces += [Piece('J', 'B')]
        pieces += [Piece('S', 'B') for _ in range(2)]
        pieces += [Piece('X', 'B') for _ in range(2)]
        pieces += [Piece('R', 'B') for _ in range(2)]
        pieces += [Piece('N', 'B') for _ in range(2)]
        pieces += [Piece('C', 'B') for _ in range(2)]
        pieces += [Piece('P', 'B') for _ in range(5)]

        assert len(pieces) == 32
        self.rng.shuffle(pieces)
        for i, p in enumerate(pieces):
            self.board[i] = p

        # flip 4 random pieces
        hidden_indices = list(range(32))
        self.rng.shuffle(hidden_indices)
        for idx in hidden_indices[:4]:
            self.board[idx].revealed = True

    @classmethod
    def from_setup(cls, desc, scores=None, seed=None, removed=None):
        """从局面描述构造任意局面(供指导/残局练习)。

        desc: 长度 32 的列表,每格取值:
          '.' / None / ''  -> 空格
          'R:J'           -> 明棋
          'R:J?'          -> 暗棋(内容指定,上帝视角)
          'H'             -> 暗棋(内容未指定,从剩余标准棋子随机分配)
        scores: 剩余分数,默认双方 60。
        removed: 已移除(被吃)棋子列表,如 ['B:J', 'R:P']——这些棋子不会
          再被随机分配给未指定内容的暗棋(H),用于贴近真实对局的公开信息。
        """
        if len(desc) != 32:
            raise ValueError('board must have 32 cells')
        gs = cls.__new__(cls)
        gs.rng = random.Random(seed)
        gs.board = [None] * 32
        gs.scores = {'R': 60, 'B': 60} if scores is None else dict(scores)
        gs.captured_counts = {'R': 0, 'B': 0}
        gs.moves_since_capture = 0
        used = {'R': dict(PIECE_COUNT), 'B': dict(PIECE_COUNT)}
        if removed:
            for s in removed:
                if not (isinstance(s, str) and len(s) >= 3 and s[1] == ':'):
                    raise ValueError(f'bad removed piece: {s}')
                color, ptype = s[0], s[2]
                if color not in ('R', 'B') or ptype not in TYPE_ORDER:
                    raise ValueError(f'bad removed piece: {s}')
                if used[color][ptype] <= 0:
                    raise ValueError(
                        f'removed piece not on board: {s}: '
                        f'已吃登记超出标准配置(每方 {PIECE_COUNT[ptype]} 个 {ptype}),'
                        '或该棋子仍摆在棋盘上')
                used[color][ptype] -= 1
        hidden = []
        for i, s in enumerate(desc):
            if s is None or s == '' or s == '.':
                continue
            if s == 'H':
                hidden.append(i)
                continue
            if isinstance(s, str) and len(s) >= 3 and s[1] == ':':
                color, ptype = s[0], s[2]
                if color not in ('R', 'B') or ptype not in TYPE_ORDER:
                    raise ValueError(f'bad cell {i}: {s}')
                revealed = not s.endswith('?')
                if revealed:
                    # 配额校验只针对明棋:暗棋(未翻开)内容对所有人未知,
                    # 局面基于公开信息,不参与配额
                    if used[color][ptype] <= 0:
                        raise ValueError(
                            f'too many {color}{ptype} (cell {i}): '
                            f'{color} 的 {TYPE_CN[ptype]}标准最多 {PIECE_COUNT[ptype]} 个,'
                            '已全部翻开在棋盘上,请检查该格是否误录,或确认「已吃」登记未与棋盘冲突')
                    used[color][ptype] -= 1
                p = Piece(ptype, color)
                p.revealed = revealed
                gs.board[i] = p
            else:
                raise ValueError(f'bad cell {i}: {s}')
        # 未指定内容的暗棋:从标准配置的剩余棋子中随机分配
        remaining = []
        for color in ('R', 'B'):
            for t, n in used[color].items():
                remaining += [Piece(t, color) for _ in range(n)]
        gs.rng.shuffle(remaining)
        for idx in hidden:
            if remaining:
                gs.board[idx] = remaining.pop()
            else:
                # 棋子已超配(理论上被前面校验拦住),随机补一个保证有内容
                gs.board[idx] = Piece(gs.rng.choice(TYPE_ORDER), gs.rng.choice(('R', 'B')))
        return gs

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.ROWS and 0 <= c < self.COLS

    def idx(self, r: int, c: int) -> int:
        return r * self.COLS + c

    def rc(self, idx: int) -> Tuple[int, int]:
        return divmod(idx, self.COLS)

    def get_legal_actions(self, color: str) -> List[Tuple]:
        actions = []
        # flips
        for i, p in enumerate(self.board):
            if p is not None and not p.revealed:
                actions.append(('flip', i))

        # moves and captures
        for i, p in enumerate(self.board):
            if p is None or not p.revealed or p.color != color:
                continue
            r, c = self.rc(i)
            # 普通移动/吃子:炮除外(炮只能通过炮击行动)
            if p.ptype != 'C':
                for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
                    nr, nc = r + dr, c + dc
                    if not self.in_bounds(nr, nc):
                        continue
                    j = self.idx(nr, nc)
                    target = self.board[j]
                    # normal move into empty
                    if target is None:
                        actions.append(('move', i, j))
                    else:
                        # can capture only if target revealed and opponent
                        if target.revealed and target.color != color:
                            # 兵可吃将,将帅不能吃兵,其余仅允许吃同级或更低级(与 apply_action 一致)
                            can = (p.ptype == 'P' and target.ptype == 'J') or \
                                  (p.rank() <= target.rank() and not (p.ptype == 'J' and target.ptype == 'P'))
                            if can:
                                actions.append(('capture', i, j))
            # cannon special: straight lines, need exactly one intervening piece
            if p.ptype == 'C':
                # four directions
                for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
                    seen = 0
                    nr, nc = r + dr, c + dc
                    while self.in_bounds(nr, nc):
                        j = self.idx(nr, nc)
                        if self.board[j] is not None:
                            seen += 1
                            if seen == 2:
                                # candidate target: seen==2 means there IS a piece here, so cannot be empty
                                # cannon can blind-shot unrevealed or capture revealed opponent; cannot target revealed own piece
                                tgt = self.board[j]
                                if (not tgt.revealed) or (tgt.revealed and tgt.color != color):
                                    actions.append(('cannon', i, j))
                                break
                            # else continue
                        nr += dr; nc += dc
        return actions

    def apply_action(self, action: Tuple) -> Tuple[bool, str]:
        # returns (game_over, reason)
        act = action[0]
        if act == 'flip':
            _, pos = action
            p = self.board[pos]
            if p is None or p.revealed:
                return False, 'invalid flip'
            p.revealed = True
            self.moves_since_capture += 1
            return self._check_end(), 'flip'
        elif act == 'move':
            _, src, dst = action
            p = self.board[src]
            if p is None or not p.revealed:
                return False, 'invalid move'
            if p.ptype == 'C':
                return False, 'cannon cannot move directly'
            if self.board[dst] is not None:
                return False, 'target not empty'
            self.board[dst] = p
            self.board[src] = None
            self.moves_since_capture += 1
            return self._check_end(), 'move'
        elif act == 'capture':
            _, src, dst = action
            mover = self.board[src]
            tgt = self.board[dst]
            if mover is None or tgt is None or not mover.revealed or not tgt.revealed:
                return False, 'invalid capture'
            if mover.ptype == 'C':
                return False, 'cannon cannot capture directly'
            # 兵可吃将,但将帅不能吃兵
            if mover.ptype == 'P' and tgt.ptype == 'J':
                self._remove_piece(dst)
                self._move_piece(src, dst)
            elif mover.ptype == 'J' and tgt.ptype == 'P':
                return False, 'invalid capture by rank'
            elif mover.rank() < tgt.rank():
                # lower index means higher rank in our TYPE_ORDER
                self._remove_piece(dst)
                self._move_piece(src, dst)
            elif mover.rank() == tgt.rank():
                # 同级相吃:谁先吃谁存活,发起方吃掉对方并占据其位置
                self._remove_piece(dst)
                self._move_piece(src, dst)
            else:
                # move fails (cannot capture higher-ranked)
                return False, 'invalid capture by rank'

            # 扣分制:被吃方(对方)剩余分数减少
            self.scores[tgt.color] -= tgt.value()
            self.captured_counts[mover.color] += 1
            self.moves_since_capture = 0
            return self._check_end(), 'capture'
        elif act == 'cannon':
            _, src, dst = action
            mover = self.board[src]
            tgt = self.board[dst]
            if mover is None or mover.ptype != 'C':
                return False, 'invalid cannon'
            # ensure there is exactly one intervening piece (already enforced in move generation normally)
            # Cannon must flip target if unrevealed
            if tgt is None:
                return False, 'no target'
            # reveal first (blind shot must show the piece before removal)
            was_revealed = tgt.revealed
            if not tgt.revealed:
                tgt.revealed = True
            # 唯一禁忌:不能主动吃已翻开的己方明棋;盲狙己方暗棋允许(误伤)
            if was_revealed and tgt.color == mover.color:
                return False, 'cannot shoot revealed own piece'
            # remove target regardless of ownership (misfire allowed)
            if tgt.color != mover.color:
                # 打掉对方:对方剩余分数扣减
                self.scores[tgt.color] -= tgt.value()
                self.captured_counts[mover.color] += 1
            else:
                # 误伤己方暗棋:已翻开展示,移除棋子并从自己剩余分数中扣除该子分值
                self.scores[mover.color] -= tgt.value()
            # 先移除目标(盲狙时已先翻开展示),炮再移动到目标格
            self._remove_piece(dst)
            self._move_piece(src, dst)
            self.moves_since_capture = 0
            return self._check_end(), 'cannon'

        return False, 'unknown action'

    def _remove_piece(self, idx: int):
        self.board[idx] = None

    def _move_piece(self, src: int, dst: int):
        self.board[dst] = self.board[src]
        self.board[src] = None

    def clone(self):
        """深拷贝局面(供搜索/模拟使用,不复制随机源)"""
        ng = GameState.__new__(GameState)
        ng.rng = random.Random()
        ng.board = []
        for p in self.board:
            if p is None:
                ng.board.append(None)
            else:
                np = Piece(p.ptype, p.color)
                np.revealed = p.revealed
                ng.board.append(np)
        ng.scores = dict(self.scores)
        ng.captured_counts = dict(self.captured_counts)
        ng.moves_since_capture = self.moves_since_capture
        return ng

    def _check_end(self) -> bool:
        # 任一剩余分数降到 0 或以下,该方判负,立即结束
        for c in ('R', 'B'):
            if self.scores[c] <= 0:
                return True
        # check 30-move without capture -> draw
        if self.moves_since_capture >= 30:
            return True
        return False

    def winner(self) -> Optional[str]:
        # 输方剩余分数先到 0,对方获胜
        if self.scores['R'] <= 0:
            return 'B'
        if self.scores['B'] <= 0:
            return 'R'
        # draw
        if self.moves_since_capture >= 30:
            return 'DRAW'
        # no winner yet
        return None

    def pretty(self) -> str:
        lines = []
        for r in range(self.ROWS):
            row = self.board[r*self.COLS:(r+1)*self.COLS]
            lines.append(' '.join(str(x) if x is not None else '.' for x in row))
        return '\n'.join(lines)


if __name__ == '__main__':
    gs = GameState(seed=42)
    print(gs.pretty())
