import random

class RandomPlayer(object):
    def __init__(self, board):
        self.board = board

    def Start(self):
        all_moves = []

        # Duyệt toàn bộ bàn cờ
        for pieces in self.board.grid:
            for piece in pieces:
                if piece is not None and piece.color == self.board.player:
                    moves, captures = self.board.GetAllowedMoves(piece, True)
                    possibleMoves = captures + moves

                    # Lưu lại dạng (piece, position)
                    for move in possibleMoves:
                        all_moves.append((piece, move))

        # Nếu không có nước đi hợp lệ, trả về None
        if not all_moves:
            return None, None

        # Chọn ngẫu nhiên một nước đi
        piece, move = random.choice(all_moves)
        return piece, move
