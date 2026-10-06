import asyncio
import math
import random
import pygame
from pygame.math import Vector2

# Start Pygame and create the game window.
pygame.init()
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Crazy Asteroids")
clock = pygame.time.Clock()

# Limit the frame rate and set the game colors.
TARGET_FPS = 120
BACKGROUND = (0, 0, 0)
WHITE = (255, 255, 255)
ASTEROID_COLOR = (0, 0, 0)
SHIP_COLOR = (255, 60, 60)
PATROL_COLOR = (80, 190, 255)
ATTACK_COLOR = (255, 100, 70)
HUD_FONT = pygame.font.Font(None, 24)


class Asteroid:
    # Create one asteroid with a position, size, speed, and shape.
    def __init__(self, position, radius, velocity, color, seed):
        self.position = Vector2(position)
        self.velocity = Vector2(velocity)
        self.radius = radius
        self.mass = radius * radius
        self.color = color
        self.angle = seed * 17
        self.spin = random.uniform(-1.5, 1.5)

        # Use a private random generator to make a repeatable rough shape.
        rng = random.Random(seed)
        self.shape = []
        for i in range(10):
            angle = i * math.tau / 10
            size = radius * rng.uniform(0.78, 1.18)
            self.shape.append(Vector2(math.cos(angle) * size,
                                      math.sin(angle) * size))

    # Move and rotate the asteroid, then wrap it around the screen edges.
    def update(self, dt):
        self.position += self.velocity * dt
        self.angle += self.spin * dt
        self.position.x %= WIDTH
        self.position.y %= HEIGHT

    # Draw a black asteroid with a white outline.
    def draw(self, surface):
        points = []
        for point in self.shape:
            points.append(self.position + point.rotate(self.angle))
        pygame.draw.polygon(surface, ASTEROID_COLOR, points)
        pygame.draw.polygon(surface, WHITE, points, 2)


class Bullet:
    # Create a bullet at a position with a starting velocity.
    def __init__(self, position, velocity):
        self.position = Vector2(position)
        self.velocity = Vector2(velocity)
        self.life = 1.2

    # Move the bullet and remove it after its lifetime ends.
    def update(self, dt):
        self.position += self.velocity * dt
        self.life -= dt
        return self.life > 0

    # Draw the bullet as a small yellow circle.
    def draw(self, surface):
        pygame.draw.circle(surface, (255, 225, 115), self.position, 3)


class Enemy:
    """A small ship that patrols until it detects the player in its FOV."""
    DETECTION_RANGE = 230
    FOV_COS_HALF_ANGLE = math.cos(math.radians(50))

    def __init__(self, position, heading):
        self.position = Vector2(position)
        self.heading = Vector2(heading).normalize()
        self.state = "patrol"
        self.patrol_turn = random.choice((-0.45, 0.45))
        self.speed = 90

    def can_see(self, target):
        to_target = Vector2(target) - self.position
        distance_squared = to_target.length_squared()
        if distance_squared == 0 or distance_squared > self.DETECTION_RANGE ** 2:
            return False

        # Dot product compares facing direction with the target direction.
        return self.heading.dot(to_target / math.sqrt(distance_squared)) >= self.FOV_COS_HALF_ANGLE

    def update(self, dt, target):
        if self.can_see(target):
            self.state = "attack"
            to_target = Vector2(target) - self.position
            if to_target.length_squared() > 0:
                self.heading = to_target.normalize()
        else:
            self.state = "patrol"
            self.heading.rotate_ip(math.degrees(self.patrol_turn * dt))

        self.position += self.heading * self.speed * dt
        self.position.x %= WIDTH
        self.position.y %= HEIGHT

    def draw(self, surface):
        color = ATTACK_COLOR if self.state == "attack" else PATROL_COLOR
        side = Vector2(-self.heading.y, self.heading.x)
        points = [self.position + self.heading * 13,
                  self.position - self.heading * 9 + side * 8,
                  self.position - self.heading * 9 - side * 8]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, WHITE, points, 1)


def make_enemies():
    positions = [(120, 120), (WIDTH - 120, HEIGHT - 120), (WIDTH - 120, 120)]
    enemies = []
    for position in positions:
        heading = Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        if heading.length_squared() == 0:
            heading = Vector2(1, 0)
        enemies.append(Enemy(position, heading))
    return enemies


def make_asteroids():
    # Create six asteroids with different speeds and random directions.
    asteroids = []
    speeds = [72, 91, 109, 128, 147, 166]

    for i, speed in enumerate(speeds):
        angle = random.uniform(0, math.tau)
        position = Vector2(random.randint(80, WIDTH - 80),
                           random.randint(70, HEIGHT - 70))
        radius = random.randint(25, 46)
        velocity = Vector2(math.cos(angle), math.sin(angle)) * speed
        asteroids.append(Asteroid(position, radius, velocity,
                                   ASTEROID_COLOR, i + 10))

    return asteroids


def resolve_asteroid_collision(first, second):
    # Find the direction and distance between the two asteroid centers.
    offset = second.position - first.position
    distance = offset.length()
    minimum_distance = first.radius + second.radius

    # Choose a safe collision direction if both centers are in the same place.
    if distance == 0:
        relative_velocity = second.velocity - first.velocity
        normal = (relative_velocity.normalize()
                  if relative_velocity.length_squared() > 0 else Vector2(1, 0))
        distance = 0.001
    else:
        normal = offset / distance

    # Stop if the circular collision areas do not overlap.
    if distance >= minimum_distance:
        return

    # Separate the overlapping asteroids based on their masses.
    overlap = minimum_distance - distance
    total_mass = first.mass + second.mass
    first.position -= normal * overlap * (second.mass / total_mass)
    second.position += normal * overlap * (first.mass / total_mass)

    # Measure the relative speed along the collision normal.
    relative_velocity = second.velocity - first.velocity
    speed_along_normal = relative_velocity.dot(normal)

    # Ignore the impulse if the asteroids are already moving apart.
    if speed_along_normal >= 0:
        return

    # Use an elastic collision impulse to transfer momentum between asteroids.
    restitution = 0.90
    impulse_size = -(1 + restitution) * speed_along_normal
    impulse_size /= (1 / first.mass) + (1 / second.mass)
    impulse = normal * impulse_size
    first.velocity -= impulse / first.mass
    second.velocity += impulse / second.mass


