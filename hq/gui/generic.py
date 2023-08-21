#!/usr/bin/env python3


"""
Basic GUI for segmenting images into regions

Original use case: Segment deck plan/points-to-plan into paint regions
"""


from enum import Enum
from typing import Optional, Callable, Tuple, List
import typer
from time import time
import contextlib

with contextlib.redirect_stdout(None):
    import pygame  # Avoid pygame's self advertisement on import

from abyss.bedrock.io.convenience import easy_load


START_RESOLUTION = (1280, 720)
BUTTON_WIDTH, BUTTON_HEIGHT = (200, 80)
VIEWPORT_EDGE_OFFSET = 20
VIEWPORT_BUTTON_OFFSET = BUTTON_HEIGHT + VIEWPORT_EDGE_OFFSET * 2
DEBOUNCE_TIME = 0.1
ZOOM_STEP = 0.1
VERTEX_RADIUS = 25
VERTEX_RESOLUTION = (VERTEX_RADIUS * 2,) * 2
VERTEX_CENTRE = (VERTEX_RADIUS,) * 2
VERTEX_COLOUR = pygame.Color(200, 20, 20, 255)


class MouseButton(Enum):
    """
    Mouse button indices, for indexing the result of pygame.mouse.get_pressed()
    """

    LEFT = 0
    RIGHT = 2
    MIDDLE = 1


def main(image_path: str) -> int:
    """
    Main GUI routine

    \b
    Returns:
        Exit status, 0 on success
    """
    SegmentRegions(image_path=image_path).main()


