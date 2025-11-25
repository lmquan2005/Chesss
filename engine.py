# chess_engine.py
# Simple Chess Engine core (Python)
# - Board: 8x8, rows 0..7 (0 is rank 8), cols 0..7 (0 is file a)
# - Pieces: 'K','Q','R','B','N','P' for White, lowercase for Black
# - Methods: init_board, clone, get_valid_moves, apply_move, undo_move,
#            is_in_check, is_checkmate, is_stalemate, print_board
# - Limitations: no en-passantd, no 50-move rule, no threefold repetition
# - Castling supported with moved flags

import copy

WHITE = 'w'
BLACK = 'b'

DIRS_KNIGHT = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
DIRS_BISHOP = [(-1,-1),(-1,1),(1,-1),(1,1)]
DIRS_ROOK = [(-1,0),(1,0),(0,-1),(0,1)]
DIRS_KING = DIRS_BISHOP + DIRS_ROOK

def in_bounds(r,c):
    return 0 <= r < 8 and 0 <= c < 8

class Move:
    def __init__(self, from_sq, to_sq, piece, captured=None, promotion=None, is_castling=False):
        self.from_sq = from_sq  # (r,c)
        self.to_sq = to_sq
        self.piece = piece
        self.captured = captured
        self.promotion = promotion
        self.is_castling = is_castling

    def __repr__(self):
        fr = f"{chr(self.from_sq[1]+97)}{8-self.from_sq[0]}"
        to = f"{chr(self.to_sq[1]+97)}{8-self.to_sq[0]}"
        promo = f"={self.promotion}" if self.promotion else ""
        return f"{self.piece}{fr}->{to}{promo}"

