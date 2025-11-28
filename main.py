import pygame
import sys
import random
from engine import Board

# --- CẤU HÌNH  ---
WIDTH = 768    
HEIGHT = 512
PANEL_WIDTH = WIDTH - HEIGHT 
MOVES_LOG_FONT = None 
TITLE_FONT = None
DIMENSION = 8          
SQ_SIZE = HEIGHT // DIMENSION
MAX_FPS = 15
IMAGES = {}

class Theme:
    # --- COLORS ---
    # Nền 
    BG_MAIN     = (48, 46, 43)       # Xám than chì (Nền Menu)
    BG_PANEL    = (38, 36, 33)       # Xám đậm (Side Panel)
    BG_CARD     = (60, 64, 72)       # Sáng hơn Side Panel
    
    # Bàn cờ 
    BOARD_LIGHT = (238, 238, 210)    # kem sáng
    BOARD_DARK  = (118, 150, 86)     # Xanh lá trầm
    
    # Text
    TEXT_MAIN   = (240, 240, 240)    # Trắng kem
    TEXT_SUB    = (200, 200, 200)    # Xám nhạt 
    TEXT_LOG    = (220, 220, 220)    # Xám
    
    # Buttons 
    BTN_MENU    = (80, 100, 120)     # Xanh xám 
    BTN_UNDO    = (218, 165, 32)     # Vàng cam 
    BTN_RESET   = (205, 92, 92)      # Đỏ nhạt 
    BTN_HOVER   = 30                 # Giá trị cộng thêm khi hover
    
    # Highlights
    H_SELECTED  = (186, 202, 68)     # Vàng chanh 
    H_LAST_MOVE = (246, 246, 105)    # Vàng sáng
    H_CHECK     = (235, 90, 70)      # Đỏ cam
    H_VALID_MOVE= (255, 255, 100)    # Vàng nhạt 

