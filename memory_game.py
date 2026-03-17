import random
from dataclasses import dataclass

import pygame


WINDOW_WIDTH = 760
WINDOW_HEIGHT = 860
FPS = 60

GRID_SIZE = 3
TILE_SIZE = 180
TILE_GAP = 18
BOARD_TOP = 210
BOARD_LEFT = (WINDOW_WIDTH - ((TILE_SIZE * GRID_SIZE) + (TILE_GAP * (GRID_SIZE - 1)))) // 2

BACKGROUND = (9, 14, 27)
PANEL = (15, 23, 42)
TEXT = (226, 232, 240)
MUTED = (148, 163, 184)
ACCENT = (248, 250, 252)
ACCENT_TEXT = (15, 23, 42)
SUCCESS = (34, 197, 94)
FAIL = (239, 68, 68)

TILE_COLORS = [
    ((239, 68, 68), (254, 202, 202)),
    ((249, 115, 22), (253, 186, 116)),
    ((234, 179, 8), (253, 224, 71)),
    ((34, 197, 94), (187, 247, 208)),
    ((6, 182, 212), (165, 243, 252)),
    ((59, 130, 246), (191, 219, 254)),
    ((139, 92, 246), (221, 214, 254)),
    ((236, 72, 153), (251, 207, 232)),
    ((20, 184, 166), (153, 246, 228)),
]

SEQUENCE_DELAY_MS = 650
FLASH_DURATION_MS = 380
ROUND_DELAY_MS = 950
MESSAGE_DURATION_MS = 1100


@dataclass
class Tile:
    rect: pygame.Rect
    base_color: tuple[int, int, int]
    glow_color: tuple[int, int, int]


