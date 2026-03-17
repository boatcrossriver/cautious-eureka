import random
from dataclasses import dataclass
from typing import Optional

import pygame


WINDOW_WIDTH = 980
WINDOW_HEIGHT = 920
FPS = 60

GRID_SIZE = 8
MAX_LEVEL = 32
MISCLICKS_PER_LEVEL = 3

BOARD_SIZE = 760
CELL_GAP = 6
BOARD_LEFT = (WINDOW_WIDTH - BOARD_SIZE) // 2
BOARD_TOP = 120
CELL_SIZE = (BOARD_SIZE - (CELL_GAP * (GRID_SIZE - 1))) // GRID_SIZE

BG = (8, 13, 24)
PANEL = (15, 23, 42)
BOARD_BG = (30, 41, 59)
CELL_IDLE = (71, 85, 105)
CELL_SHOW = (99, 102, 241)
CELL_CORRECT = (34, 197, 94)
CELL_MISS = (239, 68, 68)
CELL_HOVER = (148, 163, 184)
TEXT = (226, 232, 240)
MUTED = (148, 163, 184)
ACCENT = (248, 250, 252)
ACCENT_TEXT = (15, 23, 42)
WARN = (251, 191, 36)

MISS_FLASH_MS = 220
LEVEL_TRANSITION_MS = 850
FAIL_TRANSITION_MS = 900


@dataclass
class GridCell:
    index: int
    rect: pygame.Rect


