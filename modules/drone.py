import math

import taichi as ti

from taichi import Vector, Field, MatrixField, data_oriented
from taichi.types import f32
from modules.constants import DroneModes
from modules.gui_utils import GamePresets

@data_oriented
class DroneSwarm:
    def __init__(self, params: GamePresets, team: int) -> None:
        self.params = params
        
        self.team: int = team
        if self.team == 0:
            self.N: int = params.attacking_drone_count
            self.path = params.attacking_path_normalized
        else:
            self.N: int = params.defending_drone_count
            self.path = params.ai_path_normalized
            
        self.boundary: float = params.map_size
        
        self.max_speed: float = params.drone_max_speed
        self.max_force: float = 0.5
        self.perception_radius: float = params.drone_perception_radius
        self.shooting_perception_radius: float = params.drone_shooting_perception_radius
        self.projectile_speed: float = params.projectile_speed
        self.shoot_range: float = params.drone_shooting_range
        self.shoot_cooldown: float = params.drone_shooting_cooldown
        self.hit_radius: float = params.drone_hit_radius
        self.max_health: float =  params.drone_max_health
        self.projectile_damage: float = params.projectile_damage
        self.projectile_max_lifetime: float = params.projectile_max_lifetime
        self.projectile_radius: float = params.projectile_radius
        
        self.mode: DroneModes = DroneModes.ATTACK
        
        self.pos: MatrixField = Vector.field(3, dtype=f32, shape=self.N)
        self.vel: MatrixField = Vector.field(3, dtype=f32, shape=self.N)
        self.acc: MatrixField = Vector.field(3, dtype=f32, shape=self.N)
        
        self.active: MatrixField = Vector.field(1, dtype=ti.i32, shape=self.N)
        self.health: MatrixField = Vector.field(1, dtype=ti.f32, shape=self.N)
        self.cooldown: MatrixField = Vector.field(1, dtype=ti.f32, shape=self.N)
        
        self.max_projectiles: int = self.N * 2
        self.projectile_pos: MatrixField = Vector.field(3, dtype=f32, shape=self.max_projectiles)
        self.projectile_vel: MatrixField = Vector.field(3, dtype=f32, shape=self.max_projectiles)
        self.projectile_active: Field = ti.field(dtype=ti.i32, shape=self.max_projectiles)
        self.projectile_lifetime: Field = ti.field(dtype=ti.f32, shape=self.max_projectiles)
        
        self.projectile_free_list: Field = ti.field(dtype=ti.i32, shape=self.max_projectiles)
        self.projectile_free_count: Field = ti.field(dtype=ti.i32, shape=())
        
        self.separation_modifier = ti.field(dtype=ti.f32, shape=())
        self.alignment_modifier = ti.field(dtype=ti.f32, shape=())
        self.cohesion_modifier = ti.field(dtype=ti.f32, shape=())
        self.target_weight = ti.field(dtype=ti.f32, shape=())
        
        self.center_x = ti.field(dtype=ti.f32, shape=())
        self.center_y = ti.field(dtype=ti.f32, shape=())
        self.center_z = ti.field(dtype=ti.f32, shape=())
        self.alive_count_cache = ti.field(dtype=ti.i32, shape=())
        self.target = ti.Vector.field(3, dtype=ti.f32, shape=1)
        self.current_waypoint: int = 0
        
        # [Alive Count, Center X, Center Y, Center Z]
        self.stats = ti.field(dtype=ti.f32, shape=4)
        self.cached_stats = [0.0, 0.0, 0.0, 0.0]
        
        self.total_damage = ti.field(dtype=ti.f32, shape=())
        self.death_count = ti.field(dtype=ti.i32, shape=())
        
        self._initialize()

    @ti.kernel
    def _initialize(self):
        self.separation_modifier[None] = 5.0
        self.alignment_modifier[None] = 0.1
        self.cohesion_modifier[None] = 0.1
        self.target_weight[None] = 0.5
        self.total_damage[None] = 0.0
        self.death_count[None] = 0
        
        
        for i in range(self.N):
            if self.team == 0:
                self.pos[i] = ti.Vector([
                    -ti.random() * self.boundary,
                    -ti.random() * self.boundary * 1.5,
                    ti.random() * self.boundary * 1.5
                ])
            else:
                self.pos[i] = ti.Vector([
                    ti.random() * self.boundary ,
                    ti.random() * self.boundary,
                    ti.random() * self.boundary * 1.5
                ])
            
            self.vel[i] = ti.Vector([
                (ti.random() - 0.5) * 5.0,
                (ti.random() - 0.5) * 5.0,
                (ti.random() - 0.5) * 2.0
            ])
            
            self.active[i] = 1
            self.health[i] = self.max_health
            self.cooldown[i] = 0.0
            
        
        for i in range(self.max_projectiles):
            self.projectile_pos[i] = ti.Vector([0.0, 0.0, -10000.0])
            self.projectile_active[i] = 0
            self.projectile_lifetime[i] = 0.0
            self.projectile_free_list[i] = i
        
        self.projectile_free_count[None] = self.max_projectiles
            
    @ti.kernel
    def update_statistics(self):
        total_x = 0.0
        total_y = 0.0
        total_z = 0.0
        count = 0
        
        
        for i in range(self.N):
            if self.active[i][0] == 1:
                total_x += self.pos[i][0]
                total_y += self.pos[i][1]
                total_z += self.pos[i][2]
                count += 1
        
        self.alive_count_cache[None] = count
        self.stats[0] = ti.cast(count, ti.f32)
        
        if count > 0:
            inv_count = 1.0 / ti.cast(count, ti.f32)
            cx = total_x * inv_count
            cy = total_y * inv_count
            cz = total_z * inv_count
            
            self.center_x[None] = cx
            self.center_y[None] = cy
            self.center_z[None] = cz
            
            self.stats[1] = cx
            self.stats[2] = cy
            self.stats[3] = cz
        else:
            self.center_x[None] = 0.0
            self.center_y[None] = 0.0
            self.center_z[None] = 0.0
            
            self.stats[1] = 0.0
            self.stats[2] = 0.0
            self.stats[3] = 0.0
    
    @ti.func
    def calculate_flocking(self, i: ti.i32, 
                   pos_self: ti.types.vector(3, ti.f32),
                   vel_self: ti.types.vector(3, ti.f32),
                   grid_count: ti.template(), 
                   grid_buckets: ti.template(), 
                   grid_cell_size: ti.f32, 
                   grid_shape: ti.types.vector(3, ti.i32), 
                   grid_padding: ti.i32, 
                   grid_offset: ti.types.vector(3, ti.f32)) -> ti.types.vector(3, ti.f32):
        
        steer_sep = ti.Vector([0.0, 0.0, 0.0])
        steer_ali = ti.Vector([0.0, 0.0, 0.0])
        steer_coh = ti.Vector([0.0, 0.0, 0.0])
        
        count_sep = 0
        count_ali = 0
        count_coh = 0
        
        rad_sep_sq = (self.perception_radius * 0.6) ** 2
        rad_ali_sq = self.perception_radius ** 2
        
        pos_i = pos_self + grid_offset
        base_x = int(pos_i.x / grid_cell_size) + grid_padding
        base_y = int(pos_i.y / grid_cell_size) + grid_padding
        base_z = int(pos_i.z / grid_cell_size) + grid_padding
        
        
        for dx, dy, dz in ti.static(ti.ndrange((-1, 2), (-1, 2), (-1, 2))):
            gx = ti.math.clamp(base_x + dx, 0, grid_shape[0] - 1)
            gy = ti.math.clamp(base_y + dy, 0, grid_shape[1] - 1)
            gz = ti.math.clamp(base_z + dz, 0, grid_shape[2] - 1)
            
            cell_count = grid_count[gx, gy, gz]
            limit = ti.min(cell_count, grid_buckets.shape[3])
            
            for k in range(limit):
                j = grid_buckets[gx, gy, gz, k]
                
                if i != j:
                    diff = pos_self - self.pos[j]
                    dist_sq = diff.norm_sqr()
                    
                    # Separation
                    if dist_sq < rad_sep_sq and dist_sq > 1e-6:
                        steer_sep += diff / dist_sq
                        count_sep += 1
                    
                    # Alignment & Cohesion share same radius
                    if dist_sq < rad_ali_sq:
                        steer_ali += self.vel[j]
                        count_ali += 1
                        
                        steer_coh += self.pos[j]
                        count_coh += 1

        # Post-process Separation
        if count_sep > 0:
            steer_sep /= ti.cast(count_sep, ti.f32)
            sep_norm = steer_sep.norm()
            if sep_norm > 1e-6:
                steer_sep = steer_sep * (self.max_speed / sep_norm) - vel_self
                sep_norm = steer_sep.norm()
                if sep_norm > self.max_force:
                    steer_sep *= (self.max_force / sep_norm)
        
        # Post-process Alignment
        if count_ali > 0:
            steer_ali /= ti.cast(count_ali, ti.f32)
            ali_norm = steer_ali.norm()
            if ali_norm > 1e-6:
                steer_ali = steer_ali * (self.max_speed / ali_norm) - vel_self
                ali_norm = steer_ali.norm()
                if ali_norm > self.max_force:
                    steer_ali *= (self.max_force / ali_norm)
        
        # Post-process Cohesion
        if count_coh > 0:
            steer_coh /= ti.cast(count_coh, ti.f32)
            desired = steer_coh - pos_self
            desired_norm = desired.norm()
            if desired_norm > 1e-6:
                desired *= (self.max_speed / desired_norm)
                steer_coh = desired - vel_self
                coh_norm = steer_coh.norm()
                if coh_norm > self.max_force:
                    steer_coh *= (self.max_force / coh_norm)
        
        return (steer_sep * self.separation_modifier[None] + 
                steer_ali * self.alignment_modifier[None] + 
                steer_coh * self.cohesion_modifier[None])

    @ti.kernel
    def _update_mode(self, mode: int):
        if mode == 0:
            self.separation_modifier[None] = self.params.boids_attack_separation
            self.alignment_modifier[None] = self.params.boids_attack_alignment
            self.cohesion_modifier[None] = self.params.boids_attack_cohesion
            self.target_weight[None] = self.params.boids_attack_target
        elif mode == 1:
            self.separation_modifier[None] = self.params.boids_spread_separation
            self.alignment_modifier[None] = self.params.boids_spread_alignment
            self.cohesion_modifier[None] = self.params.boids_spread_cohesion
            self.target_weight[None] = self.params.boids_spread_target
        elif mode == 2:
            self.separation_modifier[None] = self.params.boids_patrol_separation
            self.alignment_modifier[None] = self.params.boids_patrol_alignment
            self.cohesion_modifier[None] = self.params.boids_patrol_cohesion
            self.target_weight[None] = self.params.boids_patrol_target
            
    def update_mode(self, mode: DroneModes | None):
        if not mode:
            return 
        
        self.mode = mode
        mode_map = {DroneModes.ATTACK: 0, DroneModes.SPREAD: 1, DroneModes.PATROL: 2}
        self._update_mode(mode_map[mode])

    @ti.kernel
    def update(self, dt: ti.f32,
               grid_count: ti.template(), 
               grid_buckets: ti.template(), 
               grid_cell_size: ti.f32, 
               grid_shape: ti.types.vector(3, ti.i32), 
               grid_padding: ti.i32, 
               grid_offset: ti.types.vector(3, ti.f32)):
        
        target_weight_val = self.target_weight[None]
        boundary_val = self.boundary
        
        for i in range(self.N):
            if self.active[i][0] == 0:
                continue

            pos_val = self.pos[i]
            vel_val = self.vel[i]
            acc_val = ti.Vector([0.0, 0.0, 0.0])
            
            flocking_force = self.calculate_flocking(i, pos_val, vel_val, grid_count, grid_buckets, grid_cell_size, grid_shape, grid_padding, grid_offset)
            acc_val += flocking_force
            # Optimized boundary forces with fewer branches
            boundary_force = self.max_force * 5.0
            margin = 10.0
            boundary_max = boundary_val - margin
            boundary_min = -boundary_val + margin
            inv_margin = 1.0 / margin
            
            # X boundary
            if pos_val.x > boundary_max:
                acc_val.x -= boundary_force * (pos_val.x - boundary_max) * inv_margin
            elif pos_val.x < boundary_min:
                acc_val.x += boundary_force * (boundary_min - pos_val.x) * inv_margin
            
            # Y boundary  
            if pos_val.y > boundary_max:
                acc_val.y -= boundary_force * (pos_val.y - boundary_max) * inv_margin
            elif pos_val.y < boundary_min:
                acc_val.y += boundary_force * (boundary_min - pos_val.y) * inv_margin
            
            # Z boundary
            if pos_val.z > boundary_max:
                acc_val.z -= boundary_force * (pos_val.z - boundary_max) * inv_margin
            elif pos_val.z < margin:
                acc_val.z += boundary_force * (margin - pos_val.z) * inv_margin
            
            # Optimized boundary clamping with cached boundary value
            new_pos_x = ti.math.clamp(pos_val.x, -boundary_val, boundary_val)
            new_pos_y = ti.math.clamp(pos_val.y, -boundary_val, boundary_val)
            new_pos_z = ti.math.clamp(pos_val.z, 0.0, boundary_val)
            
            # Zero velocity if hitting wall (branch prediction friendly)
            if new_pos_x != pos_val.x:
                vel_val.x = 0.0
            if new_pos_y != pos_val.y:
                vel_val.y = 0.0
            if new_pos_z != pos_val.z:
                vel_val.z = 0.0
            
            pos_val = ti.Vector([new_pos_x, new_pos_y, new_pos_z])
            
            direction = self.target[0] - pos_val
            dir_norm = direction.norm()
            if dir_norm > 1e-6:
                acc_val += direction * (target_weight_val / dir_norm)

            vel_val += acc_val * dt
            
            vel_norm = vel_val.norm()
            if vel_norm > self.max_speed:
                vel_val *= (self.max_speed / vel_norm)
            
            pos_val += vel_val * dt
            
            # Write back to global memory
            self.pos[i] = pos_val
            self.vel[i] = vel_val
            self.acc[i] = acc_val
            
            # Update cooldown
            cooldown_val = self.cooldown[i][0]
            if cooldown_val > 0.0:
                self.cooldown[i][0] = cooldown_val - dt
            
            if self.health[i][0] <= 0.0:
                self.active[i] = 0
                self.pos[i] = ti.Vector([-10000.0, 0.0, 0.0])
                ti.atomic_add(self.death_count[None], 1)
    
    @ti.kernel
    def batched_combat_update(self, dt: ti.f32, 
                              enemy_pos: ti.template(), 
                              enemy_count: ti.i32, 
                              enemy_health: ti.template(),
                              grid_count: ti.template(),
                              grid_buckets: ti.template(),
                              grid_offset: ti.types.vector(3, ti.f32),
                              grid_shape: ti.types.vector(3, ti.i32),
                              grid_cell_size: ti.f32,
                              grid_padding: ti.i32):
        # Cache constants to reduce field access
        shoot_range_sq = self.shoot_range * self.shoot_range
        hit_radius_sq = self.hit_radius * self.hit_radius
        boundary_val = self.boundary
        projectile_speed_val = self.projectile_speed
        fov_cosine_val = self.shooting_perception_radius
        
        # Shooting phase 
        for i in range(self.N):
            if self.active[i][0] == 0 or self.cooldown[i][0] > 0.0:
                continue
            
            min_dist_sq = 1e20
            target_idx = -1
            
            # Grid lookup for shooting
            local_pos_i = self.pos[i]
            local_vel_i = self.vel[i]
            vel_sq = local_vel_i.norm_sqr()
            
            pos_i = local_pos_i + grid_offset
            base_x = int(pos_i.x / grid_cell_size) + grid_padding
            base_y = int(pos_i.y / grid_cell_size) + grid_padding
            base_z = int(pos_i.z / grid_cell_size) + grid_padding
            
            for dx in ti.static(range(-1, 2)):
                for dy in ti.static(range(-1, 2)):
                    for dz in ti.static(range(-1, 2)):
                        gx = ti.math.clamp(base_x + dx, 0, grid_shape[0] - 1)
                        gy = ti.math.clamp(base_y + dy, 0, grid_shape[1] - 1)
                        gz = ti.math.clamp(base_z + dz, 0, grid_shape[2] - 1)
                        
                        cell_count = grid_count[gx, gy, gz]
                        limit = ti.min(cell_count, grid_buckets.shape[3])
                        
                        for k in range(limit):
                            j = grid_buckets[gx, gy, gz, k]
                            
                            vec_to_enemy = enemy_pos[j] - local_pos_i
                            dist_sq = vec_to_enemy.norm_sqr()
                            
                            if dist_sq < shoot_range_sq and dist_sq < min_dist_sq:
                                is_in_fov = True
                                if vel_sq > 0.1:
                                    dot_prod = local_vel_i.dot(vec_to_enemy)
                                    denom = ti.sqrt(vel_sq * dist_sq)
                                    if dot_prod < fov_cosine_val * denom:
                                        is_in_fov = False
                                
                                if is_in_fov:
                                    min_dist_sq = dist_sq
                                    target_idx = j
            
            if target_idx >= 0 and self.projectile_free_count[None] > 0:
                free_idx = ti.atomic_sub(self.projectile_free_count[None], 1) - 1
                if free_idx >= 0:
                    p = self.projectile_free_list[free_idx]
                    direction = enemy_pos[target_idx] - local_pos_i
                    inv_dist = ti.rsqrt(min_dist_sq)
                    self.projectile_pos[p] = local_pos_i
                    self.projectile_vel[p] = direction * (inv_dist * projectile_speed_val)
                    self.projectile_active[p] = 1
                    self.projectile_lifetime[p] = self.projectile_max_lifetime
                    self.cooldown[i] = self.shoot_cooldown
        
        # Projectile update phase
        for i in range(self.max_projectiles):
            if self.projectile_active[i] == 0:
                continue
            
            # Cache projectile data
            proj_pos = self.projectile_pos[i]
            proj_vel = self.projectile_vel[i]
            proj_lifetime = self.projectile_lifetime[i]
            
            # Update position and lifetime
            proj_pos += proj_vel * dt
            proj_lifetime -= dt
            
            # Optimized boundary check
            should_deactivate = (
                proj_lifetime <= 0.0 or
                proj_pos.x > boundary_val or proj_pos.x < -boundary_val or
                proj_pos.y > boundary_val or proj_pos.y < -boundary_val or
                proj_pos.z > boundary_val or proj_pos.z < 0.0
            )
            
            if should_deactivate:
                self.projectile_active[i] = 0
                self.projectile_pos[i] = ti.Vector([0.0, 0.0, -10000.0])
                free_idx = ti.atomic_add(self.projectile_free_count[None], 1)
                self.projectile_free_list[free_idx] = i
                continue
            
            # Write back updated values
            self.projectile_pos[i] = proj_pos
            self.projectile_lifetime[i] = proj_lifetime
            
            # Grid lookup for hit detection - optimized with early exit
            pos_p = proj_pos + grid_offset
            base_x = int(pos_p.x / grid_cell_size) + grid_padding
            base_y = int(pos_p.y / grid_cell_size) + grid_padding
            base_z = int(pos_p.z / grid_cell_size) + grid_padding
            
            hit_detected = 0
            
            for dx in ti.static(range(-1, 2)):
                for dy in ti.static(range(-1, 2)):
                    for dz in ti.static(range(-1, 2)):
                        if hit_detected == 0:
                            gx = ti.math.clamp(base_x + dx, 0, grid_shape[0] - 1)
                            gy = ti.math.clamp(base_y + dy, 0, grid_shape[1] - 1)
                            gz = ti.math.clamp(base_z + dz, 0, grid_shape[2] - 1)
                            
                            cell_count = grid_count[gx, gy, gz]
                            limit = ti.min(cell_count, grid_buckets.shape[3])
                            
                            for k in range(limit):
                                j = grid_buckets[gx, gy, gz, k]
                                
                                if enemy_health[j][0] > 0.0:
                                    diff = proj_pos - enemy_pos[j]
                                    dist_sq = diff.norm_sqr()
                                    if dist_sq < hit_radius_sq:
                                        self.projectile_active[i] = 0
                                        self.projectile_pos[i] = ti.Vector([0.0, 0.0, -10000.0])
                                        ti.atomic_add(enemy_health[j][0], -self.projectile_damage)
                                        ti.atomic_add(self.total_damage[None], self.projectile_damage)
                                        free_idx = ti.atomic_add(self.projectile_free_count[None], 1)
                                        self.projectile_free_list[free_idx] = i
                                        hit_detected = 1
                                        break
                                    
    def follow_path(self):
        current_target = self.path[self.current_waypoint]
        self.set_target(current_target[0], current_target[1], current_target[2])
        self.update_mode(current_target[3])
        
        swarm_center = self.get_swarm_center()
        dist = math.sqrt(
            (swarm_center[0] - current_target[0])**2 +
            (swarm_center[1] - current_target[1])**2 +
            (swarm_center[2] - current_target[2])**2
        )
        
        if dist < self.params.map_size * 0.5:
            self.current_waypoint = (self.current_waypoint + 1) % len(self.path)
            
    def set_target(self, x: float, y: float, z: float):
        self.target[0] = ti.Vector([x, y, z])
    
    def get_stats(self):
        self.cached_stats = self.stats.to_numpy()
        
    def get_target_position(self):
        return self.target
    
    def get_mode(self) -> DroneModes:   
        return self.mode
    
    def get_swarm_center(self):
        return [self.center_x[None], self.center_y[None], self.center_z[None]]
                    
    def get_pos_field(self) -> MatrixField:
        return self.pos
    
    def get_projectile_pos_field(self) -> MatrixField:
        return self.projectile_pos
    
    def get_projectile_active_field(self) -> Field:
        return self.projectile_active

    def get_alive_count(self) -> int:
        return int(self.cached_stats[0])