# Class Button
class Button:
    def __init__(self, text, x, y, width, height, color=pygame.Color('white'), hover_color = None, text_color=pygame.Color('black'), font = None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.base_color = color
        self.hover_color = hover_color if hover_color else self.lighten_color(color)
        self.text_color = text_color
        self.font = font if font else pygame.font.SysFont('Arial', 20)

    def lighten_color(self, color, amount=Theme.BTN_HOVER):
        return tuple(min(c + amount, 255) for c in color)

    def draw(self, screen):
        # Hover
        mouse_pos = pygame.mouse.get_pos()
        current_color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.base_color

        # Shadow
        shadow_rect = pygame.Rect(self.rect.x + 3, self.rect.y + 3, self.rect.width, self.rect.height)
        pygame.draw.rect(screen, (30, 30, 30), shadow_rect, border_radius=8)

        # Vẽ hình chữ nhật
        pygame.draw.rect(screen, current_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, (200, 200, 200), self.rect, 2, border_radius=8) # Viền đen

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
        self.gs = Board()
        self.game_state = "MENU" # MENU, PLAYING
        self.game_mode = "PvP"   # PvP, PvAI, AIvAI

        # Setup Fonts
        self.TITLE_FONT = pygame.font.SysFont('Comic Sans MS', 40, True, False)
        self.BUTTONS_FONT = pygame.font.SysFont('CopperPlate Gothic', 18, True, False)
        self.MOVES_LOG_FONT = pygame.font.SysFont("Consolas", 14, False, False)
        self.PANEL_FONT = pygame.font.SysFont("Arial", 18, True, False)
        self.TURN_FONT = pygame.font.SysFont("Arial", 24, True, False)
        
        # Load ảnh quân cờ
        self.load_images()

        # Khởi tạo Buttons
        btn_width = 200
        btn_height = 50
        panel_x = HEIGHT 

        # Undo
        self.btn_undo = Button("UNDO MOVE", panel_x + 28, HEIGHT - 140, btn_width, btn_height, Theme.BTN_UNDO, font = self.BUTTONS_FONT)
        
        # Reset
        self.btn_reset = Button("NEW GAME", panel_x + 28, HEIGHT - 70, btn_width, btn_height, Theme.BTN_RESET, font = self.BUTTONS_FONT)

        # Tạo các nút cho Menu
        self.btn_pvp = Button("Player vs Player", WIDTH//2 - 100, 150, 200, 50, Theme.BTN_MENU, text_color = Theme.TEXT_MAIN, font = self.BUTTONS_FONT)
        self.btn_minimax = Button("Player vs Minimax", WIDTH//2 - 100, 220, 200, 50, Theme.BTN_MENU, text_color = Theme.TEXT_MAIN, font = self.BUTTONS_FONT)
        self.btn_ai_ai = Button("AI vs AI (Demo)", WIDTH//2 - 100, 290, 200, 50, Theme.BTN_MENU, text_color = Theme.TEXT_MAIN, font = self.BUTTONS_FONT)
        
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

    def draw_menu(self):
        self.screen.fill(Theme.BG_MAIN)
        # Title
        title = self.TITLE_FONT.render("CHESS AI PROJECT", True, Theme.TEXT_MAIN)
        self.screen.blit(title, (WIDTH//2 - 200, 65))

        # Buttons
        self.btn_pvp.draw(self.screen)
        self.btn_minimax.draw(self.screen)
        self.btn_ai_ai.draw(self.screen)

    # Vẽ bàn cờ
    def draw_board(self):
        colors = [Theme.BOARD_LIGHT, Theme.BOARD_DARK]
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
            s.fill(Theme.H_SELECTED)
            self.screen.blit(s, (c * SQ_SIZE, r * SQ_SIZE))

            # Các ô đi được
            s.fill(Theme.H_VALID_MOVE)
            for move in self.valid_moves:
                target_r, target_c = move.to_sq 
                self.screen.blit(s, (target_c * SQ_SIZE, target_r * SQ_SIZE))

        # Highlight Last Move
        if len(self.gs.move_stack) > 0:
            last_move = self.gs.move_stack[-1][0] # Lấy Move object cuối cùng
            
            s = pygame.Surface((SQ_SIZE, SQ_SIZE))
            s.set_alpha(100)
            s.fill(Theme.H_LAST_MOVE) 
            
            # Highlight ô đi và ô đến
            start_r, start_c = last_move.from_sq
            end_r, end_c = last_move.to_sq
            self.screen.blit(s, (start_c*SQ_SIZE, start_r*SQ_SIZE))
            self.screen.blit(s, (end_c*SQ_SIZE, end_r*SQ_SIZE))

        # Highlight Check
        if self.gs.is_in_check(self.gs.turn):
            # Tìm vua của phe đang bị chiếu
            king_pos = self.gs.find_king(self.gs.turn)
            if king_pos:
                kr, kc = king_pos
                s = pygame.Surface((SQ_SIZE, SQ_SIZE))
                s.set_alpha(100)
                s.fill(Theme.H_CHECK) 
                self.screen.blit(s, (kc*SQ_SIZE, kr*SQ_SIZE))

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

    # Chuyển đổi Object Move thành chuỗi hiển thị
    def get_move_str(self, move_obj):
        return str(move_obj)
        # Option 2
        r1, c1 = move_obj.from_sq
        r2, c2 = move_obj.to_sq
        files = ['a','b','c','d','e','f','g','h']
        cols = ['8','7','6','5','4','3','2','1']
        start = files[c1] + cols[r1]
        end = files[c2] + cols[r2]
        return f"{start}-{end}"

    def draw_move_log(self):
        log_x = HEIGHT + 25
        log_y = 124
        line_height = 20
        
        title = self.MOVES_LOG_FONT.render("Move History:", True, Theme.TEXT_LOG)
        self.screen.blit(title, (log_x, log_y - 25))

        # move_stack chứa tuple (Move, prev_state). chỉ lấy Move.
        moves_list = [m[0] for m in self.gs.move_stack]

        # Chỉ hiện 20 nước cuối
        start_index = 0
        if len(moves_list) > 20:
            start_index = len(moves_list) - 20

        for i in range(start_index, len(moves_list), 2):
            move_num = i // 2 + 1
            text_num = f"{move_num}."
            
            # Nước Trắng
            white_move = moves_list[i]
            str_w = self.get_move_str(white_move)
            
            # Nước Đen
            str_b = ""
            if i + 1 < len(moves_list):
                black_move = moves_list[i+1]
                str_b = self.get_move_str(black_move)
            
            text = f"{text_num:<3} {str_w:<7} {str_b:<7}"
            text_object = self.MOVES_LOG_FONT.render(text, True, pygame.Color("white"))
            self.screen.blit(text_object, (log_x, log_y))
            log_y += line_height

    def draw_side_panel(self):
        # Nền panel
        panel_rect = pygame.Rect(HEIGHT, 0, PANEL_WIDTH, HEIGHT)
        pygame.draw.rect(self.screen, Theme.BG_PANEL, panel_rect) 
        
        # Card chứa Status
        status_card_rect = pygame.Rect(HEIGHT + 10, 20, PANEL_WIDTH - 20, 320)
        pygame.draw.rect(self.screen, Theme.BG_CARD, status_card_rect, border_radius=5)
        
        # Tiêu đề Card
        title_surf = self.PANEL_FONT.render("GAME STATUS", True, Theme.TEXT_SUB)
        self.screen.blit(title_surf, (HEIGHT + 23, 30))
        
        # Nội dung Status (Turn)
        status_text = "White's Turn" if self.gs.turn == 'w' else "Black's Turn"
        status_color = (255, 255, 255) if self.gs.turn == 'w' else (255, 100, 100)
        
        turn_surf = self.TURN_FONT.render(status_text, True, status_color)
        self.screen.blit(turn_surf, (HEIGHT + 23, 60))

        # Move Log
        self.draw_move_log()
        
        # Buttons
        self.btn_undo.draw(self.screen)
        self.btn_reset.draw(self.screen)

    def draw_gamestate(self):
        self.draw_board()
        self.highlight_squares()
        self.draw_pieces(self.gs.board)
        self.draw_side_panel()

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
    
    def execute_ai_move(self):
        # Tạm thời dùng Random Move để test UI. 
        valid_moves = self.gs.get_valid_moves()
        
        if not valid_moves:
            return 
        
        ai_move = None
        
        if self.game_mode == "PvAI":
            # Giả sử đây là chỗ của Minimax sau này. Tạm thời: Random
            print("AI (Minimax Placeholder) đang suy nghĩ...")
            pygame.time.delay(500) 
            ai_move = random.choice(valid_moves)
            
        elif self.game_mode == "AIvAI":
            pygame.time.delay(100) 
            ai_move = random.choice(valid_moves)
            
        if ai_move:
            self.gs.apply_move(ai_move)
            print(f"AI Moved: {ai_move}")
            # Reset trạng thái animation/highlight
            self.valid_moves = [] 
            self.selected_square = ()

    # Vòng lặp chính
    def run(self):
        running = True
        while running:
            # Kiểm tra xem có đến lượt AI không
            is_ai_turn = False
            if self.game_state == "PLAYING":
                if self.game_mode == "PvAI" and self.gs.turn == 'b':
                    is_ai_turn = True
                elif self.game_mode == "AIvAI":
                    is_ai_turn = True

            if is_ai_turn:
                self.draw_gamestate() # Vẽ lại bàn cờ trước khi AI đi để thấy nước đi của người chơi
                pygame.display.flip()
                
                pygame.time.delay(100)
                
                self.execute_ai_move() 
                

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if self.game_state == "MENU":
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        pos = pygame.mouse.get_pos()
                        if self.btn_pvp.is_clicked(pos):
                            self.game_mode = "PvP"
                            self.game_state = "PLAYING"
                            self.gs = Board() # Reset board
                        elif self.btn_minimax.is_clicked(pos):
                            self.game_mode = "PvAI"
                            self.game_state = "PLAYING"
                            self.gs = Board()
                        elif self.btn_ai_ai.is_clicked(pos):
                            self.game_mode = "AIvAI"
                            self.game_state = "PLAYING"
                            self.gs = Board()
            
                elif self.game_state == "PLAYING":
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        can_click = True
                        if self.game_mode == "PvAI" and self.gs.turn == 'b':
                            can_click = False # Không click khi AI đang nghĩ
                        if self.game_mode == "AIvAI":
                            can_click = False 

                        if can_click:
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
                                    self.game_state = "MENU"
                                elif self.btn_undo.is_clicked(location):
                                    print("Undo Move!")
                                    self.gs.undo_move()
                                    self.valid_moves = []
                                    self.selected_square = ()
                                continue

                            # Click bàn cờ
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
                        
                        location = pygame.mouse.get_pos()
                        if location[0] > HEIGHT:
                            if self.btn_reset.is_clicked(location):
                                self.game_state = "MENU" 

            if self.game_state == "MENU":
                self.draw_menu()
            elif self.game_state == "PLAYING":
                self.draw_gamestate()

            # --- CHECK GAME OVER ---
            game_over = False
            winner_text = ""
            
            if self.gs.is_checkmate(self.gs.turn):
                game_over = True
                winner = "Black" if self.gs.turn == 'w' else "White"
                winner_text = f"{winner} Wins by Checkmate!"
            elif self.gs.is_stalemate(self.gs.turn):
                game_over = True
                winner_text = "Draw by Stalemate!"
            
            if game_over:
                # Vẽ thông báo giữa màn hình
                font_big = pygame.font.SysFont("Arial", 32, True, False)
                text_surf = font_big.render(winner_text, True, pygame.Color('red'))
                text_rect = text_surf.get_rect(center=(WIDTH//2, HEIGHT//2))
                
                # Viền background
                bg_rect = text_rect.inflate(20, 20)
                pygame.draw.rect(self.screen, pygame.Color('black'), bg_rect)
                pygame.draw.rect(self.screen, pygame.Color('white'), bg_rect, 2)
                
                self.screen.blit(text_surf, text_rect)
                pygame.display.flip()
                
                # Chặn game lại, chờ click để reset hoặc thoát
                waiting_for_reset = True
                while waiting_for_reset:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            waiting_for_reset = False
                            running = False
                        if event.type == pygame.MOUSEBUTTONDOWN:
                            location = pygame.mouse.get_pos()
                            if self.btn_reset.is_clicked(location):
                                print("Resetting Game after Game Over")
                                self.gs = Board()
                                self.valid_moves = []
                                self.selected_square = ()
                                self.game_state = "MENU"
                                waiting_for_reset = False
                    self.clock.tick(MAX_FPS)

            pygame.display.flip()
            self.clock.tick(MAX_FPS)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = ChessMain()
    game.run()