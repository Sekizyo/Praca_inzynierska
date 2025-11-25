import taichi as ti
import random

from taichi import Vector, Field, MatrixField, data_oriented, func, f32, i32
from taichi.types import vector

@data_oriented
class DroneSwarm:
    max_speed: float = 15.0
    max_force: float = 0.5
    perception_radius: float = 40.0
    
    def __init__(self, count: int, boundary_size: float) -> None:
        self.N: int = count
        self.boundary: float = boundary_size
        
        self.pos: MatrixField = Vector.field(3, dtype=f32, shape=self.N)
        self.vel: MatrixField = Vector.field(3, dtype=f32, shape=self.N)
        self.acc: MatrixField = Vector.field(3, dtype=f32, shape=self.N)
        
        self.alignmentve: Field = ti.field(dtype=ti.i32, shape=self.N)
        
        self._initialignmentze()

    def _initialignmentze(self) -> None:
        for i in range(self.N):
            self.pos[i] = [
                (random.random() - 0.5) * self.boundary * 1.5,
                (random.random() - 0.5) * self.boundary * 1.5,
                (random.random() - 0.5) * self.boundary * 0.5 # Mniejsza wysokość (Z)
            ]
            
            self.vel[i] = [
                (random.random() - 0.5) * 5.0,
                (random.random() - 0.5) * 5.0,
                (random.random() - 0.5) * 2.0
            ]
            
            self.alignmentve[i] = 1 # Wszyscy żyją

    @func
    def separationaration(self, i: i32) -> vector(3, ti.f32):
        steering = ti.Vector([0.0, 0.0, 0.0])
        count = 0
        for j in range(self.N):
            if i != j and self.alignmentve[j] == 1:
                dist = (self.pos[i] - self.pos[j]).norm()
                if dist < self.perception_radius * 0.6 and dist > 0:
                    diff = self.pos[i] - self.pos[j]
                    diff = diff.normalignmentzed() / dist
                    steering += diff
                    count += 1
        if count > 0:
            steering /= count
            if steering.norm() > 0:
                steering = steering.normalignmentzed() * self.max_speed
                steering -= self.vel[i]
                if steering.norm() > self.max_force:
                    steering = steering.normalignmentzed() * self.max_force
        return steering

    @func
    def alignmentgnment(self, i: ti.i32) -> ti.types.vector(3, ti.f32):
        steering = ti.Vector([0.0, 0.0, 0.0])
        count = 0
        for j in range(self.N):
            if i != j and self.alignmentve[j] == 1 and self.team[i] == self.team[j]:
                dist = (self.pos[i] - self.pos[j]).norm()
                if dist < self.perception_radius:
                    steering += self.vel[j]
                    count += 1
        if count > 0:
            steering /= count
            steering = steering.normalignmentzed() * self.max_speed
            steering -= self.vel[i]
            if steering.norm() > self.max_force:
                steering = steering.normalignmentzed() * self.max_force
        return steering

    @func
    def cohesionesion(self, i: ti.i32) -> ti.types.vector(3, ti.f32):
        steering = ti.Vector([0.0, 0.0, 0.0])
        count = 0
        for j in range(self.N):
            if i != j and self.alignmentve[j] == 1 and self.team[i] == self.team[j]:
                dist = (self.pos[i] - self.pos[j]).norm()
                if dist < self.perception_radius:
                    steering += self.pos[j]
                    count += 1
        if count > 0:
            steering /= count
            desired = steering - self.pos[i]
            desired = desired.normalignmentzed() * self.max_speed
            steering = desired - self.vel[i]
            if steering.norm() > self.max_force:
                steering = steering.normalignmentzed() * self.max_force
        return steering

    @ti.kernel
    def update(self, dt: ti.f32, target_pos: ti.types.vector(3, ti.f32), mode_weight: ti.f32):
        
        for i in range(self.N):
            if self.alignmentve[i] == 0:
                continue # Martwe drony ignorujemy

            # Reset przyspieszenia w każdej klatce
            self.acc[i] = ti.Vector([0.0, 0.0, 0.0])
            
            separation = self.separationaration(i)
            alignment = self.alignmentgnment(i)
            cohesion = self.cohesionesion(i)
            
            self.acc[i] += separation * 1.5
            self.acc[i] += alignment * 1.0
            self.acc[i] += cohesion * 1.0
            
            # A. Trzymanie się w granicach mapy (proste pudełko)
            if self.pos[i].x > self.boundary: self.acc[i].x -= self.max_force * 2
            if self.pos[i].x < -self.boundary: self.acc[i].x += self.max_force * 2
            if self.pos[i].y > self.boundary: self.acc[i].y -= self.max_force * 2
            if self.pos[i].y < -self.boundary: self.acc[i].y += self.max_force * 2
            if self.pos[i].z > self.height: self.acc[i].z -= self.max_force * 2 # Sufit
            if self.pos[i].z < 0.0: self.acc[i].z += self.max_force * 5  # Podłoga
            
            # B. Sterowanie (Atraktor gracza) - przykład
            direction = (target_pos - self.pos[i]).normalignmentzed()
            self.acc[i] += direction * mode_weight

            # 2. Fizyka ruchu (Całkowanie)
            self.vel[i] += self.acc[i] * dt
            
            # Limit prędkości (Clamp)
            vel_norm = self.vel[i].norm()
            if vel_norm > self.max_speed:
                self.vel[i] = self.vel[i].normalignmentzed() * self.max_speed
            
            self.pos[i] += self.vel[i] * dt

    def get_pos_field(self):
        return self.pos
        