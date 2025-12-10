from enum import Enum
import taichi as ti
import random

from taichi import Vector, Field, MatrixField, data_oriented, func
from taichi.types import vector, f32, i32

class DroneModes(str, Enum):
    ATTACK = "attack"
    SPREAD = "spread"
    PATROL = "patrol"


@data_oriented
class DroneSwarm:
    max_speed: float = 15.0
    max_force: float = 0.5
    perception_radius: float = 40.0
    height: float = 50.0
    mode: DroneModes = DroneModes.SPREAD
    
    
    def __init__(self, count: int, boundary_size: float) -> None:
        self.N: int = count
        self.boundary: float = boundary_size
        
        self.pos: MatrixField = Vector.field(3, dtype=f32, shape=self.N)
        self.vel: MatrixField = Vector.field(3, dtype=f32, shape=self.N)
        self.acc: MatrixField = Vector.field(3, dtype=f32, shape=self.N)
        
        self.active: Field = ti.field(dtype=ti.i32, shape=self.N)
        
        # Modifiers as Taichi fields
        self.separation_modifier = ti.field(dtype=ti.f32, shape=())
        self.alignment_modifier = ti.field(dtype=ti.f32, shape=())
        self.cohesion_modifier = ti.field(dtype=ti.f32, shape=())
        self.target_weight = ti.field(dtype=ti.f32, shape=())
        
        # Initialize default values
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
            self.alignment_modifier[None] = 0.1
            self.cohesion_modifier[None] = 0.1
            self.target_weight[None] = 0.2
        elif self.mode == DroneModes.PATROL:
            self.separation_modifier[None] = 2
            self.alignment_modifier[None] = 2.0
            self.cohesion_modifier[None] = 3.0
            self.target_weight[None] = 1.0

    @ti.kernel
    def update(self, dt: ti.f32, target_pos: ti.types.vector(2, ti.f32)):
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
            target_3d = ti.Vector([target_pos.x, target_pos.y, self.pos[i].z])
            direction = (target_3d - self.pos[i]).normalized()
            self.acc[i] += direction * self.target_weight[None]

            # Physics integration
            self.vel[i] += self.acc[i] * dt
            
            vel_norm = self.vel[i].norm()
            if vel_norm > self.max_speed:
                self.vel[i] = self.vel[i].normalized() * self.max_speed
            
            self.pos[i] += self.vel[i] * dt

    def get_pos_field(self) -> MatrixField:
        return self.pos
        