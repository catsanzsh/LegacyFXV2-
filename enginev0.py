import pygame, sys

# Initialize pygame and mixer
pygame.init()
pygame.mixer.init()

# Screen and game constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
TILE_SIZE = 32  # Size of tiles in pixels (16x16 tiles scaled to 32x32 for NES style)

# Define Colors (including the missing 'green')
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED   = (255, 0, 0)
GREEN = (0, 255, 0)    # Added missing green color&#8203;:contentReference[oaicite:20]{index=20}
BLUE  = (0, 0, 255)
YELLOW= (255, 255, 0)

# Load images for tiles and sprites (using placeholders for illustration)
ground_img    = pygame.Surface((TILE_SIZE, TILE_SIZE));      ground_img.fill((0, 200, 0))      # green ground tile
brick_img     = pygame.Surface((TILE_SIZE, TILE_SIZE));      brick_img.fill((139, 69, 19))     # brown brick tile
question_img  = pygame.Surface((TILE_SIZE, TILE_SIZE));      question_img.fill(YELLOW)         # question block
used_block_img= pygame.Surface((TILE_SIZE, TILE_SIZE));      used_block_img.fill((200, 200, 0))# used (inactive) block
# Sprites for player (small & big) and enemy
player_small_img = pygame.Surface((TILE_SIZE, TILE_SIZE));       player_small_img.fill((255, 128, 0))
player_big_img   = pygame.Surface((TILE_SIZE, 2*TILE_SIZE));     player_big_img.fill((255, 128, 0))
goomba_frame1    = pygame.Surface((TILE_SIZE, TILE_SIZE));       goomba_frame1.fill((165, 42, 42))
goomba_frame2    = pygame.Surface((TILE_SIZE, TILE_SIZE));       goomba_frame2.fill((205, 92, 92))
goomba_flat_img  = pygame.Surface((TILE_SIZE, TILE_SIZE//2));    goomba_flat_img.fill((128, 128, 128))
mushroom_img     = pygame.Surface((TILE_SIZE, TILE_SIZE));       mushroom_img.fill((255, 0, 255))

# (In a real game, you would load images from files and use convert()/convert_alpha() for performance&#8203;:contentReference[oaicite:21]{index=21})

# Load sounds
try:
    jump_sound    = pygame.mixer.Sound("jump.wav")
    coin_sound    = pygame.mixer.Sound("coin.wav")
    stomp_sound   = pygame.mixer.Sound("stomp.wav")
    powerup_sound = pygame.mixer.Sound("powerup.wav")
    bump_sound    = pygame.mixer.Sound("bump.wav")
    die_sound     = pygame.mixer.Sound("die.wav")
except Exception as e:
    # If files not found or mixer error, use None as fallback to avoid crashes
    jump_sound = coin_sound = stomp_sound = powerup_sound = bump_sound = die_sound = None

# Level layout (string map for simplicity; would likely come from a file or generator)
level_map = [
    "                                                ",
    "                                                ",
    "   ?                                            ",
    "                                                ",
    "                              G                 ",
    "===============================         =======",
    "                                                "
]
# Legend: '=' = ground, '?' = question block (with a mushroom), 'G' = Goomba enemy

# Create data structures for level
solid_tiles = []         # list of Rects for all solid blocks (ground, pipes, blocks)
question_blocks = {}     # map from (x,y) to block info for question blocks
enemies = pygame.sprite.Group()
items = pygame.sprite.Group()

# Parse the level map to initialize tiles and spawn objects
for row_idx, row in enumerate(level_map):
    for col_idx, cell in enumerate(row):
        x = col_idx * TILE_SIZE
        y = row_idx * TILE_SIZE
        if cell == '=':  # solid ground block
            solid_tiles.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))
        elif cell == '?':  # question block with a power-up inside
            rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
            solid_tiles.append(rect)  # treat as solid
            question_blocks[(x, y)] = {"rect": rect, "used": False, "contains": "mushroom"}
        elif cell == 'G':  # Goomba enemy
            enemy = pygame.sprite.Sprite()
            enemy.image = goomba_frame1
            enemy.rect = enemy.image.get_rect(topleft=(x, y))
            enemy.vx = -1  # move left by default
            enemy.vy = 0
            enemy.on_ground = False
            enemy.frame_counter = 0
            enemies.add(enemy)
        # (Other entities like pipes or coins can be added similarly)

