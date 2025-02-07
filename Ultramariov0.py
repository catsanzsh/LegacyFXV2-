# Super Mario Bros. Clone in Python (Pygame)
import pygame
import random
import json
from array import array

# Initialize pygame and mixer for sound
pygame.mixer.pre_init(44100, -16, 1, 512)  # 44.1kHz, 16-bit, mono, small buffer for low latency
pygame.init()

# Screen setup
SCALE = 3  # scale factor for window (3x NES resolution)
TILE_SIZE = 16
SCREEN_WIDTH_TILES = 16  # 256 px width / 16 = 16 tiles
SCREEN_HEIGHT_TILES = 15  # 240 px height / 16 = 15 tiles
SCREEN_WIDTH = SCREEN_WIDTH_TILES * TILE_SIZE
SCREEN_HEIGHT = SCREEN_HEIGHT_TILES * TILE_SIZE
window = pygame.display.set_mode((SCREEN_WIDTH * SCALE, SCREEN_HEIGHT * SCALE))
pygame.display.set_caption("Super Mario Bros. Python Clone")

# Create a surface for the game world at NES resolution, to be scaled
game_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

# Load or initialize save data
save_file = "saves.json"
try:
    with open(save_file, "r") as f:
        saves = json.load(f)
except FileNotFoundError:
    # default: all slots start at world 1
    saves = {"1": 1, "2": 1, "3": 1}

# Define colors
COLOR_SKY = (107, 140, 255)   # light blue sky
COLOR_GROUND = (192, 160, 128)  # ground blocks (brownish)
COLOR_UNDERGROUND_BG = (0, 0, 0)   # black background for caves
COLOR_UNDERGROUND_GROUND = (100, 100, 100)  # gray blocks
COLOR_CASTLE_BG = (0, 0, 0)        # black background for castle
COLOR_CASTLE_GROUND = (160, 160, 160)  # light gray blocks
COLOR_COIN = (255, 216, 0)     # gold coins
COLOR_LAVA = (255, 64, 0)      # red-orange for lava
COLOR_PLAYER1 = (255, 0, 0)    # Mario (red)
COLOR_PLAYER2 = (0, 192, 0)    # Luigi (green)
COLOR_FLAG = (0, 224, 0)       # flagpole color (green)
COLOR_TEXT = (255, 255, 255)   # white text

# Prepare font for text (using a default font)
font = pygame.font.SysFont(None, 24)

