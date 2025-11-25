import taichi as ti
import random

from taichi import Vector, Field, MatrixField, data_oriented, func
from taichi.types import vector, f32, i32

@data_oriented
class DroneSwarm:
    max_speed: float = 15.0
    max_force: float = 0.5
    perception_radius: float = 40.0
    height: float = 50.0
    
    def __init__(self, count: int, boundary_size: float) -> None:
        self.N: int = count
        self.boundary: float = boundary_size
        
        self.pos: MatrixField = Vector.field(3, dtype=f32, shape=self.N)
        self.vel: MatrixField = Vector.field(3, dtype=f32, shape=self.N)
        self.acc: MatrixField = Vector.field(3, dtype=f32, shape=self.N)
        
        self.active: Field = ti.field(dtype=ti.i32, shape=self.N)
        
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

    @ti.kernel
    def update(self, dt: ti.f32, target_pos: ti.types.vector(3, ti.f32), mode_weight: ti.f32):
        for i in range(self.N):
            if self.active[i] == 0:
                continue

            self.acc[i] = ti.Vector([0.0, 0.0, 0.0])
            
            sep = self.separation(i)
            ali = self.alignment(i)
            coh = self.cohesion(i)
            
            self.acc[i] += sep * 1.5
            self.acc[i] += ali * 1.0
            self.acc[i] += coh * 1.0
            
            # Boundary constraints
            if self.pos[i].x > self.boundary: self.acc[i].x -= self.max_force * 2
            if self.pos[i].x < -self.boundary: self.acc[i].x += self.max_force * 2
            if self.pos[i].y > self.boundary: self.acc[i].y -= self.max_force * 2
            if self.pos[i].y < -self.boundary: self.acc[i].y += self.max_force * 2
            if self.pos[i].z > self.height: self.acc[i].z -= self.max_force * 2
            if self.pos[i].z < 0.0: self.acc[i].z += self.max_force * 5
            
            # Steering towards target
            direction = (target_pos - self.pos[i]).normalized()
            self.acc[i] += direction * mode_weight

            # Physics integration
            self.vel[i] += self.acc[i] * dt
            
            vel_norm = self.vel[i].norm()
            if vel_norm > self.max_speed:
                self.vel[i] = self.vel[i].normalized() * self.max_speed
            
            self.pos[i] += self.vel[i] * dt

    def get_pos_field(self) -> MatrixField:
        return self.pos
        