# Define the Player class with movement, jump, collision, etc.
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = player_small_img
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vx = 0
        self.vy = 0
        self.speed = 3         # horizontal speed
        self.jump_power = 10   # jump velocity
        self.on_ground = False
        self.is_big = False
        self.invulnerable_timer = 0
        self.direction = 1     # 1 = facing right, -1 = facing left

    def update(self, keys):
        # Horizontal movement input
        if keys[pygame.K_LEFT]:
            self.vx = -self.speed
            self.direction = -1
        elif keys[pygame.K_RIGHT]:
            self.vx = self.speed
            self.direction = 1
        else:
            # No horizontal input; apply friction to slow down if on ground
            if self.on_ground:
                if self.vx > 0:
                    self.vx -= 1
                    if self.vx < 0: self.vx = 0
                elif self.vx < 0:
                    self.vx += 1
                    if self.vx > 0: self.vx = 0

        # Jumping
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vy = -self.jump_power
            self.on_ground = False
            if jump_sound: jump_sound.play()

        # Gravity
        self.vy += 0.5  # gravity acceleration
        if self.vy > 12:   # terminal velocity cap
            self.vy = 12

        # Horizontal movement and collision
        self.rect.x += int(self.vx)
        for tile in solid_tiles:
            if self.rect.colliderect(tile):
                if self.vx > 0:   # moving right, hit a wall
                    self.rect.right = tile.left
                elif self.vx < 0: # moving left, hit a wall
                    self.rect.left = tile.right
                self.vx = 0  # stop horizontal movement on collision

        # Vertical movement and collision
        self.rect.y += int(self.vy)
        self.on_ground = False  # will be set True if landing on something
        for tile in solid_tiles:
            if self.rect.colliderect(tile):
                if self.vy > 0:  # falling down and hit ground
                    self.rect.bottom = tile.top
                    self.on_ground = True
                elif self.vy < 0:  # moving up and hit a ceiling/block
                    self.rect.top = tile.bottom
                    # Trigger question block if applicable
                    if (tile.x, tile.y) in question_blocks and not question_blocks[(tile.x, tile.y)]["used"]:
                        # Hit a question block from below
                        qb = question_blocks[(tile.x, tile.y)]
                        qb["used"] = True
                        if qb["contains"] == "mushroom":
                            # Spawn mushroom above the block
                            item = pygame.sprite.Sprite()
                            item.image = mushroom_img
                            item.rect = item.image.get_rect(midbottom=tile.midtop)
                            item.vx = 1  # mushroom moves to the right initially
                            item.vy = 0
                            items.add(item)
                        if bump_sound: bump_sound.play()
                self.vy = 0  # stop vertical movement

        # Handle power-up state (resize Mario if needed)
        if self.is_big:
            if self.image is player_small_img:  # Mario just became big
                bottom = self.rect.bottom
                self.image = player_big_img
                self.rect = self.image.get_rect(midbottom=(self.rect.centerx, bottom))
        else:
            if self.image is player_big_img:    # Mario just shrank to small
                bottom = self.rect.bottom
                self.image = player_small_img
                self.rect = self.image.get_rect(midbottom=(self.rect.centerx, bottom))

        # Invulnerability timer decrement
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= 1

    def get_hit(self):
        """Handle player getting hit by an enemy."""
        if self.invulnerable_timer > 0:
            return  # currently invulnerable, ignore the hit
        if self.is_big:
            # Shrink to small Mario instead of dying
            self.is_big = False
            self.invulnerable_timer = 60  # ~1 second of invincibility
            if powerup_sound: powerup_sound.play()  # play a power-down sound (reuse powerup_sound)
        else:
            # Mario is small and gets hit -> lose a life (game over scenario here)
            if die_sound: die_sound.play()
            # End the game or reset (here we'll just quit for simplicity)
            pygame.quit()
            sys.exit()

# Initialize player
player = Player(x=50, y=SCREEN_HEIGHT - 2*TILE_SIZE)  # start near the bottom left
player_group = pygame.sprite.GroupSingle(player)

# Set up display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("NES-style Mario")

clock = pygame.time.Clock()
camera_x = 0  # camera offset for scrolling