class SegmentRegions:
    """
    segment-regions application
    """

    def __init__(self, image_path: str) -> None:
        """
        Load the requested image and construct the application object

        Args:
            image_path: Path to image to
        """
        # Initialise display (window), make resizable
        self.screen = pygame.display.set_mode(START_RESOLUTION, flags=pygame.RESIZABLE)

        # Construct buttons
        self.buttons = [
            Button(
                colour=(255, 0, 0),
                callback=lambda: print("CALLBACK"),
                centre_x_offset=0,
                shortcut_key=pygame.K_c,
            )
        ]
        self.button_group = pygame.sprite.Group(*self.buttons)

        # Load image requested by user
        self.source_image = pygame.image.load(image_path)
        self.image_pos = pygame.Vector2(0, 0)
        self.last_mouse_pos = self.image_pos.copy()
        self.zoom = 1.0
        self.image = pygame.transform.smoothscale_by(self.source_image, self.zoom)

        # Do initial update to set button positions correctly
        self.button_group.update(
            screen_rect=self.screen.get_rect(),
            keys=pygame.key.get_pressed(),
            mouse_buttons=pygame.mouse.get_pressed(),
            mouse_pos=pygame.mouse.get_pos(),
        )

        # Undo logic: List of operations to produce points and polygons
        self.operations = []
        self.undo_operations = []
        self.vertex_group = pygame.sprite.Group()
        self.vertex_clicked = False

        # Draw initial UI
        self.draw()

    def main(self) -> None:
        """
        Main GUI loop
        """
        # Initialise all imported pygame modules
        pygame.init()

        pygame.event.clear()
        while True:
            # Wait for something to happen (keypress, mouse movement, etc), but redraw
            # periodically. This also avoids blocking ctrl-c interrupts
            event = pygame.event.wait(timeout=500)

            # Handle being closed by the OS (e.g. user clicks X button)
            if event.type == pygame.QUIT:
                break

            # Get mouse inputs
            scroll = event.y if event.type == pygame.MOUSEWHEEL else 0
            mouse_pos = pygame.mouse.get_pos()
            mouse_buttons = pygame.mouse.get_pressed()

            # Handle zooming and panning
            self.update_image(
                scroll=scroll,
                mouse_buttons=mouse_buttons,
                mouse_pos=mouse_pos,
            )

            # Update buttons' position from screen size, check if pressed
            self.button_group.update(
                screen_rect=self.screen.get_rect(),
                keys=pygame.key.get_pressed(),
                mouse_buttons=mouse_buttons,
                mouse_pos=mouse_pos,
            )

            # Draw UI
            self.draw()

        pygame.quit()

    def update_image(
        self,
        mouse_buttons: List[int],
        mouse_pos: pygame.Vector2,
        scroll: float,
    ) -> None:
        """
        Update image position and scale

        Args:
            mouse_buttons: Button state (pressed/unpressed) for each mouse button
            mouse_pos: Position of mouse on screen
            scroll: Movement of scroll wheel
        """
        # Draw annotations and points
        self.image = self.source_image.copy()

        # Reset sprites and redraw (for undo)
        # self.vertex_group = pygame.sprite.Group()
        # for operation in self.operations:
        #     operation()

        self.vertex_clicked = False
        self.vertex_group.update(
            mouse_buttons=mouse_buttons,
            mouse_pos=mouse_pos,
        )
        self.vertex_group.draw(surface=self.image)

        # Zoom
        if scroll != 0:
            zoom_step = 1 + ZOOM_STEP * (1 if scroll > 0 else -1)
            self.zoom *= zoom_step

            # TODO: Compute relevant crop of source_image and only upscale that (seg
            # fault from huge image otherwise)
            self.image = pygame.transform.smoothscale_by(self.image, self.zoom)

            # Update position to keep mouse cursor over the same part of the image
            self.image_pos = mouse_pos - zoom_step * (mouse_pos - self.image_pos)

        # Pan
        if mouse_buttons[MouseButton.RIGHT.value]:
            self.image_pos += pygame.Vector2(mouse_pos) - pygame.Vector2(
                self.last_mouse_pos
            )

        # Add points on click
        if self.vertex_clicked:
            print("vertclcik")
        elif not self.vertex_clicked and mouse_buttons[MouseButton.LEFT.value]:
            self.operations.append(
                lambda: self.vertex_group.add(
                    Vertex(
                        point=self.real_pixel_coords(mouse_pos),
                        clicked_callback=self._set_vertex_clicked,
                    )
                )
            )
            self.operations[-1]()

        self.last_mouse_pos = mouse_pos

    def draw(
        self,
    ) -> None:
        """
        Compute the position and size of the viewport

        Args:
            mouse_pos: Position of mouse on screen
            scroll: Movement of scroll wheel
        """
        # Compute viewport position and dimensions from screen size
        vpr = self.get_viewport_rect()

        # Draw white background
        pygame.draw.rect(self.screen, (255,) * 3, self.screen.get_rect())

        # Draw image into viewport
        viewport = pygame.Surface((vpr.width, vpr.height))
        viewport.blit(self.image, dest=self.image_pos)
        self.screen.blit(viewport, vpr)

        # Draw viewport border
        pygame.draw.rect(
            self.screen, color=(0,) * 3, rect=self.get_viewport_rect(), width=2
        )

        # Draw buttons
        self.button_group.draw(surface=self.screen)

        # Draw self.screen to X window
        pygame.display.flip()

    def get_viewport_rect(self) -> pygame.Rect:
        """
        Compute the position and size of the viewport

        Returns:
            Viewport position and shape/size, as rect
        """
        return pygame.Rect(
            VIEWPORT_EDGE_OFFSET,
            VIEWPORT_EDGE_OFFSET,
            self.screen.get_width() - 2 * VIEWPORT_EDGE_OFFSET,
            self.screen.get_height() - VIEWPORT_EDGE_OFFSET - VIEWPORT_BUTTON_OFFSET,
        )

    def _set_vertex_clicked(self) -> None:
        """
        Set the flag to signal a vertex wsa clicked

        This function is intended to be passed around as a callback
        """
        self.vertex_clicked = True

    def real_pixel_coords(self, mouse_pos: pygame.Vector2) -> pygame.Vector2:
        """
        Convert zoomed & panned mouse coords to image co-ordinates

        Args:
            mouse_pos: Position of cursor on window

        Returns:
            Position of cursor in image space
        """
        return (mouse_pos - self.image_pos + (VIEWPORT_EDGE_OFFSET,) * 2) / self.zoom


