from board.move import move
from pieces.nullpiece import nullpiece
from pieces.queen import queen
import random
import copy

class Minimax:
    def __init__(self):
        # lưu list moves tốt nhất tìm được ở root search
        self.tp = []
        self.root_depth = 3

    def evaluate(self, gametiles):
        """
        Trả về (y,x,n,m) cho AI sẽ di chuyển.
        Gọi minimax với độ sâu self.root_depth và lấy các nước tốt nhất lưu ở self.tp.
        """
        self.tp.clear()
        # chạy minimax — giá trị trả về không cần dùng trực tiếp ở đây
        _ = self.minimax(gametiles, self.root_depth, -10**12, 10**12, False)

        # nếu không có nước nào (ví dụ checkmate/stalemate), trả None
        if not self.tp:
            return None

        # tp chứa các move dạng [y,x,n,m,eval]
        # chọn các move có eval nhỏ nhất (vì player False = AI đang tìm min)
        min_eval = min(item[4] for item in self.tp)
        best = [item for item in self.tp if item[4] == min_eval]
        choice = random.choice(best)
        # trả 4 giá trị y,x,n,m
        return choice[0], choice[1], choice[2], choice[3]

    def reset(self, gametiles):
        for x in range(8):
            for y in range(8):
                piece = gametiles[x][y].pieceonTile
                if piece.tostring() in ('k', 'r', 'K', 'R'):
                    piece.moved = False

    def updateposition(self, x, y):
        """Chuyển (row, col) -> index đơn (0..63) theo logic của bạn"""
        return x * 8 + y

    def checkmate(self, gametiles):
        movex = move()
        # nếu bên trắng bị chiếu và không còn nước
        if movex.checkw(gametiles)[0] == 'checked':
            array = movex.movesifcheckedw(gametiles)
            if len(array) == 0:
                return True
        # nếu bên đen bị chiếu và không còn nước
        if movex.checkb(gametiles)[0] == 'checked':
            array = movex.movesifcheckedb(gametiles)
            if len(array) == 0:
                return True
        return False

    def stalemate(self, gametiles, player):
        movex = move()
        # player == False -> AI turn? giữ giống logic cũ
        if player == False:
            if movex.checkb(gametiles)[0] == 'notchecked':
                any_move = False
                for y in range(8):
                    for x in range(8):
                        piece = gametiles[y][x].pieceonTile
                        if piece.alliance == 'Black':
                            # lấy nước đi hợp lệ cho quân đen
                            moves1 = []
                            if hasattr(piece, "legalmoveb"):
                                moves1 = piece.legalmoveb(gametiles) or []
                            lx1 = movex.pinnedb(gametiles, moves1, y, x)
                            if len(lx1) > 0:
                                any_move = True
                                break
                    if any_move:
                        break
                return not any_move

        else:  # player == True
            if movex.checkw(gametiles)[0] == 'notchecked':
                any_move = False
                for y in range(8):
                    for x in range(8):
                        piece = gametiles[y][x].pieceonTile
                        if piece.alliance == 'White':
                            moves1 = []
                            if hasattr(piece, "legalmovew"):
                                moves1 = piece.legalmovew(gametiles) or []
                            lx1 = movex.pinnedw(gametiles, moves1, y, x)
                            if len(lx1) > 0:
                                any_move = True
                                break
                    if any_move:
                        break
                return not any_move

        return False

    def minimax(self, gametiles, depth, alpha, beta, player):
        # terminal
        if depth == 0 or self.checkmate(gametiles) or self.stalemate(gametiles, player):
            return self.calculateb(gametiles)

        movex = move()
        # nếu đang tìm nước cho "Black" (player == False) -- original dùng min
        if not player:
            minEval = 10**12
            kp, ks = self.eva(gametiles, player)
            # kp là list of lists: mỗi phần tử là danh sách các move dạng [y,x,n,m,eval]
            for lk in kp:
                for mv in lk:
                    mts = gametiles[mv[2]][mv[3]].pieceonTile
                    # apply move (mutate)
                    gametiles = self.move(gametiles, mv[0], mv[1], mv[2], mv[3])
                    evalk = self.minimax(gametiles, depth - 1, alpha, beta, True)
                    # nếu đang ở root depth ban đầu thì lưu các move gốc cùng eval
                    if depth == self.root_depth:
                        if evalk < minEval:
                            self.tp.clear()
                            self.tp.append([mv[0], mv[1], mv[2], mv[3], evalk])
                        elif evalk == minEval:
                            self.tp.append([mv[0], mv[1], mv[2], mv[3], evalk])
                    minEval = min(minEval, evalk)
                    beta = min(beta, evalk)
                    # revert
                    gametiles = self.revmove(gametiles, mv[2], mv[3], mv[0], mv[1], mts)
                    if beta <= alpha:
                        break
                if beta <= alpha:
                    break
            return minEval

        else:
            maxEval = -10**12
            kp, ks = self.eva(gametiles, player)
            for lk in ks:
                for mv in lk:
                    mts = gametiles[mv[2]][mv[3]].pieceonTile
                    gametiles = self.movew(gametiles, mv[0], mv[1], mv[2], mv[3])
                    evalk = self.minimax(gametiles, depth - 1, alpha, beta, False)
                    maxEval = max(maxEval, evalk)
                    alpha = max(alpha, evalk)
                    gametiles = self.revmove(gametiles, mv[2], mv[3], mv[0], mv[1], mts)
                    if beta <= alpha:
                        break
                if beta <= alpha:
                    break
            return maxEval

    def printboard(self, gametiles):
        for r in range(8):
            for c in range(8):
                print('|', end=gametiles[r][c].pieceonTile.tostring())
            print('|')

    def checkeva(self, gametiles, moves):
        arr = []
        for mv in moves:
            # calci expects moves list format [[n,m], ... ]
            lk = [[mv[2], mv[3]]]
            arr.append(self.calci(gametiles, mv[0], mv[1], lk))
        return arr

    def eva(self, gametiles, player):
        """
        Trả về (kp, ks) nơi:
        - kp: danh sách moves cho Black (k plus) (dạng [[ [y,x,n,m,eval], ... ], ...])
        - ks: danh sách moves cho White (similar)
        """
        kp = []
        ks = []
        movex = move()
        for y in range(8):
            for x in range(8):
                piece = gametiles[y][x].pieceonTile
                if piece is None:
                    continue
                # Black to move when player==False
                if piece.alliance == 'Black' and player == False:
                    if movex.checkb(gametiles)[0] == 'checked':
                        moves = movex.movesifcheckedb(gametiles)
                        kp = self.checkeva(gametiles, moves)
                        return kp, ks
                    moves = []
                    if hasattr(piece, "legalmoveb"):
                        moves = piece.legalmoveb(gametiles) or []
                    if len(moves) == 0:
                        continue
                    if piece.tostring() == 'K':
                        ax = movex.castlingb(gametiles)
                        if ax:
                            for l in ax:
                                if l == 'ks':
                                    moves.append([0, 6])
                                if l == 'qs':
                                    moves.append([0, 2])
                    pinned = movex.pinnedb(gametiles, moves, y, x)
                    if len(pinned) == 0:
                        continue
                    kp.append(self.calci(gametiles, y, x, pinned))

                # White to move when player==True
                if piece.alliance == 'White' and player == True:
                    if movex.checkw(gametiles)[0] == 'checked':
                        moves = movex.movesifcheckedw(gametiles)
                        ks = self.checkeva(gametiles, moves)
                        return kp, ks
                    moves = []
                    if hasattr(piece, "legalmovew"):
                        moves = piece.legalmovew(gametiles) or []
                    if len(moves) == 0:
                        continue
                    if piece.tostring() == 'k':
                        ax = movex.castlingw(gametiles)
                        if ax:
                            for l in ax:
                                if l == 'ks':
                                    moves.append([7, 6])
                                if l == 'qs':
                                    moves.append([7, 2])
                    pinned = movex.pinnedw(gametiles, moves, y, x)
                    if len(pinned) == 0:
                        continue
                    ks.append(self.calci(gametiles, y, x, pinned))

        return kp, ks

    def calci(self, gametiles, y, x, moves):
        arr = []
        for mv in moves:
            # move is [n,m]
            n, m = mv[0], mv[1]
            captured = gametiles[n][m].pieceonTile
            # apply
            gametiles[n][m].pieceonTile = gametiles[y][x].pieceonTile
            gametiles[y][x].pieceonTile = nullpiece()
            score = self.calculateb(gametiles)
            # revert
            gametiles[y][x].pieceonTile = gametiles[n][m].pieceonTile
            gametiles[n][m].pieceonTile = captured
            arr.append([y, x, n, m, score])
        return arr

    def calculateb(self, gametiles):
        piece_values = {
            'P': -100, 'N': -320, 'B': -330, 'R': -500,
            'Q': -900, 'K': -20000,
            'p': 100, 'n': 320, 'b': 330, 'r': 500,
            'q': 900, 'k': 20000
        }
        value = 0
        for y in range(8):
            for x in range(8):
                piece = gametiles[y][x].pieceonTile
                piece_str = piece.tostring()
                piece_value = piece_values.get(piece_str, 0)
                value += piece_value

                # King positional tweak: penalize corners for both sides (example)
                if piece_str == 'K':
                    # White king (big negative piece_value already added). Add positional penalty if near edge.
                    if x in [0, 1, 6, 7] or y in [0, 1, 6, 7]:
                        value -= 100
                    else:
                        value += 50
                if piece_str == 'k':
                    if x in [0, 1, 6, 7] or y in [0, 1, 6, 7]:
                        value += 100
                    else:
                        value -= 50

                # mobility: +10 per move for black pieces (since black positive in mapping), -10 per move for white
                if piece_str.lower() in ['q', 'r', 'b', 'n', 'p']:
                    moves = []
                    if piece.alliance == "Black" and hasattr(piece, "legalmoveb"):
                        moves = piece.legalmoveb(gametiles) or []
                    elif piece.alliance == "White" and hasattr(piece, "legalmovew"):
                        moves = piece.legalmovew(gametiles) or []
                    if moves:
                        if piece_str.islower():
                            value += len(moves) * 10
                        else:
                            value -= len(moves) * 10

                # pawn centralization bonus
                if piece_str == 'P' and x in [2, 3, 4, 5]:
                    value -= 10
                if piece_str == 'p' and x in [2, 3, 4, 5]:
                    value += 10

        return value

    def move(self, gametiles, y, x, n, m):
        promotion = False
        piece = gametiles[y][x].pieceonTile
        if piece.tostring() in ('K', 'R'):
            piece.moved = True

        # castling K side
        if piece.tostring() == 'K' and m == x + 2:
            gametiles[y][x+1].pieceonTile = gametiles[y][x+3].pieceonTile
            gametiles[y][x+1].pieceonTile.position = self.updateposition(y, x+1)
            gametiles[y][x+3].pieceonTile = nullpiece()
        # castling Q side
        if piece.tostring() == 'K' and m == x - 2:
            gametiles[y][x-1].pieceonTile = gametiles[y][0].pieceonTile
            gametiles[y][x-1].pieceonTile.position = self.updateposition(y, x-1)
            gametiles[y][0].pieceonTile = nullpiece()

        # pawn promotion (white P)
        if piece.tostring() == 'P' and y + 1 == n and y == 6:
            promotion = True

        if not promotion:
            gametiles[n][m].pieceonTile = piece
            gametiles[y][x].pieceonTile = nullpiece()
            gametiles[n][m].pieceonTile.position = self.updateposition(n, m)
        else:
            if piece.tostring() == 'P':
                gametiles[y][x].pieceonTile = nullpiece()
                gametiles[n][m].pieceonTile = queen('Black', self.updateposition(n, m))
                promotion = False

        return gametiles

    def revmove(self, gametiles, x, y, n, m, mts):
        """
        Hoàn tác nước đi: quân cờ hiện tại đang ở vị trí (x,y) và cần được đưa trở lại (n,m),
        đồng thời khôi phục quân cờ bị bắt (mts) về vị trí (x,y)?? (điều này phản ánh chữ ký hàm trước đây của bạn).
        Giữ nguyên thứ tự tham số như bạn đã sử dụng ở các chỗ khác: revmove(board, dst_x, dst_y, src_x, src_y, mts)
        """
        # handle white K
        cur = gametiles[x][y].pieceonTile
        if cur.tostring() == 'K':
            if m == y - 2:
                gametiles[x][y].pieceonTile.moved = False
                gametiles[n][m].pieceonTile = gametiles[x][y].pieceonTile
                gametiles[n][m].pieceonTile.position = self.updateposition(n, m)
                gametiles[n][7].pieceonTile = gametiles[x][y-1].pieceonTile
                gametiles[n][7].pieceonTile.position = self.updateposition(n, 7)
                gametiles[n][7].pieceonTile.moved = False
                gametiles[x][y].pieceonTile = nullpiece()
                gametiles[x][y-1].pieceonTile = nullpiece()
            elif m == y + 2:
                gametiles[x][y].pieceonTile.moved = False
                gametiles[n][m].pieceonTile = gametiles[x][y].pieceonTile
                gametiles[n][m].pieceonTile.position = self.updateposition(n, m)
                gametiles[n][0].pieceonTile = gametiles[x][y+1].pieceonTile
                gametiles[n][0].pieceonTile.position = self.updateposition(n, 0)
                gametiles[n][0].pieceonTile.moved = False
                gametiles[x][y].pieceonTile = nullpiece()
                gametiles[x][y-1].pieceonTile = nullpiece()
            else:
                gametiles[n][m].pieceonTile = gametiles[x][y].pieceonTile
                gametiles[n][m].pieceonTile.position = self.updateposition(n, m)
                gametiles[x][y].pieceonTile = mts
            return gametiles

        if cur.tostring() == 'k':
            if m == y - 2:
                gametiles[n][m].pieceonTile = gametiles[x][y].pieceonTile
                gametiles[n][m].pieceonTile.position = self.updateposition(n, m)
                gametiles[n][7].pieceonTile = gametiles[x][y-1].pieceonTile
                gametiles[n][7].pieceonTile.position = self.updateposition(n, 7)
                gametiles[x][y].pieceonTile = nullpiece()
                gametiles[x][y-1].pieceonTile = nullpiece()
            elif m == y + 2:
                gametiles[n][m].pieceonTile = gametiles[x][y].pieceonTile
                gametiles[n][m].pieceonTile.position = self.updateposition(n, m)
                gametiles[n][0].pieceonTile = gametiles[x][y+1].pieceonTile
                gametiles[n][0].pieceonTile.position = self.updateposition(n, 0)
                gametiles[x][y].pieceonTile = nullpiece()
                gametiles[x][y-1].pieceonTile = nullpiece()
            else:
                gametiles[n][m].pieceonTile = gametiles[x][y].pieceonTile
                gametiles[n][m].pieceonTile.position = self.updateposition(n, m)
                gametiles[x][y].pieceonTile = mts
            return gametiles

        # general revert
        gametiles[n][m].pieceonTile = gametiles[x][y].pieceonTile
        gametiles[n][m].pieceonTile.position = self.updateposition(n, m)
        gametiles[x][y].pieceonTile = mts
        return gametiles

    def movew(self, gametiles, y, x, n, m):
        promotion = False
        piece = gametiles[y][x].pieceonTile
        if piece.tostring() in ('k', 'r'):
            piece.moved = True

        if piece.tostring() == 'k' and m == x + 2:
            gametiles[y][x+1].pieceonTile = gametiles[y][x+3].pieceonTile
            gametiles[y][x+1].pieceonTile.position = self.updateposition(y, x+1)
            gametiles[y][x+3].pieceonTile = nullpiece()
        if piece.tostring() == 'k' and m == x - 2:
            gametiles[y][x-1].pieceonTile = gametiles[y][0].pieceonTile
            gametiles[y][x-1].pieceonTile.position = self.updateposition(y, x-1)
            gametiles[y][0].pieceonTile = nullpiece()

        # pawn promotion black->white pawn? keep original logic
        if piece.tostring() == 'p' and y - 1 == n and y == 1:
            promotion = True

        if not promotion:
            gametiles[n][m].pieceonTile = piece
            gametiles[y][x].pieceonTile = nullpiece()
            gametiles[n][m].pieceonTile.position = self.updateposition(n, m)
        else:
            if piece.tostring() == 'p':
                gametiles[y][x].pieceonTile = nullpiece()
                gametiles[n][m].pieceonTile = queen('White', self.updateposition(n, m))
                promotion = False

        return gametiles
