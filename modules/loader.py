from typing import Union, Optional
import os
from datetime import datetime
from tkinter.filedialog import askopenfilename

class FileManager:
    def create_config(self, config: dict[str, tuple[tuple[float | int | tuple[float, float]], str]]) -> None:
        os.makedirs("scenario", exist_ok=True)
        self.file_path = f"scenario/scenario_config_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        with open(self.file_path, 'w') as f:
            for key, (value, description) in config.items():
                f.write(f"{key}: {value}  # {description}\n")
                
    def load_config(self) -> Optional[dict[str, Union[float, int, list[tuple[float, float]]]]]:
        config = {}
        try:
            path = askopenfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")], title="Select a scenario file")
            if not path:
                return None
        except Exception as e:
            return None
        
        with open(path, 'r') as f:
            for line in f:
                if line.strip() == '' or line.strip().startswith('#'):
                    continue
                key_value = line.split(':', 1)
                if len(key_value) != 2:
                    continue
                key = key_value[0].strip()
                value_str = key_value[1].split('#')[0].strip()
                
                try:
                    if value_str.startswith('[') and value_str.endswith(']'):
                        value = eval(value_str)
                    elif '.' in value_str:
                        value = float(value_str)
                    else:
                        value = int(value_str)
                    config[key] = value
                except Exception as e:
                    print(f"Error parsing line: {line}. Error: {e}")
        return config