class Button(pygame.sprite.Sprite):
    """
    Generic button, with associated keyboard shortcut
    """

    def __init__(
        self,
        colour: Tuple[int, int, int],
        callback: Callable,
        centre_x_offset: float,
        shortcut_key: Optional[int] = None,
    ) -> None:
        """
        Construct the button

        Args:
            colour: Colour of button as RGB triplet
            callback: Callback function, run if button is pressed or associated
                keybinding is pressed
            centre_x_offset: Position of button in X axis (Y is fixed), as offset of
                centre of button from centre of screen. +ve => right, -ve => left
            shortcut_key: Index of shortcut key in pygame key state list. No keyboard
                shortcut for button if not given
        """
        super().__init__()
        self.image = pygame.Surface((BUTTON_WIDTH, BUTTON_HEIGHT))
        self.colour = colour
        self.highlight_colour = tuple(int(channel * 0.9) for channel in self.colour)
        self.callback = callback
        self.centre_x_offset = centre_x_offset
        self.shortcut_key = shortcut_key
        self.rect = pygame.Rect(0, 0, BUTTON_WIDTH, BUTTON_HEIGHT)
        self.last_press = 0  # Debounce timer

    def update(
        self,
        screen_rect: pygame.Rect,
        keys: List[int],
        mouse_buttons: List[int],
        mouse_pos: pygame.Vector2,
    ) -> None:
        """
        Update button state

        Args:
            screen_rect: Rectangle with width and height of screen (top and left unused)
            keys: Key state (pressed/unpressed) for each key on the keyboard
            mouse_buttons: Button state (pressed/unpressed) for each mouse button
            mouse_pos: Position of mouse on screen
        """
        # Update button position on screen
        self.rect.x = screen_rect.width / 2 + self.centre_x_offset - BUTTON_WIDTH / 2
        self.rect.y = screen_rect.height - VIEWPORT_EDGE_OFFSET - BUTTON_HEIGHT

        # Check if hovering over button
        hovering = self.rect.collidepoint(mouse_pos)

        # Draw button onto button surface
        pygame.draw.rect(
            self.image,
            self.highlight_colour if hovering else self.colour,
            self.image.get_rect(),
        )

        # Check for button pressed
        if self.activated(keys=keys, mouse_buttons=mouse_buttons, hovering=hovering):
            self.callback()

        super().update()

    def activated(
        self,
        keys: List[int],
        mouse_buttons: List[int],
        hovering: bool,
    ) -> True:
        """
        Check if the button has been clicked or its shortcut key pressed

        Args:
            keys: Key state (pressed/unpressed) for each key on the keyboard
            mouse_buttons: Button state (pressed/unpressed) for each mouse button
            hovering: True if mouse is hovering over button, False otherwise

        Returns:
            True if button has been activated
        """
        # Guard against debouncing
        if time() - self.last_press < DEBOUNCE_TIME:
            return False

        # Check actual input methods
        _activated = (hovering and mouse_buttons[MouseButton.LEFT.value]) or (
            self.shortcut_key is not None and keys[self.shortcut_key]
        )
        if _activated:
            self.last_press = time()
        return _activated


class Vertex(pygame.sprite.Sprite):
    """
    Vertices of polygons
    """

    def __init__(self, point: pygame.Vector2, clicked_callback: Callable) -> None:
        """
        Construct the vetrex

        Args:
            point: 2D vertex co-ordinates
            clicked_callback: Callback to register that vertex was clicked
        """
        super().__init__()
        self.rect = pygame.Rect(*point, *VERTEX_RESOLUTION)
        self.image = pygame.Surface(VERTEX_RESOLUTION)
        pygame.draw.circle(self.image, VERTEX_COLOUR, VERTEX_CENTRE, VERTEX_RADIUS)
        self.last_mouse_pos: Optional[pygame.Vector2] = None
        self.clicked_callback = clicked_callback

    def update(
        self,
        mouse_buttons: List[int],
        mouse_pos: pygame.Vector2,
    ) -> None:
        """
        Update vertex location (check for click and drag)

        Args:
            mouse_buttons: Button state (pressed/unpressed) for each mouse button
            mouse_pos: Position of mouse on screen
        """
        if mouse_buttons[MouseButton.LEFT.value] and self.rect.collidepoint(mouse_pos):
            # Register to game we were clicked
            self.clicked_callback()

            # When we first click, register mouse location
            if self.last_mouse_pos is None:
                self.last_mouse_pos = mouse_pos

            # On subsequent updates, mouve by relative mouse movement (avoids snapping to
            # mouse location)
            else:
                self.rect.move_ip(mouse_pos - self.last_mouse_pos)
        else:
            self.last_mouse_pos = None

        super().update()


if __name__ == "__main__":
    typer.run(main)