class VisualMemoryGame:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Visual Memory Game - 8x8")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()

        self.title_font = pygame.font.SysFont("Avenir Next", 46, bold=True)
        self.subtitle_font = pygame.font.SysFont("Avenir Next", 24)
        self.info_font = pygame.font.SysFont("Avenir Next", 30, bold=True)
        self.status_font = pygame.font.SysFont("Avenir Next", 23)
        self.button_font = pygame.font.SysFont("Avenir Next", 28, bold=True)

        self.cells = self._build_cells()
        self.button_rect = pygame.Rect(BOARD_LEFT, 36, 260, 58)
        self.running = True
        self.reset_session_state()

    def _build_cells(self) -> list[GridCell]:
        cells: list[GridCell] = []
        for idx in range(GRID_SIZE * GRID_SIZE):
            row, col = divmod(idx, GRID_SIZE)
            x = BOARD_LEFT + col * (CELL_SIZE + CELL_GAP)
            y = BOARD_TOP + row * (CELL_SIZE + CELL_GAP)
            cells.append(GridCell(index=idx, rect=pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)))
        return cells

    def reset_session_state(self) -> None:
        self.level = 0
        self.pattern: set[int] = set()
        self.correct_clicks: set[int] = set()
        self.misclicks_left = MISCLICKS_PER_LEVEL
        self.state = "ready"
        self.status_text = "Press Start to play."
        self.status_color = MUTED
        self.phase_ends_at = 0
        self.pending_state: Optional[str] = None
        self.miss_flash_until: dict[int, int] = {}

    def start_game(self) -> None:
        self.level = 1
        self._start_level(self.level)

    def _start_level(self, level: int) -> None:
        self.level = level
        self.pattern = set(random.sample(range(GRID_SIZE * GRID_SIZE), self.level))
        self.correct_clicks = set()
        self.misclicks_left = MISCLICKS_PER_LEVEL
        self.state = "show_pattern"
        self.status_text = f"Level {self.level}: memorize the highlighted tiles."
        self.status_color = TEXT
        self.phase_ends_at = pygame.time.get_ticks() + self._reveal_duration_ms(level)
        self.pending_state = None
        self.miss_flash_until = {}

    def _reveal_duration_ms(self, level: int) -> int:
        # Slightly more time as levels get harder, capped to keep pacing fluid.
        return min(1600 + (level * 50), 3200)

    def _cell_at(self, position: tuple[int, int]) -> Optional[int]:
        for cell in self.cells:
            if cell.rect.collidepoint(position):
                return cell.index
        return None

    def _schedule_transition(self, delay_ms: int, pending: str, message: str, color: tuple[int, int, int]) -> None:
        self.state = "transition"
        self.pending_state = pending
        self.phase_ends_at = pygame.time.get_ticks() + delay_ms
        self.status_text = message
        self.status_color = color

    def handle_click(self, position: tuple[int, int]) -> None:
        if self.button_rect.collidepoint(position) and self.state in {"ready", "game_over", "victory"}:
            self.start_game()
            return

        if self.state != "input":
            return

        index = self._cell_at(position)
        if index is None:
            return

        if index in self.pattern:
            if index not in self.correct_clicks:
                self.correct_clicks.add(index)
            if len(self.correct_clicks) == len(self.pattern):
                if self.level >= MAX_LEVEL:
                    self._schedule_transition(
                        LEVEL_TRANSITION_MS,
                        "victory",
                        "Perfect run. You cleared all 32 levels.",
                        CELL_CORRECT,
                    )
                else:
                    self._schedule_transition(
                        LEVEL_TRANSITION_MS,
                        "next_level",
                        f"Level {self.level} complete. Preparing level {self.level + 1}.",
                        CELL_CORRECT,
                    )
            return

        self.misclicks_left -= 1
        self.miss_flash_until[index] = pygame.time.get_ticks() + MISS_FLASH_MS
        if self.misclicks_left <= 0:
            self._schedule_transition(
                FAIL_TRANSITION_MS,
                "game_over",
                f"Out of attempts on level {self.level}.",
                CELL_MISS,
            )
        else:
            self.status_text = f"Wrong tile. Attempts left this level: {self.misclicks_left}."
            self.status_color = WARN

    def update(self) -> None:
        now = pygame.time.get_ticks()

        # Clean up expired miss flashes.
        self.miss_flash_until = {
            idx: expires for idx, expires in self.miss_flash_until.items() if expires > now
        }

        if self.state == "show_pattern" and now >= self.phase_ends_at:
            self.state = "input"
            self.status_text = (
                f"Level {self.level}: click the {len(self.pattern)} memorized tiles. "
                f"Misclicks left: {self.misclicks_left}."
            )
            self.status_color = TEXT

        elif self.state == "transition" and now >= self.phase_ends_at:
            if self.pending_state == "next_level":
                self._start_level(self.level + 1)
            elif self.pending_state == "victory":
                self.state = "victory"
                self.status_text = "Victory. Press Start to run again."
                self.status_color = CELL_CORRECT
            elif self.pending_state == "game_over":
                self.state = "game_over"
                self.status_text = "Game over. Press Start to try again."
                self.status_color = CELL_MISS

    def _draw_background(self) -> None:
        self.screen.fill(BG)
        pygame.draw.rect(
            self.screen,
            PANEL,
            pygame.Rect(34, 20, WINDOW_WIDTH - 68, WINDOW_HEIGHT - 40),
            border_radius=26,
        )
        pygame.draw.rect(
            self.screen,
            BOARD_BG,
            pygame.Rect(BOARD_LEFT - 14, BOARD_TOP - 14, BOARD_SIZE + 28, BOARD_SIZE + 28),
            border_radius=20,
        )

    def _draw_header(self) -> None:
        title = self.title_font.render("Visual Memory", True, TEXT)
        self.screen.blit(title, (BOARD_LEFT + 290, 30))

        subtitle = self.subtitle_font.render("8x8 pattern recall up to 32 tiles", True, MUTED)
        self.screen.blit(subtitle, (BOARD_LEFT + 292, 74))

        button_label = "Start Game" if self.state in {"ready", "game_over", "victory"} else "In Progress"
        button_color = ACCENT if self.state in {"ready", "game_over", "victory"} else (100, 116, 139)
        text_color = ACCENT_TEXT if self.state in {"ready", "game_over", "victory"} else TEXT
        pygame.draw.rect(self.screen, button_color, self.button_rect, border_radius=14)
        label = self.button_font.render(button_label, True, text_color)
        self.screen.blit(label, label.get_rect(center=self.button_rect.center))

        level_label = self.info_font.render(f"Level: {self.level}/{MAX_LEVEL}", True, TEXT)
        attempts_label = self.info_font.render(f"Misclicks: {self.misclicks_left}", True, WARN)
        self.screen.blit(level_label, (BOARD_LEFT + 4, BOARD_TOP + BOARD_SIZE + 22))
        self.screen.blit(attempts_label, (BOARD_LEFT + 355, BOARD_TOP + BOARD_SIZE + 22))

        status_surface = self.status_font.render(self.status_text, True, self.status_color)
        self.screen.blit(status_surface, (BOARD_LEFT + 4, BOARD_TOP + BOARD_SIZE + 64))

    def _cell_color(self, index: int, mouse_pos: tuple[int, int]) -> tuple[int, int, int]:
        if index in self.miss_flash_until:
            return CELL_MISS

        if self.state == "show_pattern":
            if index in self.pattern:
                return CELL_SHOW
            return CELL_IDLE

        if self.state == "victory":
            return CELL_CORRECT if index in self.pattern else CELL_IDLE

        if self.state == "game_over":
            if index in self.pattern:
                return CELL_SHOW
            return CELL_IDLE

        if index in self.correct_clicks:
            return CELL_CORRECT

        cell = self.cells[index]
        if self.state == "input" and cell.rect.collidepoint(mouse_pos):
            return CELL_HOVER

        return CELL_IDLE

    def _draw_grid(self) -> None:
        mouse_pos = pygame.mouse.get_pos()
        for cell in self.cells:
            color = self._cell_color(cell.index, mouse_pos)
            pygame.draw.rect(self.screen, color, cell.rect, border_radius=8)

    def draw(self) -> None:
        self._draw_background()
        self._draw_header()
        self._draw_grid()
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
    VisualMemoryGame().run()


if __name__ == "__main__":
    main()
