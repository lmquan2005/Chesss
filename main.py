import pygame
import time
from Minimax.chessAI import Minimax
from Minimax.Random import RandomPlayer
from setting import Config
from board import Board
import datetime


class Display:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(Config.resolution)
        pygame.display.set_caption("MiniMax")
        self.clock = pygame.time.Clock()
        self.gameOver = False
        self.width, self.height = Config.resolution

    def draw_board(self):
        self.screen.fill((0, 0, 0))
        spotSize = Config.spotSize
        boardSize = Config.boardSize * spotSize
        offset_x = (self.width - boardSize) // 2
        offset_y = (self.height - boardSize) // 2

        for x in range(Config.boardSize):
            for y in range(Config.boardSize):
                rect = pygame.Rect(offset_x + x*spotSize, offset_y + y*spotSize, spotSize, spotSize)
                color = (235, 235, 208) if (x+y)%2==0 else (119, 148, 85)
                pygame.draw.rect(self.screen, color, rect)

                piece = self.board.grid[x][y]
                if piece:
                    self.screen.blit(piece.sprite, (offset_x + x*spotSize, offset_y + y*spotSize))

        pygame.display.update()


    def AIvsRandom_display(self, num_games=1, delay=0.5):
        results = {"Minimax": 0, "Random": 0, "Draw": 0}

        with open("result.txt", "a", encoding="utf-8") as f:
            start_all = time.time()
            f.write("\n=============================\n")
            f.write(f"Chạy lúc: {datetime.datetime.now()}\n")
            f.write(f"Số ván: {num_games}\n")
            f.write("=============================\n")

            for game_num in range(1, num_games + 1):
                game_start_time = time.time()

                self.board = Board()
                self.gameOver = False

                minimax_agent = Minimax(Config.AI_DEPTH, self.board, True, True)
                random_agent = RandomPlayer(self.board)

                while not self.gameOver:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            return

                    if self.board.player == 0:
                        piece, move = random_agent.Start()
                    else:
                        piece, move = minimax_agent.Start(0)

                    if piece and move:
                        self.board.Move(piece, move)
                        if self.board.pieceToPromote:
                            self.board.PromotePawn(self.board.pieceToPromote, 0)

                    self.draw_board()
                    time.sleep(delay)

                    if self.board.winner is not None:
                        self.gameOver = True

                if self.board.winner == 0:
                    winner = "Random"
                elif self.board.winner == 1:
                    winner = "Minimax"
                else:
                    winner = "Draw"

                results[winner] += 1

                elapsed = time.time() - game_start_time

                print(f"Game {game_num}: Winner -> {winner} | Time: {elapsed:.2f}s", flush=True)

                f.write(f"Game {game_num}: Winner -> {winner} | Time: {elapsed:.2f}s\n")

            total_time = time.time() - start_all
            f.write("\n---- Kết quả ----\n")
            f.write(f"Minimax win: {results['Minimax']}\n")
            f.write(f"Random win: {results['Random']}\n")
            f.write(f"Draw: {results['Draw']}\n")
            f.write(f"Total Runtime: {total_time:.2f}s\n")
            f.write("=============================\n\n")

        print("\nKết quả sau", num_games, "ván:")
        print("Minimax:", results["Minimax"])
        print("Random:", results["Random"])
        print("Draw:", results["Draw"])
        print(f"Tổng thời gian chạy: {total_time:.2f}s")


if __name__ == "__main__":
    test = Display()
    test.AIvsRandom_display(num_games=1, delay=0.5)
