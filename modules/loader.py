import os
from datetime import datetime

class FileManager:
    def create_config(self, config: dict[str, tuple[tuple[float | int | tuple[float, float]], str]]) -> None:
        os.makedirs("config", exist_ok=True)
        self.file_path = f"config/scenario_config_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        with open(self.file_path, 'w') as f:
            for key, (value, description) in config.items():
                f.write(f"{key}: {value}  # {description}\n")
                
                
    def load_config(self) -> dict[str, float | int | tuple[float, float]]:
        config: dict[str, float | int | tuple[float, float]] = {}
        with open(self.file_path, 'r') as f:
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