# Main game loop
running = True
while running:
    clock.tick(FPS)  # cap frame rate
    
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:   # handle window close
            running = False
        # (If there are any other one-time events like shooting fireballs, handle KEYDOWN here)
    
    # Get key states
    keys = pygame.key.get_pressed()
    # Update player (movement & collisions)
    player_group.update(keys)
    
    # Update enemies (movement, gravity, animation)
    for enemy in enemies:
        # Apply gravity to enemy
        enemy.vy += 0.5
        if enemy.vy > 10: 
            enemy.vy = 10
        # Horizontal movement and wall bounce
        enemy.rect.x += int(enemy.vx)
        for tile in solid_tiles:
            if enemy.rect.colliderect(tile):
                if enemy.vx > 0:
                    enemy.rect.right = tile.left
                elif enemy.vx < 0:
                    enemy.rect.left = tile.right
                enemy.vx *= -1  # reverse direction on hit wall
        # Vertical movement and floor collision
        enemy.rect.y += int(enemy.vy)
        enemy.on_ground = False
        for tile in solid_tiles:
            if enemy.rect.colliderect(tile):
                if enemy.vy > 0:
                    enemy.rect.bottom = tile.top
                    enemy.on_ground = True
                elif enemy.vy < 0:
                    enemy.rect.top = tile.bottom
                enemy.vy = 0
        # Animate Goomba by toggling frames
        enemy.frame_counter = (enemy.frame_counter + 1) % 30  # slow toggle
        if enemy.frame_counter == 0:  # switch frame periodically
            enemy.image = goomba_frame1 if enemy.image == goomba_frame2 else goomba_frame2
    
    # Update moving items (e.g., mushrooms)
    for item in items:
        if hasattr(item, 'vx'):
            # Apply gravity
            item.vy += 0.5
            if item.vy > 10: 
                item.vy = 10
            # Horizontal move
            item.rect.x += int(item.vx)
            for tile in solid_tiles:
                if item.rect.colliderect(tile):
                    if item.vx > 0:
                        item.rect.right = tile.left
                    elif item.vx < 0:
                        item.rect.left = tile.right
                    item.vx *= -1  # bounce off walls
            # Vertical move
            item.rect.y += int(item.vy)
            for tile in solid_tiles:
                if item.rect.colliderect(tile):
                    if item.vy > 0:
                        item.rect.bottom = tile.top
                    elif item.vy < 0:
                        item.rect.top = tile.bottom
                    item.vy = 0
        # Remove item if it falls off the bottom of the level (no need to keep it)
        if item.rect.top > SCREEN_HEIGHT:
            items.remove(item)
    
    # Player collisions with enemies
    for enemy in pygame.sprite.spritecollide(player, enemies, False):
        if player.vy > 0 and player.rect.bottom <= enemy.rect.bottom + 5:
            # Mario is falling onto the enemy -> stomp
            enemies.remove(enemy)  # remove the enemy
            if stomp_sound: stomp_sound.play()
            # Spawn a flattened enemy sprite (for animation) or just remove completely
            stomped = pygame.sprite.Sprite()
            stomped.image = goomba_flat_img
            stomped.rect = stomped.image.get_rect(midbottom = enemy.rect.midbottom)
            # We could display the stomped image briefly; here we'll skip straight to removal
            # Bounce Mario up a bit after stomp
            player.vy = -6
        else:
            # Enemy hit Mario from side or above -> Mario takes damage
            player.get_hit()
            # If Mario died in get_hit(), the game loop will exit
    
    # Player collisions with items (power-ups, coins)
    for item in pygame.sprite.spritecollide(player, items, True):
        # Assume any item in this group is a mushroom for power-up (coins could be handled separately)
        player.is_big = True  # Mario grows
        player.invulnerable_timer = 60  # a brief grace period after powering up
        if powerup_sound: powerup_sound.play()
    
    # Camera scrolling logic (keep player near center, clamp at edges)&#8203;:contentReference[oaicite:22]{index=22}
    level_width_px = len(level_map[0]) * TILE_SIZE
    # Center camera on player by default
    camera_x = -player.rect.centerx + SCREEN_WIDTH // 2
    # Clamp camera within level bounds
    if camera_x > 0:
        camera_x = 0  # do not scroll left past start
    if camera_x < -(level_width_px - SCREEN_WIDTH):
        camera_x = -(level_width_px - SCREEN_WIDTH)  # do not scroll past end of level
    
    # Drawing everything
    screen.fill((107, 140, 255))  # sky blue background
    # Draw tiles in view
    for (x, y), qb in question_blocks.items():
        # Draw question or used block
        if qb["used"]:
            screen.blit(used_block_img, (x + camera_x, y))
        else:
            screen.blit(question_img, (x + camera_x, y))
    for tile in solid_tiles:
        # Draw ground/solid blocks (excluding question blocks which were drawn above to potentially override)
        # Here we assume ground tiles ('=') are all in solid_tiles except those also in question_blocks.
        if (tile.x, tile.y) not in question_blocks:
            screen.blit(ground_img, (tile.x + camera_x, tile.y))
    # Draw enemies and items
    for enemy in enemies:
        screen.blit(enemy.image, enemy.rect.move(camera_x, 0))
    for item in items:
        screen.blit(item.image, item.rect.move(camera_x, 0))
    # Draw player (with flicker if invulnerable)
    if player.invulnerable_timer > 0 and player.invulnerable_timer % 10 < 5:
        # skip drawing (flicker effect)
        pass
    else:
        # Ensure the player is facing the correct direction visually
        if player.direction < 0:
            # Flip the player image for left-facing (without permanently altering the original sprite)
            flipped_image = pygame.transform.flip(player.image, True, False)
            screen.blit(flipped_image, player.rect.move(camera_x, 0))
        else:
            screen.blit(player.image, player.rect.move(camera_x, 0))
    
    pygame.display.flip()

# Quit game loop
pygame.quit()