def draw_ship(surface, position, angle):
    # Build a transparent triangle that points in the ship's direction.
    forward = Vector2(0, -1).rotate(-angle)
    side = Vector2(1, 0).rotate(-angle)
    points = [position + forward * 20,
              position - forward * 14 + side * 12,
              position - forward * 14 - side * 12]

    # Draw only the red outline.
    pygame.draw.polygon(surface, SHIP_COLOR, points, 2)


def new_game():
    # Return the starting state for a new game.
    return (make_asteroids(), make_enemies(),
            Vector2(WIDTH / 2, HEIGHT / 2), [], 0, 3)


async def main():
    # Set the initial game state.
    asteroids, enemies, ship_position, bullets, score, lives = new_game()
    ship_invulnerable = 0
    ship_velocity = Vector2()
    ship_angle = 0
    shoot_cooldown = 0
    running = True

    # Run the main game loop until the window is closed.
    while running:
        # Use elapsed time so movement is independent of frame rate.
        dt = min(clock.tick(0) / 1000.0, 0.05)

        # Handle window events and keyboard actions.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and shoot_cooldown <= 0:
                    # Fire a bullet in the direction the ship is facing.
                    direction = Vector2(0, -1).rotate(-ship_angle)
                    bullets.append(Bullet(ship_position + direction * 20,
                                          direction * 430 + ship_velocity))
                    shoot_cooldown = 0.22
                elif event.key == pygame.K_r and not asteroids:
                    # Restart after all asteroids are removed.
                    asteroids, enemies, ship_position, bullets, score, lives = new_game()
                    ship_invulnerable = 0

        # Read the current movement keys.
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]:
            ship_angle += 190 * dt
        if keys[pygame.K_d]:
            ship_angle -= 190 * dt
        if keys[pygame.K_w]:
            thrust = Vector2(0, -260).rotate(-ship_angle)
            ship_velocity += thrust * dt
        if keys[pygame.K_s]:
            ship_velocity *= max(0, 1 - 2.5 * dt)

        # Apply drag, move the ship, and wrap it around the screen edges.
        ship_velocity *= 1 - min(0.8 * dt, 0.08)
        ship_position += ship_velocity * dt
        ship_position.x %= WIDTH
        ship_position.y %= HEIGHT
        shoot_cooldown -= dt
        ship_invulnerable = max(0, ship_invulnerable - dt)

        # Update every asteroid.
        for asteroid in asteroids:
            asteroid.update(dt)

        # Run several collision passes to reduce overlap between asteroids.
        for _ in range(3):
            for i in range(len(asteroids)):
                for j in range(i + 1, len(asteroids)):
                    resolve_asteroid_collision(asteroids[i], asteroids[j])

        # Update enemy AI; each enemy switches state based on range and FOV.
        for enemy in enemies:
            enemy.update(dt, ship_position)

        # Update bullets and remove bullets whose lifetime has ended.
        bullets = [bullet for bullet in bullets if bullet.update(dt)]

        # Remove asteroids hit by bullets without copying/removing from the list repeatedly.
        remaining_asteroids = []
        spent_bullets = set()
        for asteroid in asteroids:
            hit = False
            for bullet in bullets:
                if (bullet not in spent_bullets and
                        bullet.position.distance_squared_to(asteroid.position) < asteroid.radius ** 2):
                    spent_bullets.add(bullet)
                    score += 10
                    hit = True
                    break
            if not hit:
                remaining_asteroids.append(asteroid)
        asteroids = remaining_asteroids
        bullets = [bullet for bullet in bullets if bullet not in spent_bullets]

        # Take a life when the ship touches an asteroid or enemy.
        asteroid_hit = any(
            ship_position.distance_squared_to(a.position) < (a.radius + 14) ** 2
            for a in asteroids
        )
        enemy_hit = any(
            ship_position.distance_squared_to(enemy.position) < 22 ** 2
            for enemy in enemies
        )
        if lives > 0 and ship_invulnerable <= 0 and (asteroid_hit or enemy_hit):
            lives = max(0, lives - 1)
            ship_position = Vector2(WIDTH / 2, HEIGHT / 2)
            ship_velocity.update(0, 0)
            ship_invulnerable = 1.5

            # End the game when all lives are lost.
            if lives == 0:
                asteroids.clear()

        # Draw the current frame.
        screen.fill(BACKGROUND)
        for asteroid in asteroids:
            asteroid.draw(screen)
        for enemy in enemies:
            enemy.draw(screen)
        for bullet in bullets:
            bullet.draw(screen)
        if asteroids and (ship_invulnerable <= 0 or int(ship_invulnerable * 10) % 2 == 0):
            draw_ship(screen, ship_position, ship_angle)

        patrol_count = sum(enemy.state == "patrol" for enemy in enemies)
        attack_count = len(enemies) - patrol_count
        hud = HUD_FONT.render(
            f"Score: {score}  Lives: {lives}  AI: {patrol_count} PATROL / {attack_count} ATTACK",
            True, WHITE
        )
        screen.blit(hud, (12, 12))

        pygame.display.flip()
        await asyncio.sleep(0)

    # Close Pygame when the loop ends.
    pygame.quit()


asyncio.run(main())
