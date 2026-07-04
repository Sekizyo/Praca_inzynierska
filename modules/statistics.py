import os
import csv
from datetime import datetime
import multiprocessing
import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
from tkinter import filedialog, simpledialog

def run_plot_process(history: dict) -> None:
    try:
        plt.style.use('dark_background')
        
        fig, axs = plt.subplots(2, 2, figsize=(14, 10))
        if fig is None: return None
        fig.canvas.manager.set_window_title('Mission Analysis')
        
        axs[0, 0].plot(history['time'], history['player_count'], label='Attacking', color='salmon')
        axs[0, 0].plot(history['time'], history['enemy_count'], label='Defending', color='lightgreen')
        axs[0, 0].set_title('Drone Population')
        axs[0, 0].set_ylabel('Count')
        axs[0, 0].legend()
        axs[0, 0].grid(True, alpha=0.3)
        
        axs[0, 1].plot(history['time'], history['territory'], label='Attacking Control', color='salmon')
        axs[0, 1].fill_between(history['time'], history['territory'], alpha=0.2, color='lightgreen')
        axs[0, 1].axhline(y=50, color='gray', linestyle='--', alpha=0.5)
        axs[0, 1].set_title('Territory Control (%)')
        axs[0, 1].set_ylim(0, 100)
        axs[0, 1].grid(True, alpha=0.3)
        
        axs[1, 0].plot(history['time'], history['damage_p'], label='Attacking Dmg', color='salmon')
        axs[1, 0].plot(history['time'], history['damage_e'], label='Defending Dmg', color='lightgreen')
        axs[1, 0].set_title('Total Damage Dealt (Cumulative)')
        axs[1, 0].set_ylabel('Damage')
        axs[1, 0].legend()
        axs[1, 0].grid(True, alpha=0.3)
        
        if 'kd_ratio' in history:
            axs[1, 1].plot(history['time'], history['kd_ratio'], label='Attacking K/D', color='gold')
            axs[1, 1].axhline(y=1.0, color='white', linestyle='--', label='Even (1.0)')
            axs[1, 1].set_title('Kill / Death Ratio')
            axs[1, 1].set_xlabel('Time (s)')
            axs[1, 1].legend()
            axs[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    except Exception as e:
        raise 

def run_positions_plot_from_data(data: dict, frame: int, map_size: int) -> None:
    try:
        plt.style.use('dark_background')
        fig = plt.figure(figsize=(10, 8))
        fig.canvas.manager.set_window_title(f'Spatial Analysis - Frame {frame}')
        ax = fig.add_subplot(111, projection='3d')
        
        if len(data['attacking']) > 0:
            att_arr = np.array(data['attacking'])
            ax.scatter(att_arr[:, 0], att_arr[:, 1], att_arr[:, 2], 
                       c='green', marker='^', label='Attacking Drones', s=10)
        
        if len(data['defending']) > 0:
            def_arr = np.array(data['defending'])
            ax.scatter(def_arr[:, 0], def_arr[:, 1], def_arr[:, 2], 
                       c='red', marker='v', label='Defending Drones', s=10)
            
        ax.set_xlim([0, map_size])
        ax.set_ylim([0, map_size])
        ax.set_zlim([0, map_size])
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.set_title(f'Drone Formations at Frame {frame}')
        ax.legend()
        
        plt.tight_layout()
        plt.show()
    except Exception as e:
        raise

def run_positions_plot(positions_data: dict, map_size: int) -> None:
    try:
        if not positions_data:
            return
            
        last_frame = sorted(positions_data.keys())[-1]
        data = positions_data[last_frame]
        run_positions_plot_from_data(data, last_frame, map_size)
    except Exception as e:
        raise

def load_and_plot_positions_process(map_size: int):
    root = tk.Tk()
    root.withdraw()
    
    file_path = filedialog.askopenfilename(
        title="Select Positions CSV",
        filetypes=[("CSV files", "*.csv")]
    )
    
    if not file_path:
        return
        
    frame_str = simpledialog.askstring("Input", "Enter frame number to visualize:")
    if not frame_str or not frame_str.isdigit():
        return
        
    target_frame = int(frame_str)
    
    attacking = []
    defending = []
    
    try:
        with open(file_path, mode='r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if int(row["Frame"]) == target_frame:
                    pt = [float(row["X"]), float(row["Y"]), float(row["Z"])]
                    if row["Team"] == "Player":
                        attacking.append(pt)
                    elif row["Team"] == "Enemy":
                        defending.append(pt)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return
        
    if not attacking and not defending:
        print(f"No data found for frame {target_frame}")
        return
        
    data = {
        "attacking": attacking,
        "defending": defending
    }
    
    run_positions_plot_from_data(data, target_frame, map_size)

class StatisticsLogger:
    def __init__(self):
        self.stats_history = {
            "frame": [],
            "time": [],
            "player_count": [],
            "enemy_count": [],
            "territory": [],
            "damage_p": [], 
            "damage_e": [], 
            "deaths_p": [],
            "deaths_e": [],
            "kd_ratio": []  
        }
        self.positions_history = {}

    def record(self, frame: int, current_t: float, p_count: int, e_count: int, territory: float, 
               p_dmg: float, e_dmg: float, p_deaths: int, e_deaths: int, kd: float):
        self.stats_history["frame"].append(frame)
        self.stats_history["time"].append(current_t)
        self.stats_history["player_count"].append(p_count)
        self.stats_history["enemy_count"].append(e_count)
        self.stats_history["territory"].append(territory)
        self.stats_history["damage_p"].append(p_dmg)
        self.stats_history["damage_e"].append(e_dmg)
        self.stats_history["deaths_p"].append(p_deaths)
        self.stats_history["deaths_e"].append(e_deaths)
        self.stats_history["kd_ratio"].append(kd)
        
    def record_positions(self, frame: int, attacking_positions: np.ndarray, defending_positions: np.ndarray):
        self.positions_history[frame] = {
            "attacking": attacking_positions.tolist(),
            "defending": defending_positions.tolist()
        }
        
    def save_to_csv(self):
        """Dumps all collected memory stats into a CSV file."""
        if not self.stats_history["time"]:
            return 
            
        os.makedirs("stats", exist_ok=True)
        filename = f"stats/stats_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        
        with open(filename, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Frame", "TimeElapsed", "AttackingCount", "DefendingCount", 
                "TerritoryControl", "DamageAttacking", "DamageDefending", 
                "DeathsAttacking", "DeathsDefending", "KDRatio"
            ])
            
            # Write all rows
            for i in range(len(self.stats_history["time"])):
                writer.writerow([
                    self.stats_history["frame"][i],
                    f"{self.stats_history['time'][i]:.3f}",
                    self.stats_history["player_count"][i],
                    self.stats_history["enemy_count"][i],
                    f"{self.stats_history['territory'][i]:.2f}",
                    f"{self.stats_history['damage_p'][i]:.2f}",
                    f"{self.stats_history['damage_e'][i]:.2f}",
                    self.stats_history["deaths_p"][i],
                    self.stats_history["deaths_e"][i],
                    f"{self.stats_history['kd_ratio'][i]:.2f}"
                ])
                
        if self.positions_history:
            pos_filename = f"stats/positions_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
            with open(pos_filename, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Frame", "Team", "X", "Y", "Z"])
                
                for frame_num, data in self.positions_history.items():
                    for pt in data["attacking"]:
                        writer.writerow([frame_num, "Attacking", f"{pt[0]:.2f}", f"{pt[1]:.2f}", f"{pt[2]:.2f}"])
                    for pt in data["defending"]:
                        writer.writerow([frame_num, "Defending", f"{pt[0]:.2f}", f"{pt[1]:.2f}", f"{pt[2]:.2f}"])
                
    def show_plot(self):
        if not self.stats_history['time']:
            return

        ctx = multiprocessing.get_context('spawn')
        p = ctx.Process(target=run_plot_process, args=(self.stats_history,))
        p.start()
        
    def show_positions_plot(self, map_size: int):
        if not self.positions_history:
            return
            
        ctx = multiprocessing.get_context('spawn')
        p = ctx.Process(target=run_positions_plot, args=(self.positions_history, map_size))
        p.start()

    @staticmethod
    def show_positions_from_file(map_size: int):
        ctx = multiprocessing.get_context('spawn')
        p = ctx.Process(target=load_and_plot_positions_process, args=(map_size,))
        p.start()