# Sound generation functions
def generate_wave(frequency, duration, waveform="square"):
    """Generate a Sound object of a given waveform (square, triangle, noise)"""
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    amp = 32767 // 4  # lower volume to avoid clipping (1/4 max)
    buf = array('h')  # signed 16-bit output array

    if waveform == "square":
        # square wave: half period high, half low
        if frequency <= 0:
            # if frequency is 0 or None, treat as silence or noise placeholder
            frequency = 440
        period = int(sample_rate / frequency)
        if period <= 0:
            period = 1
        for i in range(n_samples):
            # high for first half of period, low for second half
            value = amp if (i % period) < (period // 2) else -amp
            buf.append(value)
    elif waveform == "triangle":
        if frequency <= 0:
            frequency = 440
        period = int(sample_rate / frequency)
        if period <= 0:
            period = 1
        half_period = period // 2
        for i in range(n_samples):
            # Triangle wave: ramp up in first half, ramp down in second half
            pos = i % period
            if pos < half_period:
                # ramp up from -amp to +amp
                value = -amp + int((pos / half_period) * 2 * amp)
            else:
                # ramp down from +amp to -amp
                pos2 = pos - half_period
                value = amp - int((pos2 / half_period) * 2 * amp)
            buf.append(int(value))
    elif waveform == "noise":
        # noise: random values each sample (white noise)
        for i in range(n_samples):
            buf.append(random.randint(-amp, amp))
    else:
        # default fallback: silence
        buf.extend([0] * n_samples)

    sound = pygame.mixer.Sound(buffer=buf)
    return sound

# Create game sounds
# Background music: simple loop of a few notes (square wave)
notes = [440, 554, 659, 880]  # A, C#, E, A (just a chord arpeggio as example)
music_wave = array('h')
for freq in notes:
    # append 0.125 sec of each note to form one sequence
    samples = generate_wave(freq, 0.125, "square")
    # pygame.mixer.Sound(buffer=buf) doesn't let us extract samples easily,
    # instead, generate_wave returns Sound. We can get raw samples via Sound.get_raw()
    raw = samples.get_raw()  # bytes
    # convert bytes to array of 16-bit
    arr = array('h', raw)
    music_wave.extend(arr)
# Make it loop by duplicating the sequence (to avoid gap in looping)
music_wave_all = music_wave * 4  # extend four times for a longer loop
background_music = pygame.mixer.Sound(buffer=music_wave_all)
background_music.set_volume(0.1)

# Sound effects
coin_sound = generate_wave(1320, 0.1, "square")
coin_sound.set_volume(0.3)
jump_sound = generate_wave(880, 0.2, "square")
jump_sound.set_volume(0.3)
stomp_sound = generate_wave(440, 0.1, "square")
stomp_sound.set_volume(0.3)
death_sound = generate_wave(0, 0.5, "noise")  # noise burst for death
death_sound.set_volume(0.4)

# Data structures for game state
current_slot = None
current_world = 1
current_level = 1

# Player attributes
players = [
    {"name": "MARIO", "color": COLOR_PLAYER1, "lives": 3},
    {"name": "LUIGI", "color": COLOR_PLAYER2, "lives": 3}
]
active_player_index = 0  # 0 for Mario, 1 for Luigi

# Player physics constants
PLAYER_SPEED = 3  # horizontal speed in pixels per frame
JUMP_VELOCITY = -9  # initial upward velocity for jump (negative because up is -y)
GRAVITY = 0.5       # gravity acceleration (pixels per frame^2)
MAX_FALL_SPEED = 10 # terminal velocity

# Define player and enemy objects
class Player:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.vx = 0
        self.vy = 0
        self.width = 16
        self.height = 16
        self.on_ground = False

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

class Goomba:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = -1  # start moving left by default
        self.vy = 0
        self.width = 16
        self.height = 16
        self.on_ground = False
        self.alive = True

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

# Helper to get tile at a given position
def get_tile(level_map, tx, ty):
    # returns the tile character at tile coordinates (tx, ty) or None if out of bounds
    if tx < 0 or tx >= len(level_map[0]) or ty < 0 or ty >= len(level_map):
        return None
    return level_map[ty][tx]

# Level generation function
def generate_level(world, level):
    """Generate a level map (list of strings) for the given world and level number."""
    # Determine theme based on level number
    if level == 2:   # underground levels
        theme_bg = COLOR_UNDERGROUND_BG
        theme_ground_color = COLOR_UNDERGROUND_GROUND
        underground = True
        castle = False
    elif level == 4:  # castle levels
        theme_bg = COLOR_CASTLE_BG
        theme_ground_color = COLOR_CASTLE_GROUND
        underground = False
        castle = True
    else:  # overworld (day or night) levels
        theme_bg = COLOR_SKY if level % 2 == 1 else COLOR_SKY  # (could vary for night levels)
        theme_ground_color = COLOR_GROUND
        underground = False
        castle = False

    # Base dimensions and structure
    # Increase level width with world number for difficulty
    base_width = 60 + world * 5
    width = base_width
    height = SCREEN_HEIGHT_TILES  # 15
    # Initialize level grid with empty spaces
    lvl = [[ '.' for _ in range(width) ] for _ in range(height) ]

    # Ground initialization
    ground_y = height - 1  # index of ground row (14)
    if castle:
        # start with ground as floor
        for x in range(width):
            lvl[ground_y][x] = 'X'
    else:
        # normal ground
        for x in range(width):
            lvl[ground_y][x] = 'X'

    # Ceiling for underground
    if underground:
        for x in range(width):
            lvl[0][x] = 'X'

    # Create pits (gaps in ground)
    pit_count = 2
    if not castle and not underground:
        # More pits in later worlds for overworld
        if world >= 5:
            pit_count = 3
    elif castle:
        # castle can have pits of lava
        pit_count = 2
    elif underground:
        pit_count = 1  # fewer pits underground
    pit_positions = []
    if pit_count > 0:
        # choose pit positions spread out in the level
        segment = width // (pit_count + 1)
        for i in range(1, pit_count+1):
            # starting x of pit somewhere in segment i
            start = segment * i - 3
            if start < 5: 
                start = 5
            pit_len = 2 + (world % 3)  # vary length a bit with world
            if pit_len > 5: pit_len = 5
            end = start + pit_len - 1
            if end >= width-2: 
                end = width-3
                start = end - pit_len + 1
            # Mark pit tiles: remove ground or replace with lava
            for x in range(start, end+1):
                if castle:
                    lvl[ground_y][x] = 'L'  # lava pool
                else:
                    lvl[ground_y][x] = '.'
            pit_positions.append((start, end))
    # Ensure first and last few tiles are ground (no pit at spawn or goal)
    for x in range(0, 3):
        lvl[ground_y][x] = 'X'
    for x in range(width-3, width):
        lvl[ground_y][x] = 'X'
        if castle:
            lvl[ground_y][x] = 'X'  # override any lava at end with ground for flag

    # Place flag at end of level
    lvl[ground_y-1][width-1] = 'F'  # flag just above last ground tile
    # Optionally, a flagpole: draw a pole 4 tiles tall (for visuals)
    pole_height = 4
    for h in range(pole_height):
        pole_y = ground_y - h
        # use 'F' for the entire pole for simplicity (drawn as pole in rendering)
        lvl[pole_y][width-1] = 'F'

    # Place a staircase near the flag (for overworld levels like the end stairs)
    if not underground and not castle:
        stair_height = 3 + (world // 3)  # taller stairs in later worlds
        base_x = width - 1 - stair_height - 1  # start a bit before flag
        for i in range(stair_height):
            # stack blocks increasing height towards flag
            lvl[ground_y - i - 1][base_x + i] = 'X'
            # ensure ground beneath staircase remains (already ground)
        # The top of staircase might be just below flag which is fine
    # Place some floating platforms or blocks for variety
    if not castle:
        if underground:
            # an elevated platform in underground
            plat_y = ground_y - 4
            plat_x0 = width // 3
            plat_length = 8
            for x in range(plat_x0, plat_x0 + plat_length):
                lvl[plat_y][x] = 'X'
        else:
            # an overhead block cluster in overworld
            cluster_y = ground_y - 5
            cluster_x0 = width // 2 - 2
            for x in range(cluster_x0, cluster_x0 + 5):
                lvl[cluster_y][x] = 'X'
            # put a coin above the middle block
            mid_x = cluster_x0 + 2
            lvl[cluster_y - 1][mid_x] = 'C'

    # Coins above pits (create coin arcs or lines over gaps)
    for (ps, pe) in pit_positions:
        # place a few coins spanning the pit
        coin_y = ground_y - 4  # 4 tiles above ground
        if coin_y < 0: coin_y = 0
        for cx in range(ps, pe+1):
            if cx >= 0 and cx < width:
                lvl[coin_y][cx] = 'C'

    # Place enemies (Goombas) on ground segments
    enemies = []
    # Determine potential enemy x positions based on fractions of level
    enemy_count = 2 + ((world - 1) // 3)  # increase enemies by world
    if enemy_count > 5: enemy_count = 5
    frac_positions = [i/(enemy_count+1) for i in range(1, enemy_count+1)]
    for frac in frac_positions:
        ex = int(frac * width)
        if ex < 1: ex = 1
        if ex > width-2: ex = width-2
        # adjust if in or right next to a pit
        in_pit = False
        for (ps, pe) in pit_positions:
            if ps <= ex <= pe:
                in_pit = True
                break
        if in_pit:
            continue  # skip placing enemy in a pit
        # also avoid placing on the flag or near end
        if ex >= width-3:
            continue
        # place goomba one tile above ground (so it stands on ground)
        if lvl[ground_y][ex] == 'X':
            lvl[ground_y-1][ex] = 'G'
            # create Goomba object later after level_map is returned
    # Level map is ready as list of strings
    level_map = ["".join(row) for row in lvl]
    return level_map, theme_bg, theme_ground_color

# Game state variables
level_map = []
theme_bg_color = COLOR_SKY
theme_ground_color = COLOR_GROUND
player = Player()
goombas = []
running = True
playing = False  # becomes True when in a level
game_over = False
win = False

# Start background music (loop indefinitely)
pygame.mixer.Channel(0).play(background_music, loops=-1)

clock = pygame.time.Clock()

# Main game loop
state = "menu"
while running:
    if state == "menu":
        # Draw menu
        game_surface.fill((0, 0, 0))
        title_text = font.render("SELECT FILE (1-3):", True, COLOR_TEXT)
        game_surface.blit(title_text, (40, 50))
        # Display each slot status
        for i in range(1, 4):
            w = saves.get(str(i), 1)
            status = f"World {w}-1" if w <= 8 else "Completed!"
            slot_text = font.render(f"{i}. {status}", True, COLOR_TEXT)
            game_surface.blit(slot_text, (60, 50 + 20 * i))
        # Blit menu to window
        scaled = pygame.transform.scale(game_surface, window.get_size())
        window.blit(scaled, (0, 0))
        pygame.display.flip()

        # Handle menu events
        menu_chosen = False
        while not menu_chosen:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    menu_chosen = True
                    break
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1 or event.key == pygame.K_KP1:
                        current_slot = 1
                        menu_chosen = True
                    elif event.key == pygame.K_2 or event.key == pygame.K_KP2:
                        current_slot = 2
                        menu_chosen = True
                    elif event.key == pygame.K_3 or event.key == pygame.K_KP3:
                        current_slot = 3
                        menu_chosen = True
            clock.tick(30)
        if not running:
            break
        # Setup game start based on selected slot
        current_world = saves.get(str(current_slot), 1)
        if current_world < 1 or current_world > 8:
            current_world = 1
        current_level = 1
        # Reset players lives
        players[0]["lives"] = 3
        players[1]["lives"] = 3
        active_player_index = 0  # Mario starts
        state = "game"
        playing = True
        game_over = False
        win = False
        # Generate first level
        level_map, theme_bg_color, theme_ground_color = generate_level(current_world, current_level)
        # Set player start position (at leftmost ground)
        player.x = 16
        player.y = (SCREEN_HEIGHT_TILES - 2) * TILE_SIZE  # one tile above bottom (ground_y-1)
        player.vx = 0
        player.vy = 0
        player.on_ground = False
        # Spawn enemies for this level
        goombas = []
        for iy, row in enumerate(level_map):
            for ix, ch in enumerate(row):
                if ch == 'G':
                    # Create goomba at this tile position
                    g = Goomba(ix * TILE_SIZE, iy * TILE_SIZE)
                    goombas.append(g)
                    # Remove the 'G' from the map representation (so it's treated as empty space for collisions)
                    level_map[iy] = level_map[iy][:ix] + '.' + level_map[iy][ix+1:]
    elif state == "game":
        # Game playing state
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_SPACE or event.key == pygame.K_UP:
                    # Jump if on ground
                    if player.on_ground:
                        player.vy = JUMP_VELOCITY
                        player.on_ground = False
                        jump_sound.play()
            # No explicit event for left/right; handled by keys pressed state below

        # Key state for continuous movement
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            player.vx = -PLAYER_SPEED
        elif keys[pygame.K_RIGHT]:
            player.vx = PLAYER_SPEED
        else:
            player.vx = 0

        # Apply gravity to player
        player.vy += GRAVITY
        if player.vy > MAX_FALL_SPEED:
            player.vy = MAX_FALL_SPEED

        # Horizontal movement and collision for player
        player.x += player.vx
        # Check horizontal collisions with tiles
        if player.vx != 0:
            # Determine direction
            direction = 1 if player.vx > 0 else -1
            # Check the tile(s) at player's front in that direction (top and bottom corners)
            front_x = int((player.x + (player.width if direction == 1 else 0)) // TILE_SIZE)
            # Check two vertical points: player's top and bottom (slightly adjusted to avoid missing corners)
            for check_y in [player.y + 1, player.y + player.height - 1]:
                tile_y = int(check_y // TILE_SIZE)
                tile = get_tile(level_map, front_x, tile_y)
                if tile == 'X':  # solid block
                    # Place player adjacent to the solid block and stop horizontal movement
                    if direction == 1:
                        player.x = front_x * TILE_SIZE - player.width
                    else:
                        player.x = (front_x + 1) * TILE_SIZE
                    player.vx = 0
                    break  # no need to check further once collision handled
        # Vertical movement and collision for player
        player.y += player.vy
        player.on_ground = False
        if player.vy >= 0:
            # falling downwards: check bottom side
            bottom_y = int((player.y + player.height) // TILE_SIZE)
            # Check bottom left and bottom right corners
            for check_x in [player.x + 2, player.x + player.width - 2]:
                tile_x = int(check_x // TILE_SIZE)
                tile = get_tile(level_map, tile_x, bottom_y)
                if tile == 'X' or tile == 'L':  # solid or lava counts as "ground" for stopping, but lava will kill
                    player.y = bottom_y * TILE_SIZE - player.height
                    player.vy = 0
                    if tile == 'X':
                        player.on_ground = True
                    # If lava, trigger death
                    if tile == 'L':
                        player.on_ground = True  # treat as on ground to avoid falling through
                        # kill player by simulating no lives (handled below)
                        players[active_player_index]["lives"] = 0
            # If out of level bottom (fell into a pit)
            if player.y > SCREEN_HEIGHT:
                players[active_player_index]["lives"] = 0  # player dies
        else:
            # moving upwards: check top side for head bump
            top_y = int(player.y // TILE_SIZE)
            for check_x in [player.x + 2, player.x + player.width - 2]:
                tile_x = int(check_x // TILE_SIZE)
                tile = get_tile(level_map, tile_x, top_y)
                if tile == 'X':
                    # hit head on block
                    player.y = (top_y + 1) * TILE_SIZE
                    player.vy = 0
                    # (Could add breaking brick or hitting question mark logic here)

        # Update enemies (Goombas)
        for goomba in goombas:
            if not goomba.alive:
                continue
            # Gravity
            goomba.vy += GRAVITY
            if goomba.vy > MAX_FALL_SPEED:
                goomba.vy = MAX_FALL_SPEED
            # Horizontal movement (goomba always moves with its vx)
            goomba.x += goomba.vx
            # Check horizontal collision for goomba (turn around on walls)
            front_x = int((goomba.x + (goomba.width if goomba.vx > 0 else 0)) // TILE_SIZE)
            # bottom center for checking floor
            foot_y = int((goomba.y + goomba.height - 1) // TILE_SIZE)
            hit_wall = False
            for check_y in [goomba.y + 2, goomba.y + goomba.height - 2]:
                tile_y = int(check_y // TILE_SIZE)
                tile = get_tile(level_map, front_x, tile_y)
                if tile == 'X':
                    hit_wall = True
                    break
            if hit_wall:
                # Reverse direction
                goomba.x = (front_x * TILE_SIZE - goomba.width) if goomba.vx > 0 else ((front_x + 1) * TILE_SIZE)
                goomba.vx *= -1

            # Vertical movement for goomba
            goomba.y += goomba.vy
            goomba.on_ground = False
            if goomba.vy >= 0:
                bottom_y = int((goomba.y + goomba.height) // TILE_SIZE)
                tile_bL = get_tile(level_map, int(goomba.x // TILE_SIZE), bottom_y)
                tile_bR = get_tile(level_map, int((goomba.x + goomba.width - 1) // TILE_SIZE), bottom_y)
                # If standing on ground
                if tile_bL == 'X' or tile_bR == 'X' or tile_bL == 'L' or tile_bR == 'L':
                    goomba.y = bottom_y * TILE_SIZE - goomba.height
                    goomba.vy = 0
                    goomba.on_ground = True
                    # If landed on lava, kill the goomba
                    if (tile_bL == 'L' or tile_bR == 'L'):
                        goomba.alive = False
                # If fell off bottom of screen
                if goomba.y > SCREEN_HEIGHT:
                    goomba.alive = False

        # Check collisions between player and enemies
        player_rect = player.rect()
        for goomba in goombas:
            if not goomba.alive:
                continue
            if player_rect.colliderect(goomba.rect()):
                # Determine if player is stomping (coming from above)
                if player.vy > 0 and player.y < goomba.y:
                    # Stomp enemy
                    goomba.alive = False
                    stomp_sound.play()
                    # bounce player up a bit
                    player.vy = -5
                    player.on_ground = False
                else:
                    # Player hit from side or below -> lose a life
                    players[active_player_index]["lives"] = 0  # set lives to 0 to trigger death
        # Check if player reached flag ('F' tile)
        px_idx = int((player.x + player.width/2) // TILE_SIZE)
        py_idx = int((player.y + player.height/2) // TILE_SIZE)
        tile = get_tile(level_map, px_idx, py_idx)
        if tile == 'F':
            # Level complete
            # Advance to next level or world
            coin_sound.play()  # use coin sound as a placeholder for level clear sound
            active_player = players[active_player_index]
            # The active player continues to next level, but as per alternating mode, we switch player at level completion
            # Switch to other player for next level (if they have lives left)
            next_player_index = 1 - active_player_index
            if players[next_player_index]["lives"] <= 0:
                # If other player is out of lives, current player stays (no switch)
                next_player_index = active_player_index
            # Update world/level
            if current_level == 4:
                # finished a world
                current_world += 1
                current_level = 1
                # Save progress (if not beyond world 8)
                if current_world <= 8:
                    saves[str(current_slot)] = current_world
                    with open(save_file, "w") as f:
                        json.dump(saves, f)
            else:
                current_level += 1
            # Check win condition
            if current_world > 8:
                # Game completed
                win = True
                playing = False
            else:
                # Load next level
                level_map, theme_bg_color, theme_ground_color = generate_level(current_world, current_level)
                # Respawn player at start
                player.x = 16
                player.y = (SCREEN_HEIGHT_TILES - 2) * TILE_SIZE
                player.vx = 0
                player.vy = 0
                player.on_ground = False
                # Spawn new enemies
                goombas = []
                for iy, row in enumerate(level_map):
                    for ix, ch in enumerate(row):
                        if ch == 'G':
                            g = Goomba(ix * TILE_SIZE, iy * TILE_SIZE)
                            goombas.append(g)
                            level_map[iy] = level_map[iy][:ix] + '.' + level_map[iy][ix+1:]
                # Switch player turn
                active_player_index = next_player_index
            # Skip the rest of this frame to avoid processing death simultaneously
            if not playing:
                state = "game_over"  # triggers win message
            continue

        # Check for player death (lives <= 0)
        if players[active_player_index]["lives"] <= 0:
            # Play death sound
            death_sound.play()
            # Switch to next player if available
            next_player_index = 1 - active_player_index
            # Mark if game over (both players dead)
            if players[next_player_index]["lives"] <= 0:
                # Both players have 0 lives
                game_over = True
                playing = False
            else:
                # Other player will continue on same level
                active_player_index = next_player_index
                # Reset current player (who died) lives maybe to 3 if you want continue feature? 
                # In original, once lives are 0 you game over for that player. We'll leave them at 0 (no continue for that player).
                # Reset position for new player
                player.x = 16
                player.y = (SCREEN_HEIGHT_TILES - 2) * TILE_SIZE
                player.vx = 0
                player.vy = 0
                player.on_ground = False
                # Also reset enemies to initial for retry
                level_map, theme_bg_color, theme_ground_color = generate_level(current_world, current_level)
                goombas = []
                for iy, row in enumerate(level_map):
                    for ix, ch in enumerate(row):
                        if ch == 'G':
                            g = Goomba(ix * TILE_SIZE, iy * TILE_SIZE)
                            goombas.append(g)
                            level_map[iy] = level_map[iy][:ix] + '.' + level_map[iy][ix+1:]
            if not playing:
                state = "game_over"
                # Ensure to break out of game loop to show game over
                continue

        # Drawing the game frame
        # Fill background
        game_surface.fill(theme_bg_color)
        # Draw tiles
        cam_x = int(player.x) - (SCREEN_WIDTH // 2)  # simple camera: center on player
        # Clamp camera within level bounds
        if cam_x < 0:
            cam_x = 0
        max_cam_x = len(level_map[0]) * TILE_SIZE - SCREEN_WIDTH
        if cam_x > max_cam_x:
            cam_x = max_cam_x
        # Determine visible tile range
        first_tile = cam_x // TILE_SIZE
        last_tile = (cam_x + SCREEN_WIDTH) // TILE_SIZE + 1
        if last_tile > len(level_map[0]):
            last_tile = len(level_map[0])
        for ty, row in enumerate(level_map):
            for tx in range(first_tile, last_tile):
                tile = row[tx]
                if tile == '.':
                    continue
                px = tx * TILE_SIZE - cam_x
                py = ty * TILE_SIZE
                if tile == 'X':
                    # draw solid block
                    pygame.draw.rect(game_surface, theme_ground_color, (px, py, TILE_SIZE, TILE_SIZE))
                elif tile == 'C':
                    # draw coin as a small circle
                    pygame.draw.circle(game_surface, COLOR_COIN, (px + TILE_SIZE//2, py + TILE_SIZE//2), TILE_SIZE//2 - 2)
                elif tile == 'L':
                    # draw lava tile as filled rect
                    pygame.draw.rect(game_surface, COLOR_LAVA, (px, py, TILE_SIZE, TILE_SIZE))
                elif tile == 'F':
                    # draw flagpole (if bottom of pole)
                    # We'll draw the pole and flag: for simplicity, draw a green rectangle (pole) and a small flag
                    # Determine if this is the bottom of pole
                    # If the tile below is also 'F', this is part of the pole, draw pole here
                    pygame.draw.rect(game_surface, COLOR_FLAG, (px + TILE_SIZE//2 - 2, py, 4, TILE_SIZE))
                    # If this is the top of the pole (tile above is empty or out of bounds), draw a flag triangle
                    above_tile = get_tile(level_map, tx, ty-1)
                    if above_tile != 'F':
                        # draw a simple triangle flag
                        pygame.draw.polygon(game_surface, (255, 0, 0), [(px + TILE_SIZE//2, py), (px + TILE_SIZE//2, py + 6), (px + TILE_SIZE//2 + 8, py + 3)])
        # Draw enemies
        for goomba in goombas:
            if not goomba.alive:
                continue
            gx = int(goomba.x) - cam_x
            gy = int(goomba.y)
            # draw goomba as a brown/orange rectangle
            pygame.draw.rect(game_surface, (165, 42, 42), (gx, gy + 8, goomba.width, goomba.height - 8))  # body
            pygame.draw.rect(game_surface, (0, 0, 0), (gx+4, gy+12, 8, 2))  # feet (small detail)

        # Draw player
        px = int(player.x) - cam_x
        py = int(player.y)
        player_color = players[active_player_index]["color"]
        pygame.draw.rect(game_surface, player_color, (px, py, player.width, player.height))
        # (We could draw eyes or features, but a solid color block suffices for this clone)

        # HUD text (world, lives, player)
        hud_text = f"World {current_world}-{current_level}   {players[0]['name']}:{players[0]['lives']}  {players[1]['name']}:{players[1]['lives']}"
        hud_surface = font.render(hud_text, True, COLOR_TEXT)
        game_surface.blit(hud_surface, (5, 5))

        # Scale game surface to window and update display
        scaled_surface = pygame.transform.scale(game_surface, window.get_size())
        window.blit(scaled_surface, (0, 0))
        pygame.display.flip()

        # Cap frame rate
        clock.tick(60)
    elif state == "game_over":
        # Display Game Over or Victory message
        game_surface.fill((0, 0, 0))
        if win:
            msg = "YOU WIN! CONGRATULATIONS!"
        else:
            msg = "GAME OVER"
        over_text = font.render(msg, True, COLOR_TEXT)
        prompt_text = font.render("Press any key to return to menu", True, COLOR_TEXT)
        game_surface.blit(over_text, (60, 100))
        game_surface.blit(prompt_text, (20, 130))
        scaled = pygame.transform.scale(game_surface, window.get_size())
        window.blit(scaled, (0, 0))
        pygame.display.flip()
        # Wait for key press or quit
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    waiting = False
                if event.type == pygame.KEYDOWN:
                    waiting = False
        # After any key, go back to menu
        state = "menu"
        win = False
        game_over = False
        playing = False

# Cleanup
pygame.quit()