class Board:
    def __init__(self):
        self.board = [['.' for _ in range(8)] for _ in range(8)]
        self.turn = WHITE
        # castling rights: wk/wq/bk/bq
        self.castling = {'w_k':True, 'w_q':True, 'b_k':True, 'b_q':True}
        self.move_stack = []  # stack of (Move, prev_state_info)
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.init_board()

    def clone(self):
        return copy.deepcopy(self)

    def init_board(self):
        # Standard initial position
        setup = [
            "rnbqkbnr",
            "pppppppp",
            "........",
            "........",
            "........",
            "........",
            "PPPPPPPP",
            "RNBQKBNR"
        ]
        for r in range(8):
            for c in range(8):
                ch = setup[r][c]
                self.board[r][c] = ch if ch != '.' else '.'
        self.turn = WHITE
        self.castling = {'w_k':True, 'w_q':True, 'b_k':True, 'b_q':True}
        self.move_stack = []
        self.halfmove_clock = 0
        self.fullmove_number = 1

    def print_board(self):
        print("  +-----------------+")
        for r in range(8):
            row = self.board[r]
            print(f"{8-r} | {' '.join(row)} |")
        print("  +-----------------+")
        print("    a b c d e f g h")
        print(f"Turn: {'White' if self.turn==WHITE else 'Black'}")
        print(f"Castling: {self.castling}")
        print(f"Fullmove: {self.fullmove_number}")

    def piece_color(self, p):
        if p == '.' : return None
        return WHITE if p.isupper() else BLACK

    def find_king(self, color):
        k = 'K' if color == WHITE else 'k'
        for r in range(8):
            for c in range(8):
                if self.board[r][c] == k:
                    return (r,c)
        return None

    def is_square_attacked(self, sq, by_color):
        # return True if square (r,c) is attacked by side by_color
        r0,c0 = sq
        # pawns
        if by_color == WHITE:
            pawn_dirs = [(-1,-1),(-1,1)]
            pawn = 'P'
        else:
            pawn_dirs = [(1,-1),(1,1)]
            pawn = 'p'
        for dr,dc in pawn_dirs:
            r,c = r0+dr, c0+dc
            if in_bounds(r,c) and self.board[r][c] == pawn:
                return True
        # knights
        knight = 'N' if by_color==WHITE else 'n'
        for dr,dc in DIRS_KNIGHT:
            r,c = r0+dr, c0+dc
            if in_bounds(r,c) and self.board[r][c] == knight:
                return True
        # bishops/queens (diagonals)
        for dr,dc in DIRS_BISHOP:
            r,c = r0+dr, c0+dc
            while in_bounds(r,c):
                ch = self.board[r][c]
                if ch != '.':
                    if self.piece_color(ch) == by_color and (ch.lower()=='b' or ch.lower()=='q'):
                        return True
                    break
                r += dr; c += dc
        # rooks/queens (lines)
        for dr,dc in DIRS_ROOK:
            r,c = r0+dr, c0+dc
            while in_bounds(r,c):
                ch = self.board[r][c]
                if ch != '.':
                    if self.piece_color(ch) == by_color and (ch.lower()=='r' or ch.lower()=='q'):
                        return True
                    break
                r += dr; c += dc
        # king adjacency
        king = 'K' if by_color==WHITE else 'k'
        for dr,dc in DIRS_KING:
            r,c = r0+dr, c0+dc
            if in_bounds(r,c) and self.board[r][c] == king:
                return True
        return False

    def generate_pseudo_legal_moves(self):
        moves = []
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p == '.': continue
                if self.piece_color(p) != self.turn: continue
                moves.extend(self._piece_moves((r,c), p))
        return moves

    def _piece_moves(self, pos, p):
        r,c = pos
        color = self.piece_color(p)
        opp = BLACK if color==WHITE else WHITE
        moves = []
        pl = p.lower()
        if pl == 'p':  # pawn
            direction = -1 if color==WHITE else 1
            start_row = 6 if color==WHITE else 1
            # single forward
            r1,c1 = r+direction, c
            if in_bounds(r1,c1) and self.board[r1][c1]=='.':
                # promotion?
                if r1==0 or r1==7:
                    for promo in ['Q','R','B','N']:
                        promo_piece = promo if color==WHITE else promo.lower()
                        moves.append(Move((r,c),(r1,c1),p, captured=None, promotion=promo_piece))
                else:
                    moves.append(Move((r,c),(r1,c1),p))
                # double
                r2 = r + 2*direction
                if r == start_row and in_bounds(r2,c) and self.board[r2][c]=='.':
                    moves.append(Move((r,c),(r2,c),p))
            # captures
            for dc in (-1,1):
                rr,cc = r+direction, c+dc
                if in_bounds(rr,cc) and self.board[rr][cc] != '.' and self.piece_color(self.board[rr][cc])==opp:
                    if rr==0 or rr==7:
                        for promo in ['Q','R','B','N']:
                            promo_piece = promo if color==WHITE else promo.lower()
                            moves.append(Move((r,c),(rr,cc),p, captured=self.board[rr][cc], promotion=promo_piece))
                    else:
                        moves.append(Move((r,c),(rr,cc),p, captured=self.board[rr][cc]))
            # Note: en-passant not implemented
        elif pl == 'n':
            for dr,dc in DIRS_KNIGHT:
                rr,cc = r+dr, c+dc
                if not in_bounds(rr,cc): continue
                if self.board[rr][cc]=='.' or self.piece_color(self.board[rr][cc])==opp:
                    moves.append(Move((r,c),(rr,cc),p, captured=(self.board[rr][cc] if self.board[rr][cc]!='.' else None)))
        elif pl == 'b' or pl == 'r' or pl == 'q':
            dirs = []
            if pl == 'b': dirs = DIRS_BISHOP
            elif pl == 'r': dirs = DIRS_ROOK
            else: dirs = DIRS_BISHOP + DIRS_ROOK
            for dr,dc in dirs:
                rr,cc = r+dr, c+dc
                while in_bounds(rr,cc):
                    if self.board[rr][cc] == '.':
                        moves.append(Move((r,c),(rr,cc),p))
                    else:
                        if self.piece_color(self.board[rr][cc])==opp:
                            moves.append(Move((r,c),(rr,cc),p, captured=self.board[rr][cc]))
                        break
                    rr += dr; cc += dc
        elif pl == 'k':
            for dr,dc in DIRS_KING:
                rr,cc = r+dr, c+dc
                if not in_bounds(rr,cc): continue
                if self.board[rr][cc]=='.' or self.piece_color(self.board[rr][cc])==opp:
                    moves.append(Move((r,c),(rr,cc),p, captured=(self.board[rr][cc] if self.board[rr][cc]!='.' else None)))
            # castling (basic checks: squares empty and not in check and rook/king not moved)
            if color==WHITE:
                if self.castling['w_k']:
                    # squares f1 (7,5) and g1 (7,6) must be empty and not attacked
                    if self.board[7][5]=='.' and self.board[7][6]=='.':
                        if not self.is_square_attacked((7,4),BLACK) and not self.is_square_attacked((7,5),BLACK) and not self.is_square_attacked((7,6),BLACK):
                            if self.board[7][7].lower()=='r':
                                moves.append(Move((r,c),(7,6),p, is_castling=True))
                if self.castling['w_q']:
                    if self.board[7][1]=='.' and self.board[7][2]=='.' and self.board[7][3]=='.':
                        if not self.is_square_attacked((7,4),BLACK) and not self.is_square_attacked((7,3),BLACK) and not self.is_square_attacked((7,2),BLACK):
                            if self.board[7][0].lower()=='r':
                                moves.append(Move((r,c),(7,2),p, is_castling=True))
            else:
                if self.castling['b_k']:
                    if self.board[0][5]=='.' and self.board[0][6]=='.':
                        if not self.is_square_attacked((0,4),WHITE) and not self.is_square_attacked((0,5),WHITE) and not self.is_square_attacked((0,6),WHITE):
                            if self.board[0][7].lower()=='r':
                                moves.append(Move((r,c),(0,6),p, is_castling=True))
                if self.castling['b_q']:
                    if self.board[0][1]=='.' and self.board[0][2]=='.' and self.board[0][3]=='.':
                        if not self.is_square_attacked((0,4),WHITE) and not self.is_square_attacked((0,3),WHITE) and not self.is_square_attacked((0,2),WHITE):
                            if self.board[0][0].lower()=='r':
                                moves.append(Move((r,c),(0,2),p, is_castling=True))
        return moves

    def get_valid_moves(self):
        # Generate pseudo-legal and remove those leaving own king in check
        moves = self.generate_pseudo_legal_moves()
        legal = []
        for m in moves:
            prev = self._make_move_on_board(m)
            king_pos = self.find_king(self.turn)
            # After making move, check if king is attacked
            if king_pos is None:
                # king captured? treat as illegal
                ok = False
            else:
                ok = not self.is_square_attacked(self.find_king(self.turn), BLACK if self.turn==WHITE else WHITE)
            self._unmake_move_on_board(m, prev)
            if ok:
                legal.append(m)
        return legal

    def _make_move_on_board(self, m):
        # Apply move on board only, return previous state info for undo
        r1,c1 = m.from_sq; r2,c2 = m.to_sq
        prev_piece_from = self.board[r1][c1]
        prev_piece_to = self.board[r2][c2]
        prev_castling = self.castling.copy()
        prev_halfmove = self.halfmove_clock
        prev_fullmove = self.fullmove_number

        # Move piece
        self.board[r2][c2] = m.promotion if m.promotion else self.board[r1][c1]
        self.board[r1][c1] = '.'

        # castling rook move
        if m.is_castling:
            # white king moved from e1 (7,4) to g1 (7,6) or c1 (7,2)
            if self.turn==WHITE:
                if (r2,c2) == (7,6):  # king side
                    self.board[7][5] = self.board[7][7]; self.board[7][7]='.'
                elif (r2,c2) == (7,2): # queen side
                    self.board[7][3] = self.board[7][0]; self.board[7][0]='.'
            else:
                if (r2,c2) == (0,6):
                    self.board[0][5] = self.board[0][7]; self.board[0][7]='.'
                elif (r2,c2) == (0,2):
                    self.board[0][3] = self.board[0][0]; self.board[0][0]='.'

        # update castling rights if king or rook moved/captured
        piece_moved = prev_piece_from
        if piece_moved == 'K':
            self.castling['w_k'] = False; self.castling['w_q'] = False
        if piece_moved == 'k':
            self.castling['b_k'] = False; self.castling['b_q'] = False
        # rook moved from initial squares
        if (r1,c1) == (7,0) or (r2,c2)==(7,0):
            if self.board[7][0].lower() != 'r': self.castling['w_q'] = False
        if (r1,c1) == (7,7) or (r2,c2)==(7,7):
            if self.board[7][7].lower() != 'r': self.castling['w_k'] = False
        if (r1,c1) == (0,0) or (r2,c2)==(0,0):
            if self.board[0][0].lower() != 'r': self.castling['b_q'] = False
        if (r1,c1) == (0,7) or (r2,c2)==(0,7):
            if self.board[0][7].lower() != 'r': self.castling['b_k'] = False

        # halfmove clock update
        if prev_piece_to != '.' or piece_moved.lower()=='p':
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        # turn switch & fullmove update
        self.turn = BLACK if self.turn==WHITE else WHITE
        if self.turn == WHITE:
            self.fullmove_number += 1

        return (prev_piece_from, prev_piece_to, prev_castling, prev_halfmove, prev_fullmove)

    def _unmake_move_on_board(self, m, prev):
        r1,c1 = m.from_sq; r2,c2 = m.to_sq
        prev_piece_from, prev_piece_to, prev_castling, prev_halfmove, prev_fullmove = prev
        # revert main move
        # If promotion occurred, we restore the pawn
        self.board[r1][c1] = prev_piece_from
        self.board[r2][c2] = prev_piece_to if prev_piece_to != '.' else '.'
        # revert castling rook move
        if m.is_castling:
            if prev_piece_from == 'K':
                # was white king
                if (r2,c2) == (7,6):  # king side
                    self.board[7][7] = self.board[7][5]; self.board[7][5] = '.'
                elif (r2,c2) == (7,2):
                    self.board[7][0] = self.board[7][3]; self.board[7][3] = '.'
            else:
                if (r2,c2) == (0,6):
                    self.board[0][7] = self.board[0][5]; self.board[0][5] = '.'
                elif (r2,c2) == (0,2):
                    self.board[0][0] = self.board[0][3]; self.board[0][3] = '.'

        # restore castling and clocks
        self.castling = prev_castling
        self.halfmove_clock = prev_halfmove
        self.fullmove_number = prev_fullmove
        # switch turn back
        self.turn = BLACK if self.turn==WHITE else WHITE

    def apply_move(self, m):
        # apply move and record for undo
        prev = self._make_move_on_board(m)
        self.move_stack.append((m, prev))

    def undo_move(self):
        if not self.move_stack:
            return
        m, prev = self.move_stack.pop()
        self._unmake_move_on_board(m, prev)

    def is_in_check(self, color):
        king = self.find_king(color)
        if king is None:  # no king -> treated as in check
            return True
        return self.is_square_attacked(king, BLACK if color==WHITE else WHITE)

    def legal_moves_exist(self, color):
        saved_turn = self.turn
        self.turn = color
        moves = self.get_valid_moves()
        self.turn = saved_turn
        return len(moves) > 0

    def is_checkmate(self, color):
        if not self.is_in_check(color): return False
        return not self.legal_moves_exist(color)

    def is_stalemate(self, color):
        if self.is_in_check(color): return False
        return not self.legal_moves_exist(color)

# Quick demo: random play until terminal or N moves
if __name__ == "__main__":
    import random, time
    b = Board()
    b.print_board()
    max_moves = 200
    for i in range(max_moves):
        moves = b.get_valid_moves()
        if not moves:
            if b.is_in_check(b.turn):
                print(f"Checkmate! Winner: {'Black' if b.turn==WHITE else 'White'}")
            else:
                print("Stalemate!")
            break
        m = random.choice(moves)
        print("Applying:", m)
        b.apply_move(m)
        b.print_board()
        time.sleep(0.1)
    else:
        print("Max moves reached.")
