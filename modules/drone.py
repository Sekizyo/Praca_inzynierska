import taichi as ti
import random

from taichi import Vector, Field, MatrixField, data_oriented, func
from taichi.types import vector, f32, i32
from modules.constants import DroneModes
from modules.gui_utils import GuiState

from modules.utils import run_every_n_calls

@data_oriented
class DroneSwarm:
    max_speed: float = 15.0
    max_force: float = 0.5
    perception_radius: float = 40.0
    mode: DroneModes = DroneModes.SPREAD
    projectile_speed: float = 50.0
    shoot_range: float = 50.0
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
        
        self.projectile_free_list: Field = ti.field(dtype=ti.i32, shape=self.max_projectiles)
        self.projectile_free_count: Field = ti.field(dtype=ti.i32, shape=())
        
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
        
        self.center_x = ti.field(dtype=ti.f32, shape=())
        self.center_y = ti.field(dtype=ti.f32, shape=())
        self.center_z = ti.field(dtype=ti.f32, shape=())
        
        self._initialize()

    def _initialize(self) -> None:
        for i in range(self.N):
            if self.team == 0:
                self.pos[i] = [
                    -random.random() * self.boundary * 1.5,
                    -random.random() * self.boundary * 1.5,
                    random.random() * self.boundary * 1.5
                ]
            else:
                self.pos[i] = [
                    random.random() * self.boundary * 1.5,
                    random.random() * self.boundary * 1.5,
                    random.random() * self.boundary * 1.5
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
            self.projectile_free_list[i] = i
        
        self.projectile_free_count[None] = self.max_projectiles
            
    def get_mode(self) -> DroneModes:   
        return self.mode

    def get_modifiers(self) -> tuple[float, float, float, float]:
        return (self.separation_modifier[None], self.alignment_modifier[None], self.cohesion_modifier[None], self.target_weight[None])
    
    @ti.kernel
    def get_alive_count(self) -> ti.i32:
        count = 0
        for i in range(self.N):
            if self.active[i] == 1:
                count += 1
        return count
    
    @ti.func
    def separation(self, i: ti.i32) -> ti.types.vector(3, ti.f32):
        steering = ti.Vector([0.0, 0.0, 0.0])
        count = 0
        perception_sq = (self.perception_radius * 0.6) ** 2
        
        for j in range(self.N):
            if i != j and self.active[j] == 1:
                diff = self.pos[i] - self.pos[j]
                dist_sq = diff.norm_sqr()
                if dist_sq < perception_sq and dist_sq > 1e-6:
                    inv_dist = ti.rsqrt(dist_sq)
                    steering += diff * inv_dist * inv_dist
                    count += 1
        
        if count > 0:
            steering /= ti.cast(count, ti.f32)
            steering_norm = steering.norm()
            if steering_norm > 1e-6:
                desired_vel = steering * (self.max_speed / steering_norm)
                steering = desired_vel - self.vel[i]
                steering_norm = steering.norm()
                if steering_norm > self.max_force:
                    steering *= (self.max_force / steering_norm)
        return steering

    @ti.func
    def alignment(self, i: ti.i32) -> ti.types.vector(3, ti.f32):
        steering = ti.Vector([0.0, 0.0, 0.0])
        count = 0
        perception_sq = self.perception_radius ** 2
        
        for j in range(self.N):
            if i != j and self.active[j] == 1:
                dist_sq = (self.pos[i] - self.pos[j]).norm_sqr()
                if dist_sq < perception_sq:
                    steering += self.vel[j]
                    count += 1
        
        if count > 0:
            steering /= ti.cast(count, ti.f32)
            steering_norm = steering.norm()
            if steering_norm > 1e-6:
                desired_vel = steering * (self.max_speed / steering_norm)
                steering = desired_vel - self.vel[i]
                steering_norm = steering.norm()
                if steering_norm > self.max_force:
                    steering *= (self.max_force / steering_norm)
        return steering

    @ti.func
    def cohesion(self, i: ti.i32) -> ti.types.vector(3, ti.f32):
        steering = ti.Vector([0.0, 0.0, 0.0])
        count = 0
        perception_sq = self.perception_radius ** 2
        
        for j in range(self.N):
            if i != j and self.active[j] == 1:
                dist_sq = (self.pos[i] - self.pos[j]).norm_sqr()
                if dist_sq < perception_sq:
                    steering += self.pos[j]
                    count += 1
        
        if count > 0:
            steering /= ti.cast(count, ti.f32)
            desired = steering - self.pos[i]
            desired_norm = desired.norm()
            if desired_norm > 1e-6:
                desired *= (self.max_speed / desired_norm)
                steering = desired - self.vel[i]
                steering_norm = steering.norm()
                if steering_norm > self.max_force:
                    steering *= (self.max_force / steering_norm)
        return steering
    
    @ti.kernel
    def _update_mode(self, mode: ti.i32):
        if mode == 0:
            self.separation_modifier[None] = 2.0
            self.alignment_modifier[None] = 2.0
            self.cohesion_modifier[None] = 1.0
            self.target_weight[None] = 2
        elif mode == 1:
            self.separation_modifier[None] = 3.0
            self.alignment_modifier[None] = 0.2
            self.cohesion_modifier[None] = 0.2
            self.target_weight[None] = 0.6
        elif mode == 2:
            self.separation_modifier[None] = 0.5
            self.alignment_modifier[None] = 1.0
            self.cohesion_modifier[None] = 0.5
            self.target_weight[None] = 0.7
    
    def update_mode(self, mode: DroneModes):
        self.mode = mode
        mode_map = {DroneModes.ATTACK: 0, DroneModes.SPREAD: 1, DroneModes.PATROL: 2}
        self._update_mode(mode_map[mode])

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
            
            boundary_force = self.max_force * 5.0
            margin = 10.0
            boundary_max = self.boundary - margin
            boundary_min = -self.boundary + margin
            inv_margin = 1.0 / margin
            
            pos = self.pos[i]
            
            if pos.x > boundary_max:
                self.acc[i].x -= boundary_force * (pos.x - boundary_max) * inv_margin
            elif pos.x < boundary_min:
                self.acc[i].x += boundary_force * (boundary_min - pos.x) * inv_margin
            
            if pos.y > boundary_max:
                self.acc[i].y -= boundary_force * (pos.y - boundary_max) * inv_margin
            elif pos.y < boundary_min:
                self.acc[i].y += boundary_force * (boundary_min - pos.y) * inv_margin
            
            if pos.z > boundary_max:
                self.acc[i].z -= boundary_force * (pos.z - boundary_max) * inv_margin
            elif pos.z < margin:
                self.acc[i].z += boundary_force * (margin - pos.z) * inv_margin
            
            self.pos[i].x = ti.math.clamp(pos.x, -self.boundary, self.boundary)
            self.pos[i].y = ti.math.clamp(pos.y, -self.boundary, self.boundary)
            self.pos[i].z = ti.math.clamp(pos.z, 0.0, self.boundary)
            
            if pos.x != self.pos[i].x:
                self.vel[i].x = 0.0
            if pos.y != self.pos[i].y:
                self.vel[i].y = 0.0
            if pos.z != self.pos[i].z:
                self.vel[i].z = 0.0
            
            direction = target_pos[0] - self.pos[i]
            dir_norm = direction.norm()
            if dir_norm > 1e-6:
                self.acc[i] += direction * (self.target_weight[None] / dir_norm)

            self.vel[i] += self.acc[i] * dt
            
            vel_norm = self.vel[i].norm()
            if vel_norm > self.max_speed:
                self.vel[i] *= (self.max_speed / vel_norm)
            
            self.pos[i] += self.vel[i] * dt
            
            if self.cooldown[i] > 0.0:
                self.cooldown[i] -= dt
            
            # Batched health check to reduce kernel launches
            if self.health[i] <= 0.0:
                self.active[i] = 0
                self.pos[i] = ti.Vector([-10000.0, 0.0, 0.0])

    @ti.kernel
    def shoot(self, enemy_pos: ti.template(), enemy_count: ti.i32, enemy_health: ti.template()):
        shoot_range_sq = self.shoot_range * self.shoot_range
        
        for i in range(self.N):
            if self.active[i] == 0 or self.cooldown[i] > 0.0:
                continue
            
            min_dist_sq = 1e20
            target_idx = -1
            
            for j in range(enemy_count):
                if enemy_health[j] <= 0.0:
                    continue
                diff = self.pos[i] - enemy_pos[j]
                dist_sq = diff.norm_sqr()
                if dist_sq < shoot_range_sq and dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    target_idx = j
            
            if target_idx >= 0 and self.projectile_free_count[None] > 0:
                free_idx = ti.atomic_sub(self.projectile_free_count[None], 1) - 1
                if free_idx >= 0:
                    p = self.projectile_free_list[free_idx]
                    direction = enemy_pos[target_idx] - self.pos[i]
                    inv_dist = ti.rsqrt(min_dist_sq)
                    self.projectile_pos[p] = self.pos[i]
                    self.projectile_vel[p] = direction * (inv_dist * self.projectile_speed)
                    self.projectile_active[p] = 1
                    self.projectile_lifetime[p] = self.projectile_max_lifetime
                    self.cooldown[i] = self.shoot_cooldown

    @ti.kernel
    def update_projectiles(self, dt: ti.f32):
        # Optimized batched projectile update
        for i in range(self.max_projectiles):
            if self.projectile_active[i] == 0:
                continue
            
            # Update position and lifetime in one go
            self.projectile_pos[i] += self.projectile_vel[i] * dt
            self.projectile_lifetime[i] -= dt
            
            # Batched boundary and lifetime checks
            pos = self.projectile_pos[i]
            should_deactivate = (
                self.projectile_lifetime[i] <= 0.0 or
                pos.x > self.boundary or pos.x < -self.boundary or
                pos.y > self.boundary or pos.y < -self.boundary or
                pos.z > self.boundary or pos.z < 0.0
            )
            
            if should_deactivate:
                self.projectile_active[i] = 0
                self.projectile_pos[i] = ti.Vector([0.0, 0.0, -10000.0])
                free_idx = ti.atomic_add(self.projectile_free_count[None], 1)
                self.projectile_free_list[free_idx] = i

    @ti.kernel
    def check_hits(self, enemy_pos: ti.template(), enemy_count: ti.i32, enemy_health: ti.template()):
        hit_radius_sq = self.hit_radius * self.hit_radius
        
        for i in range(self.max_projectiles):
            if self.projectile_active[i] == 0:
                continue
            
            for j in range(enemy_count):
                if enemy_health[j] <= 0.0:
                    continue
                
                diff = self.projectile_pos[i] - enemy_pos[j]
                dist_sq = diff.norm_sqr()
                if dist_sq < hit_radius_sq:
                    self.projectile_active[i] = 0
                    self.projectile_pos[i] = ti.Vector([0.0, 0.0, -10000.0])
                    ti.atomic_add(enemy_health[j], -self.projectile_damage)
                    free_idx = ti.atomic_add(self.projectile_free_count[None], 1)
                    self.projectile_free_list[free_idx] = i
                    break
    
    @ti.kernel
    def update_health(self):
        # Deprecated: Health checking now integrated into main update loop
        # Kept for backwards compatibility
        for i in range(self.N):
            if self.health[i] <= 0.0:
                self.active[i] = 0
                self.pos[i] = ti.Vector([-10000.0, 0.0, 0.0])
    
    @ti.kernel
    def compute_range_circles(self):
        for i in range(self.N):
            if self.active[i] == 0:
                continue
            
            for seg in ti.static(range(self.segments_per_circle)):
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
    
    @ti.kernel
    def _compute_swarm_center(self):
        total_x = 0.0
        total_y = 0.0
        total_z = 0.0
        count = 0
        
        for i in range(self.N):
            if self.active[i] == 1:
                total_x += self.pos[i][0]
                total_y += self.pos[i][1]
                total_z += self.pos[i][2]
                count += 1
        
        if count > 0:
            inv_count = 1.0 / ti.cast(count, ti.f32)
            self.center_x[None] = total_x * inv_count
            self.center_y[None] = total_y * inv_count
            self.center_z[None] = total_z * inv_count
        else:
            self.center_x[None] = 0.0
            self.center_y[None] = 0.0
            self.center_z[None] = 0.0
    
    def get_swarm_center(self):
        self._compute_swarm_center()
        return [self.center_x[None], self.center_y[None], self.center_z[None]]
    
    @ti.kernel
    def get_health_ratio(self) -> float:
        total_health = 0.0
        count = 0
        
        for i in range(self.N):
            if self.active[i] == 1:
                total_health += self.health[i]
                count += 1
        
        return total_health / (ti.cast(count, ti.f32) * self.max_health)
                    
    def get_range_circles(self) -> MatrixField:
        return self.range_circles

    def get_pos_field(self) -> MatrixField:
        return self.pos
    
    def get_projectile_pos_field(self) -> MatrixField:
        return self.projectile_pos
    
    def get_projectile_active_field(self) -> Field:
        return self.projectile_active    
    @ti.kernel
    def batched_combat_update(self, dt: ti.f32, enemy_pos: ti.template(), enemy_count: ti.i32, enemy_health: ti.template()):
        shoot_range_sq = self.shoot_range * self.shoot_range
        hit_radius_sq = self.hit_radius * self.hit_radius
        
        for i in range(self.N):
            if self.active[i] == 0 or self.cooldown[i] > 0.0:
                continue
            
            min_dist_sq = 1e20
            target_idx = -1
            
            for j in range(enemy_count):
                if enemy_health[j] <= 0.0:
                    continue
                diff = self.pos[i] - enemy_pos[j]
                dist_sq = diff.norm_sqr()
                if dist_sq < shoot_range_sq and dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    target_idx = j
            
            if target_idx >= 0 and self.projectile_free_count[None] > 0:
                free_idx = ti.atomic_sub(self.projectile_free_count[None], 1) - 1
                if free_idx >= 0:
                    p = self.projectile_free_list[free_idx]
                    direction = enemy_pos[target_idx] - self.pos[i]
                    inv_dist = ti.rsqrt(min_dist_sq)
                    self.projectile_pos[p] = self.pos[i]
                    self.projectile_vel[p] = direction * (inv_dist * self.projectile_speed)
                    self.projectile_active[p] = 1
                    self.projectile_lifetime[p] = self.projectile_max_lifetime
                    self.cooldown[i] = self.shoot_cooldown
        
        for i in range(self.max_projectiles):
            if self.projectile_active[i] == 0:
                continue
            
            self.projectile_pos[i] += self.projectile_vel[i] * dt
            self.projectile_lifetime[i] -= dt
            
            pos = self.projectile_pos[i]
            should_deactivate = (
                self.projectile_lifetime[i] <= 0.0 or
                pos.x > self.boundary or pos.x < -self.boundary or
                pos.y > self.boundary or pos.y < -self.boundary or
                pos.z > self.boundary or pos.z < 0.0
            )
            
            if should_deactivate:
                self.projectile_active[i] = 0
                self.projectile_pos[i] = ti.Vector([0.0, 0.0, -10000.0])
                free_idx = ti.atomic_add(self.projectile_free_count[None], 1)
                self.projectile_free_list[free_idx] = i
                continue
            
            for j in range(enemy_count):
                if enemy_health[j] <= 0.0:
                    continue
                
                diff = self.projectile_pos[i] - enemy_pos[j]
                dist_sq = diff.norm_sqr()
                if dist_sq < hit_radius_sq:
                    self.projectile_active[i] = 0
                    self.projectile_pos[i] = ti.Vector([0.0, 0.0, -10000.0])
                    ti.atomic_add(enemy_health[j], -self.projectile_damage)
                    free_idx = ti.atomic_add(self.projectile_free_count[None], 1)
                    self.projectile_free_list[free_idx] = i
                    break