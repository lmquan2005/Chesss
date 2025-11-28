# chess_engine_full.py
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
        self.from_sq = from_sq
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
        self.castling = {'w_k':True,'w_q':True,'b_k':True,'b_q':True}
        self.move_stack = []
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.init_board()

    def clone(self):
        return copy.deepcopy(self)

    def init_board(self):
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
                self.board[r][c] = setup[r][c]
        self.turn = WHITE
        self.castling = {'w_k':True,'w_q':True,'b_k':True,'b_q':True}
        self.move_stack = []
        self.halfmove_clock = 0
        self.fullmove_number = 1

    def print_board(self):
        print("  +-----------------+")
        for r in range(8):
            print(f"{8-r} | {' '.join(self.board[r])} |")
        print("  +-----------------+")
        print("    a b c d e f g h")
        print(f"Turn: {'White' if self.turn==WHITE else 'Black'}")
        print(f"Castling: {self.castling}")
        print(f"Fullmove: {self.fullmove_number}")

    def piece_color(self, p):
        if p == '.': return None
        return WHITE if p.isupper() else BLACK

    def find_king(self, color):
        k = 'K' if color==WHITE else 'k'
        for r in range(8):
            for c in range(8):
                if self.board[r][c] == k:
                    return (r,c)
        return None

    def is_square_attacked(self, sq, by_color):
        r0,c0 = sq
        # Pawns
        if by_color == WHITE:
            dirs = [(-1,-1),(-1,1)]
            pawn = 'P'
        else:
            dirs = [(1,-1),(1,1)]
            pawn = 'p'
        for dr,dc in dirs:
            r,c = r0+dr, c0+dc
            if in_bounds(r,c) and self.board[r][c]==pawn:
                return True
        # Knights
        knight = 'N' if by_color==WHITE else 'n'
        for dr,dc in DIRS_KNIGHT:
            r,c = r0+dr, c0+dc
            if in_bounds(r,c) and self.board[r][c]==knight:
                return True
        # Bishops/Queens
        for dr,dc in DIRS_BISHOP:
            r,c = r0+dr,c0+dc
            while in_bounds(r,c):
                ch = self.board[r][c]
                if ch != '.':
                    if self.piece_color(ch)==by_color and ch.lower() in ['b','q']:
                        return True
                    break
                r+=dr; c+=dc
        # Rooks/Queens
        for dr,dc in DIRS_ROOK:
            r,c = r0+dr,c0+dc
            while in_bounds(r,c):
                ch = self.board[r][c]
                if ch != '.':
                    if self.piece_color(ch)==by_color and ch.lower() in ['r','q']:
                        return True
                    break
                r+=dr;c+=dc
        # King
        king = 'K' if by_color==WHITE else 'k'
        for dr,dc in DIRS_KING:
            r,c = r0+dr, c0+dc
            if in_bounds(r,c) and self.board[r][c]==king:
                return True
        return False

    def generate_pseudo_legal_moves(self):
        moves = []
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p=='.': continue
                if self.piece_color(p)!=self.turn: continue
                moves.extend(self._piece_moves((r,c),p))
        return moves

    def _piece_moves(self,pos,p):
        r,c = pos
        color = self.piece_color(p)
        opp = BLACK if color==WHITE else WHITE
        moves = []
        pl = p.lower()
        if pl=='p':
            direction = -1 if color==WHITE else 1
            start_row = 6 if color==WHITE else 1
            # forward
            r1 = r+direction
            if in_bounds(r1,c) and self.board[r1][c]=='.':
                if r1==0 or r1==7:
                    for promo in ['Q','R','B','N']:
                        promo_piece = promo if color==WHITE else promo.lower()
                        moves.append(Move((r,c),(r1,c),p,promotion=promo_piece))
                else:
                    moves.append(Move((r,c),(r1,c),p))
                r2 = r+2*direction
                if r==start_row and in_bounds(r2,c) and self.board[r2][c]=='.':
                    moves.append(Move((r,c),(r2,c),p))
            # capture
            for dc in [-1,1]:
                rr,cc = r+direction, c+dc
                if in_bounds(rr,cc) and self.board[rr][cc]!='.' and self.piece_color(self.board[rr][cc])==opp:
                    if rr==0 or rr==7:
                        for promo in ['Q','R','B','N']:
                            promo_piece = promo if color==WHITE else promo.lower()
                            moves.append(Move((r,c),(rr,cc),p,captured=self.board[rr][cc],promotion=promo_piece))
                    else:
                        moves.append(Move((r,c),(rr,cc),p,captured=self.board[rr][cc]))
        elif pl=='n':
            for dr,dc in DIRS_KNIGHT:
                rr,cc = r+dr,c+dc
                if not in_bounds(rr,cc): continue
                target = self.board[rr][cc]
                if target=='.' or self.piece_color(target)==opp:
                    moves.append(Move((r,c),(rr,cc),p,captured=(target if target!='.' else None)))
        elif pl in ['b','r','q']:
            dirs = DIRS_BISHOP if pl=='b' else DIRS_ROOK if pl=='r' else DIRS_BISHOP+DIRS_ROOK
            for dr,dc in dirs:
                rr,cc = r+dr,c+dc
                while in_bounds(rr,cc):
                    target = self.board[rr][cc]
                    if target=='.':
                        moves.append(Move((r,c),(rr,cc),p))
                    else:
                        if self.piece_color(target)==opp:
                            moves.append(Move((r,c),(rr,cc),p,captured=target))
                        break
                    rr+=dr; cc+=dc
        elif pl=='k':
            for dr,dc in DIRS_KING:
                rr,cc = r+dr,c+dc
                if not in_bounds(rr,cc): continue
                target = self.board[rr][cc]
                if target=='.' or self.piece_color(target)==opp:
                    # simulate king move
                    orig_from, orig_to = self.board[r][c], self.board[rr][cc]
                    self.board[rr][cc]=p
                    self.board[r][c]='.'
                    if not self.is_square_attacked((rr,cc),opp):
                        moves.append(Move((r,c),(rr,cc),p,captured=(target if target!='.' else None)))
                    self.board[r][c]=orig_from
                    self.board[rr][cc]=orig_to
            # castling
            if color==WHITE:
                # King side
                if self.castling['w_k'] and self.board[7][5]=='.' and self.board[7][6]=='.' and self.board[7][7]=='R':
                    if not any(self.is_square_attacked(sq,BLACK) for sq in [(7,4),(7,5),(7,6)]):
                        moves.append(Move((7,4),(7,6),'K',is_castling=True))
                # Queen side
                if self.castling['w_q'] and self.board[7][1]=='.' and self.board[7][2]=='.' and self.board[7][3]=='.' and self.board[7][0]=='R':
                    if not any(self.is_square_attacked(sq,BLACK) for sq in [(7,4),(7,3),(7,2)]):
                        moves.append(Move((7,4),(7,2),'K',is_castling=True))
            else:
                if self.castling['b_k'] and self.board[0][5]=='.' and self.board[0][6]=='.' and self.board[0][7]=='r':
                    if not any(self.is_square_attacked(sq,WHITE) for sq in [(0,4),(0,5),(0,6)]):
                        moves.append(Move((0,4),(0,6),'k',is_castling=True))
                if self.castling['b_q'] and self.board[0][1]=='.' and self.board[0][2]=='.' and self.board[0][3]=='.' and self.board[0][0]=='r':
                    if not any(self.is_square_attacked(sq,WHITE) for sq in [(0,4),(0,3),(0,2)]):
                        moves.append(Move((0,4),(0,2),'k',is_castling=True))
        return moves

    def _make_move_on_board(self,m):
        r1,c1 = m.from_sq; r2,c2 = m.to_sq
        prev_from = self.board[r1][c1]
        prev_to = self.board[r2][c2]
        prev_castling = self.castling.copy()
        prev_half = self.halfmove_clock
        prev_full = self.fullmove_number

        # move
        self.board[r2][c2] = m.promotion if m.promotion else self.board[r1][c1]
        self.board[r1][c1]='.'

        # castling
        if m.is_castling:
            if m.piece=='K':
                if (r2,c2)==(7,6):
                    self.board[7][5]=self.board[7][7]; self.board[7][7]='.'
                else:
                    self.board[7][3]=self.board[7][0]; self.board[7][0]='.'
            else:
                if (r2,c2)==(0,6):
                    self.board[0][5]=self.board[0][7]; self.board[0][7]='.'
                else:
                    self.board[0][3]=self.board[0][0]; self.board[0][0]='.'

        # update castling rights
        if prev_from in ['K','k']:
            if prev_from=='K': self.castling['w_k']=self.castling['w_q']=False
            else: self.castling['b_k']=self.castling['b_q']=False
        if (r1,c1)==(7,0) or (r2,c2)==(7,0): self.castling['w_q']=False
        if (r1,c1)==(7,7) or (r2,c2)==(7,7): self.castling['w_k']=False
        if (r1,c1)==(0,0) or (r2,c2)==(0,0): self.castling['b_q']=False
        if (r1,c1)==(0,7) or (r2,c2)==(0,7): self.castling['b_k']=False

        # halfmove clock
        if prev_to!='.' or prev_from.lower()=='p': self.halfmove_clock=0
        else: self.halfmove_clock+=1

        # switch turn
        self.turn = BLACK if self.turn==WHITE else WHITE
        if self.turn==WHITE: self.fullmove_number+=1

        return (prev_from,prev_to,prev_castling,prev_half,prev_full)

    def _unmake_move_on_board(self,m,prev):
        r1,c1 = m.from_sq; r2,c2 = m.to_sq
        prev_from,prev_to,prev_castling,prev_half,prev_full=prev
        self.board[r1][c1]=prev_from
        self.board[r2][c2]=prev_to if prev_to!='.' else '.'

        # undo castling
        if m.is_castling:
            if m.piece=='K':
                if (r2,c2)==(7,6): self.board[7][7]=self.board[7][5]; self.board[7][5]='.'
                else: self.board[7][0]=self.board[7][3]; self.board[7][3]='.'
            else:
                if (r2,c2)==(0,6): self.board[0][7]=self.board[0][5]; self.board[0][5]='.'
                else: self.board[0][0]=self.board[0][3]; self.board[0][3]='.'

        self.castling=prev_castling
        self.halfmove_clock=prev_half
        self.fullmove_number=prev_full
        self.turn = BLACK if self.turn==WHITE else WHITE

    def get_valid_moves(self):
        pseudo = self.generate_pseudo_legal_moves()
        legal = []
        for m in pseudo:
            prev = self._make_move_on_board(m)
            king_pos = self.find_king(BLACK if self.turn==WHITE else WHITE)
            if king_pos and not self.is_square_attacked(king_pos, self.turn):
                legal.append(m)
            self._unmake_move_on_board(m,prev)
        return legal

    def apply_move(self,m):
        prev = self._make_move_on_board(m)
        self.move_stack.append((m,prev))

    def undo_move(self):
        if not self.move_stack: return
        m,prev = self.move_stack.pop()
        self._unmake_move_on_board(m,prev)

    def is_in_check(self,color):
        king = self.find_king(color)
        if king is None: return True
        return self.is_square_attacked(king, BLACK if color==WHITE else WHITE)

    def legal_moves_exist(self,color):
        saved = self.turn
        self.turn=color
        moves = self.get_valid_moves()
        self.turn=saved
        return len(moves)>0

    def is_checkmate(self,color):
        return self.is_in_check(color) and not self.legal_moves_exist(color)

    def is_stalemate(self,color):
        return not self.is_in_check(color) and not self.legal_moves_exist(color)


# Demo random play
if __name__=="__main__":
    import random, time
    b = Board()
    b.print_board()
    for i in range(200):
        moves = b.get_valid_moves()
        if not moves:
            if b.is_in_check(b.turn):
                print(f"Checkmate! Winner: {'Black' if b.turn==WHITE else 'White'}")
            else:
                print("Stalemate!")
            break
        m = random.choice(moves)
        print("Applying:",m)
        b.apply_move(m)
        b.print_board()
        time.sleep(0.05)
