import pygame
import sys
# from mock_engine import GameState
from engine import Board

# --- CẤU HÌNH  ---
WIDTH = 768    
HEIGHT = 512
PANEL_WIDTH = WIDTH - HEIGHT 
MOVES_LOG_FONT = None 
DIMENSION = 8          
SQ_SIZE = HEIGHT // DIMENSION
MAX_FPS = 15
IMAGES = {}

# Class Button
class Button:
    def __init__(self, text, x, y, width, height, color=pygame.Color('white'), text_color=pygame.Color('black')):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.font = pygame.font.SysFont("Arial", 20, True)

    def draw(self, screen):
        # Vẽ hình chữ nhật
        pygame.draw.rect(screen, self.color, self.rect)
        pygame.draw.rect(screen, pygame.Color('black'), self.rect, 2) # Viền đen

        # Ghi chữ
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

# --- CLASS CHÍNH ---
class ChessMain:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Chess UI - Group Project Mockup")
        self.clock = pygame.time.Clock()
        # self.gs = GameState()
        self.gs = Board()
        self.MOVES_LOG_FONT = pygame.font.SysFont('Arial', 18, True, False)
        
        self.load_images()

        # Khởi tạo Buttons
        btn_width = 200
        btn_height = 50
        panel_x = HEIGHT 
        
        # Undo
        self.btn_undo = Button("UNDO MOVE", panel_x + 28, HEIGHT - 140, btn_width, btn_height, pygame.Color('darkorange'))
        
        # Reset
        self.btn_reset = Button("NEW GAME", panel_x + 28, HEIGHT - 70, btn_width, btn_height, pygame.Color('forestgreen'))
        
        # ... Các nút chọn khác

        # Trạng thái click chuột
        self.selected_square = () # (row, col) người dùng vừa click
        self.valid_moves = []     # Danh sách ô có thể đi từ ô đã chọn

    def load_images(self):
        pieces = ['wP', 'wR', 'wN', 'wB', 'wQ', 'wK', 'bP', 'bR', 'bN', 'bB', 'bQ', 'bK']
        for piece in pieces:
            try:
                original_image = pygame.image.load(f"images/{piece}.png")
                IMAGES[piece] = pygame.transform.scale(original_image, (SQ_SIZE, SQ_SIZE))
            except FileNotFoundError:
                print(f"Warning: Không tìm thấy file ảnh images/{piece}.png")

    # Vẽ bàn cờ
    def draw_board(self):
        colors = [pygame.Color("white"), pygame.Color("gray")]
        for r in range(DIMENSION):
            for c in range(DIMENSION):
                color = colors[((r + c) % 2)]
                pygame.draw.rect(self.screen, color, pygame.Rect(c*SQ_SIZE, r*SQ_SIZE, SQ_SIZE, SQ_SIZE))

    def highlight_squares(self):
        if self.selected_square != ():
            r, c = self.selected_square
            
            # Tô màu ô chọn
            s = pygame.Surface((SQ_SIZE, SQ_SIZE))
            s.set_alpha(100)
            s.fill(pygame.Color('blue'))
            self.screen.blit(s, (c * SQ_SIZE, r * SQ_SIZE))

            # Tô màu các ô đi được
            s.fill(pygame.Color('yellow'))
            for move in self.valid_moves:
                target_r, target_c = move.to_sq 
                self.screen.blit(s, (target_c * SQ_SIZE, target_r * SQ_SIZE))

    # Vẽ quân cờ
    def draw_pieces(self, board):
        for r in range(DIMENSION):
            for c in range(DIMENSION):
                piece = board[r][c]
                
                if piece != '.': 
                    if piece.isupper():
                        color = 'w'
                        type_ = piece
                    else:
                        color = 'b'
                        type_ = piece.upper()
                    
                    image_key = color + type_
                    
                    if image_key in IMAGES:
                         self.screen.blit(IMAGES[image_key], pygame.Rect(c*SQ_SIZE, r*SQ_SIZE, SQ_SIZE, SQ_SIZE))

    # Vẽ Side Panel
    def draw_side_panel(self, text_lines):
        panel_rect = pygame.Rect(HEIGHT, 0, PANEL_WIDTH, HEIGHT)
        pygame.draw.rect(self.screen, pygame.Color('lightslategrey'), panel_rect)
        
        if self.MOVES_LOG_FONT is None:
            self.MOVES_LOG_FONT = pygame.font.SysFont("Arial", 18, True, False)

        y_offset = 20
        for line in text_lines:
            text_object = self.MOVES_LOG_FONT.render(line, True, pygame.Color('white'))
            self.screen.blit(text_object, (HEIGHT + 20, y_offset))
            y_offset += 30
        
        # Buttons
        self.btn_undo.draw(self.screen)
        self.btn_reset.draw(self.screen)

    def draw_gamestate(self):
        self.draw_board()
        self.highlight_squares()
        self.draw_pieces(self.gs.board)
        
        status = "White to Move" if self.gs.turn == 'w' else "Black to Move"
        info = [
            "PROJECT: CHESS AI",
            "-----------------",
            f"Turn: {status}",
            "",
            "Game Mode:",
            "PvP (Default)" 
        ]
        self.draw_side_panel(info)

    """
    Popup chọn quân phong cấp
    Input: color ('w' hoặc 'b')
    Output: piece_code ('Q','R','B','N')
    """
    def show_promotion_popup(self, color):
        popup_width = 4 * SQ_SIZE 
        popup_height = SQ_SIZE    
        popup_x = (WIDTH - popup_width) // 2
        popup_y = (HEIGHT - popup_height) // 2
        
        choices = ['Q', 'R', 'B', 'N']
        choice_rects = [] 
        
        pygame.draw.rect(self.screen, pygame.Color('lightgray'), 
                            (popup_x - 5, popup_y - 5, popup_width + 10, popup_height + 10))
        pygame.draw.rect(self.screen, pygame.Color('black'), 
                            (popup_x - 5, popup_y - 5, popup_width + 10, popup_height + 10), 2)

        for i, piece_code in enumerate(choices):
            image_key = color + piece_code 
            
            x = popup_x + i * SQ_SIZE
            y = popup_y
            rect = pygame.Rect(x, y, SQ_SIZE, SQ_SIZE)
            choice_rects.append((rect, piece_code)) 
            
            pygame.draw.rect(self.screen, pygame.Color('white'), rect)
            pygame.draw.rect(self.screen, pygame.Color('black'), rect, 1)
            
            if image_key in IMAGES:
                self.screen.blit(IMAGES[image_key], rect)

        pygame.display.flip() 

        waiting = True
        selected_piece = 'Q' # Mặc định là Q nếu lỗi

        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                    
                if event.type == pygame.MOUSEBUTTONDOWN:
                    location = pygame.mouse.get_pos()
                    for rect, code in choice_rects:
                        if rect.collidepoint(location):
                            selected_piece = code
                            waiting = False 
                            
            self.clock.tick(MAX_FPS)
        
        return selected_piece

    # Vòng lặp chính
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    location = pygame.mouse.get_pos()
                    col = location[0] // SQ_SIZE
                    row = location[1] // SQ_SIZE

                    # Click side panel
                    if location[0] > HEIGHT:
                        if self.btn_reset.is_clicked(location):
                            print("Reset Game!")
                            self.gs = Board() 
                            self.valid_moves = []
                            self.selected_square = ()
                        elif self.btn_undo.is_clicked(location):
                            print("Undo Move!")
                            self.gs.undo_move()
                            self.valid_moves = []
                            self.selected_square = ()
                        continue

                    # --- Click bàn cờ ---
                    # Nếu click lại vào chính ô đang chọn -> Hủy chọn
                    if self.selected_square == (row, col):
                        self.selected_square = ()
                        self.valid_moves = []
                    else:
                        # Kiểm tra xem người dùng có click vào một ô đích hợp lệ không
                        clicked_move = None
                        for move in self.valid_moves:
                            if move.to_sq == (row, col):
                                clicked_move = move
                                break
                        
                        if clicked_move:
                            # Trường hợp thực hiện di chuyển 
                            # Nếu tìm thấy nhiều nước đi đến cùng 1 ô nghĩa là đang promotion: Q,R,B,N
                            potential_promotions = [m for m in self.valid_moves if m.to_sq == (row, col)]
                            
                            final_move = clicked_move # Mặc định

                            if len(potential_promotions) > 1:
                                print("Cần chọn quân phong cấp")
                                color = self.gs.turn 
                                choice = self.show_promotion_popup(color) 
                                
                                # Tìm nước đi khớp với lựa chọn của user
                                # engine.py: promo_piece = promo if color==WHITE else promo.lower()
                                target_promo = choice if color == 'w' else choice.lower()
                                
                                for p_move in potential_promotions:
                                    if p_move.promotion == target_promo:
                                        final_move = p_move
                                        break
                            
                            self.gs.apply_move(final_move)
                            print(f"Moved: {final_move}")
                            
                            self.selected_square = ()
                            self.valid_moves = []
                            
                        else:
                            # Trường hợp chọn quân mới
                            piece = self.gs.board[row][col]
                            if piece != '.':
                                self.selected_square = (row, col)
                                self.valid_moves = []
                                
                                all_valid_moves = self.gs.get_valid_moves()
                                
                                # append các nước đi hợp lệ từ ô đã chọn
                                for move in all_valid_moves:
                                    if move.from_sq == (row, col):
                                        self.valid_moves.append(move)

            self.draw_gamestate()
            pygame.display.flip()
            self.clock.tick(MAX_FPS)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = ChessMain()
    game.run()