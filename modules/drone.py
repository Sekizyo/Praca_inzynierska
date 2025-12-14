import taichi as ti
import random

from taichi import Vector, Field, MatrixField, data_oriented, func
from taichi.types import vector, f32, i32
from modules.constants import DroneModes
from modules.gui_utils import GuiState

@data_oriented
class DroneSwarm:
    max_speed: float = 15.0
    max_force: float = 0.5
    perception_radius: float = 40.0
    height: float = 50.0
    mode: DroneModes = DroneModes.SPREAD
    projectile_speed: float = 50.0
    shoot_range: float = 25.0
    shoot_cooldown: float = 3.0
    hit_radius: float = 2.0
    max_health: float = 100.0
    projectile_damage: float = 25.0
    projectile_max_lifetime: float = 2.0
    projectile_radius: float = 0.5
    segments_per_circle: int = 64

    def __init__(self, count: int, boundary_size: float, team: int = 0) -> None:
        self.N: int = count
        self.boundary: float = boundary_size
        self.team: int = team
        
        self.pos: MatrixField = Vector.field(3, dtype=f32, shape=self.N)
        self.vel: MatrixField = Vector.field(3, dtype=f32, shape=self.N)
        self.acc: MatrixField = Vector.field(3, dtype=f32, shape=self.N)
        
        self.active: Field = ti.field(dtype=ti.i32, shape=self.N)
        self.health: Field = ti.field(dtype=ti.f32, shape=self.N)
        self.cooldown: Field = ti.field(dtype=ti.f32, shape=self.N)
        
        self.max_projectiles: int = count * 10
        self.projectile_pos: MatrixField = Vector.field(3, dtype=f32, shape=self.max_projectiles)
        self.projectile_vel: MatrixField = Vector.field(3, dtype=f32, shape=self.max_projectiles)
        self.projectile_active: Field = ti.field(dtype=ti.i32, shape=self.max_projectiles)
        self.projectile_lifetime: Field = ti.field(dtype=ti.f32, shape=self.max_projectiles)
        
        max_segments = self.N * self.segments_per_circle * 2
        self.range_circles = ti.Vector.field(3, dtype=ti.f32, shape=max_segments)
        
        # Modifiers as Taichi fields
        self.separation_modifier = ti.field(dtype=ti.f32, shape=())
        self.alignment_modifier = ti.field(dtype=ti.f32, shape=())
        self.cohesion_modifier = ti.field(dtype=ti.f32, shape=())
        self.target_weight = ti.field(dtype=ti.f32, shape=())
        
        self.separation_modifier[None] = 5.0
        self.alignment_modifier[None] = 0.1
        self.cohesion_modifier[None] = 0.1
        self.target_weight[None] = 0.5
        
        self._initialize()

    def _initialize(self) -> None:
        for i in range(self.N):
            self.pos[i] = [
                (random.random() - 0.5) * self.boundary * 1.5,
                (random.random() - 0.5) * self.boundary * 1.5,
                (random.random() - 0.5) * self.boundary * 0.5
            ]
            
            self.vel[i] = [
                (random.random() - 0.5) * 5.0,
                (random.random() - 0.5) * 5.0,
                (random.random() - 0.5) * 2.0
            ]
            
            self.active[i] = 1
            self.health[i] = self.max_health
            self.cooldown[i] = 0.0
        
        for i in range(self.max_projectiles):
            self.projectile_active[i] = 0
            self.projectile_lifetime[i] = 0.0
            
    def get_mode(self) -> DroneModes:   
        return self.mode

    def get_modifiers(self) -> tuple[float, float, float, float]:
        return (self.separation_modifier[None], self.alignment_modifier[None], self.cohesion_modifier[None], self.target_weight[None])
    
    @ti.func
    def separation(self, i: ti.i32) -> ti.types.vector(3, ti.f32):
        steering = ti.Vector([0.0, 0.0, 0.0])
        count = 0
        for j in range(self.N):
            if i != j and self.active[j] == 1:
                dist = (self.pos[i] - self.pos[j]).norm()
                if dist < self.perception_radius * 0.6 and dist > 0:
                    diff = self.pos[i] - self.pos[j]
                    diff = diff.normalized() / dist
                    steering += diff
                    count += 1
        if count > 0:
            steering /= count
            if steering.norm() > 0:
                steering = steering.normalized() * self.max_speed
                steering -= self.vel[i]
                if steering.norm() > self.max_force:
                    steering = steering.normalized() * self.max_force
        return steering

    @ti.func
    def alignment(self, i: ti.i32) -> ti.types.vector(3, ti.f32):
        steering = ti.Vector([0.0, 0.0, 0.0])
        count = 0
        for j in range(self.N):
            if i != j and self.active[j] == 1:
                dist = (self.pos[i] - self.pos[j]).norm()
                if dist < self.perception_radius:
                    steering += self.vel[j]
                    count += 1
        if count > 0:
            steering /= count
            steering = steering.normalized() * self.max_speed
            steering -= self.vel[i]
            if steering.norm() > self.max_force:
                steering = steering.normalized() * self.max_force
        return steering

    @ti.func
    def cohesion(self, i: ti.i32) -> ti.types.vector(3, ti.f32):
        steering = ti.Vector([0.0, 0.0, 0.0])
        count = 0
        for j in range(self.N):
            if i != j and self.active[j] == 1:
                dist = (self.pos[i] - self.pos[j]).norm()
                if dist < self.perception_radius:
                    steering += self.pos[j]
                    count += 1
        if count > 0:
            steering /= count
            desired = steering - self.pos[i]
            desired = desired.normalized() * self.max_speed
            steering = desired - self.vel[i]
            if steering.norm() > self.max_force:
                steering = steering.normalized() * self.max_force
        return steering
    
    def update_mode(self, mode: DroneModes) -> None:
        self.mode = mode
        
        if self.mode == DroneModes.ATTACK:
            self.separation_modifier[None] = 3
            self.alignment_modifier[None] = 2.0
            self.cohesion_modifier[None] = 1.0
            self.target_weight[None] = 1.0
        elif self.mode == DroneModes.SPREAD:
            self.separation_modifier[None] = 10.0
            self.alignment_modifier[None] = 0.2
            self.cohesion_modifier[None] = 0.2
            self.target_weight[None] = 0.3
        elif self.mode == DroneModes.PATROL:
            self.separation_modifier[None] = 2
            self.alignment_modifier[None] = 2.0
            self.cohesion_modifier[None] = 3.0
            self.target_weight[None] = 1.0

    @ti.kernel
    def update(self, dt: ti.f32, target_pos: ti.template()):
        for i in range(self.N):
            if self.active[i] == 0:
                continue

            self.acc[i] = ti.Vector([0.0, 0.0, 0.0])
            
            sep = self.separation(i)
            ali = self.alignment(i)
            coh = self.cohesion(i)
            
            self.acc[i] += sep * self.separation_modifier[None]
            self.acc[i] += ali * self.alignment_modifier[None]
            self.acc[i] += coh * self.cohesion_modifier[None]
            
            # Boundary constraints - soft walls with stronger force
            boundary_force = self.max_force * 5.0
            margin = 10.0  # Distance from boundary where force starts
            
            if self.pos[i].x > self.boundary - margin:
                self.acc[i].x -= boundary_force * (self.pos[i].x - (self.boundary - margin)) / margin
            if self.pos[i].x < -self.boundary + margin:
                self.acc[i].x += boundary_force * ((-self.boundary + margin) - self.pos[i].x) / margin
            if self.pos[i].y > self.boundary - margin:
                self.acc[i].y -= boundary_force * (self.pos[i].y - (self.boundary - margin)) / margin
            if self.pos[i].y < -self.boundary + margin:
                self.acc[i].y += boundary_force * ((-self.boundary + margin) - self.pos[i].y) / margin
            if self.pos[i].z > self.height - margin:
                self.acc[i].z -= boundary_force * (self.pos[i].z - (self.height - margin)) / margin
            if self.pos[i].z < margin:
                self.acc[i].z += boundary_force * (margin - self.pos[i].z) / margin
            
            # Hard clamp - prevent going outside boundaries
            if self.pos[i].x > self.boundary:
                self.pos[i].x = self.boundary
                self.vel[i].x = 0.0
            if self.pos[i].x < -self.boundary:
                self.pos[i].x = -self.boundary
                self.vel[i].x = 0.0
            if self.pos[i].y > self.boundary:
                self.pos[i].y = self.boundary
                self.vel[i].y = 0.0
            if self.pos[i].y < -self.boundary:
                self.pos[i].y = -self.boundary
                self.vel[i].y = 0.0
            if self.pos[i].z > self.height:
                self.pos[i].z = self.height
                self.vel[i].z = 0.0
            if self.pos[i].z < 0.0:
                self.pos[i].z = 0.0
                self.vel[i].z = 0.0
            
            # Steering towards target (2D - only x and y)
            target_3d = ti.Vector([target_pos[0][0], target_pos[0][1], 0.0])
            direction = (target_3d - self.pos[i]).normalized()
            self.acc[i] += direction * self.target_weight[None]

            # Physics integration
            self.vel[i] += self.acc[i] * dt
            
            vel_norm = self.vel[i].norm()
            if vel_norm > self.max_speed:
                self.vel[i] = self.vel[i].normalized() * self.max_speed
            
            self.pos[i] += self.vel[i] * dt
            
            if self.cooldown[i] > 0.0:
                self.cooldown[i] -= dt

    @ti.kernel
    def shoot(self, enemy_pos: ti.template(), enemy_count: ti.i32, enemy_health: ti.template()):
        for i in range(self.N):
            if self.active[i] == 0 or self.cooldown[i] > 0.0:
                continue
            
            min_dist = ti.cast(1e10, ti.f32)
            target_idx = -1
            
            for j in range(enemy_count):
                if enemy_health[j] <= 0.0:
                    continue
                dist = (self.pos[i] - enemy_pos[j]).norm()
                if dist < self.shoot_range and dist < min_dist:
                    min_dist = dist
                    target_idx = j
            
            if target_idx >= 0:
                for p in range(self.max_projectiles):
                    if self.projectile_active[p] == 0:
                        direction = (enemy_pos[target_idx] - self.pos[i]).normalized()
                        self.projectile_pos[p] = self.pos[i]
                        self.projectile_vel[p] = direction * self.projectile_speed
                        self.projectile_active[p] = 1
                        self.projectile_lifetime[p] = self.projectile_max_lifetime
                        self.cooldown[i] = self.shoot_cooldown
                        break

    @ti.kernel
    def update_projectiles(self, dt: ti.f32):
        for i in range(self.max_projectiles):
            if self.projectile_active[i] == 0:
                continue
            
            self.projectile_pos[i] += self.projectile_vel[i] * dt
            self.projectile_lifetime[i] -= dt
            
            if self.projectile_lifetime[i] <= 0.0:
                self.projectile_active[i] = 0
                self.projectile_pos[i] = ti.Vector([0.0, 0.0, -10000.0])
            
            if self.projectile_pos[i].x > self.boundary or self.projectile_pos[i].x < -self.boundary:
                self.projectile_active[i] = 0
                self.projectile_pos[i] = ti.Vector([0.0, 0.0, -10000.0])
            if self.projectile_pos[i].y > self.boundary or self.projectile_pos[i].y < -self.boundary:
                self.projectile_active[i] = 0
                self.projectile_pos[i] = ti.Vector([0.0, 0.0, -10000.0])
            if self.projectile_pos[i].z > self.height or self.projectile_pos[i].z < 0.0:
                self.projectile_active[i] = 0
                self.projectile_pos[i] = ti.Vector([0.0, 0.0, -10000.0])

    @ti.kernel
    def check_hits(self, enemy_pos: ti.template(), enemy_count: ti.i32, enemy_health: ti.template()):
        for i in range(self.max_projectiles):
            if self.projectile_active[i] == 0:
                continue
            
            for j in range(enemy_count):
                if enemy_health[j] <= 0.0:
                    continue
                
                dist = (self.projectile_pos[i] - enemy_pos[j]).norm()
                if dist < self.hit_radius:
                    self.projectile_active[i] = 0
                    self.projectile_pos[i] = ti.Vector([0.0, 0.0, -10000.0])
                    ti.atomic_add(enemy_health[j], -self.projectile_damage)
                    break
    
    @ti.kernel
    def update_health(self):
        for i in range(self.N):
            if self.health[i] <= 0.0:
                self.active[i] = 0
                self.pos[i] = ti.Vector([-10000.0, 0.0, 0.0])
    
    @ti.kernel
    def compute_range_circles(self):
        for i in range(self.N):
            if self.active[i] == 0:
                continue
            
            for seg in range(self.segments_per_circle):
                angle1 = (ti.cast(seg, ti.f32) / self.segments_per_circle) * 2.0 * 3.14159265359
                angle2 = (ti.cast(seg + 1, ti.f32) / self.segments_per_circle) * 2.0 * 3.14159265359
                mid_angle = (angle1 + angle2) * 0.5
                
                x_point = self.pos[i].x + self.shoot_range * ti.cos(mid_angle)
                y_point = self.pos[i].y + self.shoot_range * ti.sin(mid_angle)
                
                is_inside_other = 0
                
                for j in range(self.N):
                    if i == j or self.active[j] == 0:
                        continue
                    
                    dx = x_point - self.pos[j].x
                    dy = y_point - self.pos[j].y
                    dist_to_center = ti.sqrt(dx * dx + dy * dy)
                    
                    if dist_to_center < self.shoot_range - 0.1:
                        is_inside_other = 1
                        break
                
                idx = i * self.segments_per_circle * 2 + seg * 2
                
                if is_inside_other == 0:
                    x1 = self.pos[i].x + self.shoot_range * ti.cos(angle1)
                    y1 = self.pos[i].y + self.shoot_range * ti.sin(angle1)
                    z1 = 0.0
                    
                    x2 = self.pos[i].x + self.shoot_range * ti.cos(angle2)
                    y2 = self.pos[i].y + self.shoot_range * ti.sin(angle2)
                    z2 = 0.0
                    
                    self.range_circles[idx] = ti.Vector([x1, y1, z1])
                    self.range_circles[idx + 1] = ti.Vector([x2, y2, z2])
                else:
                    self.range_circles[idx] = ti.Vector([0.0, 0.0, -1000.0])
                    self.range_circles[idx + 1] = ti.Vector([0.0, 0.0, -1000.0])
                    
    def get_range_circles(self) -> MatrixField:
        return self.range_circles

    def get_pos_field(self) -> MatrixField:
        return self.pos
    
    def get_projectile_pos_field(self) -> MatrixField:
        return self.projectile_pos
    
    def get_projectile_active_field(self) -> Field:
        return self.projectile_active
        