class MemoryGame:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Visual Memory Game")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()

        self.title_font = pygame.font.SysFont("Avenir Next", 44, bold=True)
        self.body_font = pygame.font.SysFont("Avenir Next", 24)
        self.small_font = pygame.font.SysFont("Avenir Next", 18)
        self.button_font = pygame.font.SysFont("Avenir Next", 26, bold=True)

        self.tiles = self._build_tiles()
        self.start_button = pygame.Rect(BOARD_LEFT, 110, 240, 60)

        self.sequence: list[int] = []
        self.input_index = 0
        self.level = 0
        self.best_score = 0
        self.active_tile: int | None = None
        self.flash_end_ms = 0
        self.next_step_ms = 0
        self.sequence_cursor = 0
        self.awaiting_next_round = False
        self.running = True

        self.state = "idle"
        self.status_text = "Press Start to begin."
        self.status_color = MUTED

    def _build_tiles(self) -> list[Tile]:
        tiles: list[Tile] = []
        for index, (base_color, glow_color) in enumerate(TILE_COLORS):
            row, col = divmod(index, GRID_SIZE)
            x = BOARD_LEFT + col * (TILE_SIZE + TILE_GAP)
            y = BOARD_TOP + row * (TILE_SIZE + TILE_GAP)
            tiles.append(Tile(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE), base_color, glow_color))
        return tiles

    def reset_game(self) -> None:
        self.sequence = []
        self.level = 0
        self.input_index = 0
        self.sequence_cursor = 0
        self.active_tile = None
        self.flash_end_ms = 0
        self.next_step_ms = 0
        self.awaiting_next_round = False
        self.state = "showing"
        self.status_text = "Memorize the pattern."
        self.status_color = TEXT
        self.advance_round()

    def advance_round(self) -> None:
        self.level += 1
        self.sequence.append(random.randrange(len(self.tiles)))
        self.input_index = 0
        self.sequence_cursor = 0
        self.active_tile = None
        self.awaiting_next_round = False
        self.state = "showing"
        self.status_text = f"Level {self.level}: watch carefully."
        self.status_color = TEXT
        self.next_step_ms = pygame.time.get_ticks() + 500

    def begin_input_phase(self) -> None:
        self.state = "input"
        self.input_index = 0
        self.active_tile = None
        self.flash_end_ms = 0
        self.status_text = "Your turn. Repeat the sequence."
        self.status_color = TEXT

    def trigger_tile_flash(self, index: int, duration_ms: int) -> None:
        self.active_tile = index
        self.flash_end_ms = pygame.time.get_ticks() + duration_ms

    def register_player_choice(self, index: int) -> None:
        if self.state != "input":
            return

        self.trigger_tile_flash(index, MESSAGE_DURATION_MS // 2)
        expected = self.sequence[self.input_index]
        if index != expected:
            self.best_score = max(self.best_score, self.level)
            self.state = "idle"
            self.status_text = f"Wrong tile. You reached level {self.level}. Press Start to try again."
            self.status_color = FAIL
            return

        self.input_index += 1
        if self.input_index == len(self.sequence):
            self.best_score = max(self.best_score, self.level)
            self.state = "transition"
            self.awaiting_next_round = True
            self.next_step_ms = pygame.time.get_ticks() + ROUND_DELAY_MS
            self.status_text = "Correct. Next round incoming."
            self.status_color = SUCCESS

    def handle_click(self, position: tuple[int, int]) -> None:
        if self.start_button.collidepoint(position) and self.state in {"idle", "transition"}:
            self.reset_game()
            return

        for index, tile in enumerate(self.tiles):
            if tile.rect.collidepoint(position):
                self.register_player_choice(index)
                return

    def update(self) -> None:
        now = pygame.time.get_ticks()

        if self.active_tile is not None and now >= self.flash_end_ms:
            self.active_tile = None

        if self.state == "showing" and now >= self.next_step_ms:
            if self.sequence_cursor >= len(self.sequence):
                self.begin_input_phase()
            else:
                tile_index = self.sequence[self.sequence_cursor]
                self.trigger_tile_flash(tile_index, FLASH_DURATION_MS)
                self.sequence_cursor += 1
                self.next_step_ms = now + SEQUENCE_DELAY_MS

        if self.state == "transition" and self.awaiting_next_round and now >= self.next_step_ms:
            self.advance_round()

    def draw_text(self, text: str, font: pygame.font.Font, color: tuple[int, int, int], x: int, y: int) -> None:
        surface = font.render(text, True, color)
        self.screen.blit(surface, (x, y))

    def draw(self) -> None:
        self.screen.fill(BACKGROUND)

        panel_rect = pygame.Rect(42, 42, WINDOW_WIDTH - 84, WINDOW_HEIGHT - 84)
        pygame.draw.rect(self.screen, PANEL, panel_rect, border_radius=28)

        self.draw_text("Visual Memory", self.title_font, TEXT, 72, 68)
        self.draw_text("Watch the pattern. Replay it from memory.", self.body_font, MUTED, 74, 126)

        button_color = ACCENT if self.state in {"idle", "transition"} else (71, 85, 105)
        button_text_color = ACCENT_TEXT if self.state in {"idle", "transition"} else TEXT
        pygame.draw.rect(self.screen, button_color, self.start_button, border_radius=18)

        label = "Start Game" if self.state == "idle" else "Restart"
        label_surface = self.button_font.render(label, True, button_text_color)
        label_rect = label_surface.get_rect(center=self.start_button.center)
        self.screen.blit(label_surface, label_rect)

        level_text = self.body_font.render(f"Level: {self.level}", True, TEXT)
        best_text = self.body_font.render(f"Best: {self.best_score}", True, TEXT)
        self.screen.blit(level_text, (WINDOW_WIDTH - 250, 118))
        self.screen.blit(best_text, (WINDOW_WIDTH - 250, 148))

        for index, tile in enumerate(self.tiles):
            color = tile.glow_color if self.active_tile == index else tile.base_color
            pygame.draw.rect(self.screen, color, tile.rect, border_radius=24)
            if self.active_tile == index:
                pygame.draw.rect(self.screen, ACCENT, tile.rect, width=5, border_radius=24)

        status_box = pygame.Rect(72, 790, WINDOW_WIDTH - 144, 36)
        pygame.draw.rect(self.screen, BACKGROUND, status_box, border_radius=12)
        status_surface = self.small_font.render(self.status_text, True, self.status_color)
        status_rect = status_surface.get_rect(center=status_box.center)
        self.screen.blit(status_surface, status_rect)

        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)

            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()


def main() -> None:
    MemoryGame().run()


if __name__ == "__main__":
    main()
