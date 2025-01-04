import win32gui
import keyboard
import time
import random
from threading import Thread, Event
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from pynput.keyboard import Controller
import json
import os




#timmer för hur

# Standardkonfiguration som kan ändras
DEFAULT_CONFIG = {
    "movements": [
        {"key": "a", "duration": 0.3, "description": "Kort sväng vänster"},
        {"key": "d", "duration": 0.3, "description": "Kort sväng höger"}
    ],
    "delay_between_moves": {
        "min": 2.0,  # Längre delay mellan svängar
        "max": 4.0
    },
    "moves_per_cycle": {
        "min": 1,
        "max": 2
    },
    "pause_key": "insert",
    "exit_key": "end"
}
#
class AFKBot:
    def __init__(self):
        self.console = Console()
        self.pause_event = Event()
        self.kb = Controller()
        self.config = self.load_config()
        self.running = True  # För att hålla koll på om W är intryckt
        self.w_pressed = False  # Ny variabel för att hålla koll på W-status
        self.last_window_check = 0 
        self.window_check_interval = 0.5  # Hur ofta vi kollar fönstret (sekunder)
        
    def load_config(self):
        """Ladda eller skapa konfigurationsfil"""
        config_path = "afk_config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except:
                self.console.print("[yellow]Kunde inte ladda config, använder standard[/yellow]")
                return DEFAULT_CONFIG
        else:
            # Skapa ny configfil med standardvärden
            with open(config_path, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            return DEFAULT_CONFIG

    def save_config(self):
        """Spara nuvarande konfiguration"""
        with open("afk_config.json", 'w') as f:
            json.dump(self.config, f, indent=4)

    def edit_config(self):
        """Låt användaren ändra konfigurationen"""
        self.console.print("\n[cyan]Current configuration:[/cyan]")
        for i, move in enumerate(self.config["movements"]):
            self.console.print(f"{i+1}. Key: {move['key']}, Duration: {move['duration']}s - {move['description']}")
        
        self.console.print("\n[yellow]Edit configuration? (y/n)[/yellow]")
        if input().lower() == 'y':
            self.config["movements"] = []
            while True:
                self.console.print("\nAdd movement (or press enter to finish):")
                key = input("Key (w/a/s/d/shift/space): ").strip()
                if not key:
                    break
                try:
                    duration = float(input("Duration (seconds): "))
                    desc = input("Description: ")
                    self.config["movements"].append({
                        "key": key,
                        "duration": duration,
                        "description": desc
                    })
                except ValueError:
                    self.console.print("[red]Invalid input, skipping[/red]")
            
            self.save_config()
            self.console.print("[green]Configuration saved![/green]")

    def start_running(self):
        """Börja springa och håll W intryckt"""
        if not self.w_pressed:  # Bara om W inte redan är intryckt
            self.kb.press('w')
            self.w_pressed = True
        self.running = True
        
    def stop_running(self):
        """Sluta springa och släpp W"""
        if self.w_pressed:  # Bara om W är intryckt
            self.kb.release('w')
            self.w_pressed = False
        self.running = False

    def safe_movement(self):
        """Utför svängar medan W hålls intryckt"""
        if not self.w_pressed:  # Se till att W är intryckt
            self.start_running()
        
        # Gör svängen
        move = random.choice(self.config["movements"])
        key = move["key"]
        duration = move["duration"]
        
        self.kb.press(key)
        time.sleep(duration)
        self.kb.release(key)

    def is_fortnite_window(self):
        """Kontrollera om Fortnite-fönstret är aktivt"""
        try:
            current_time = time.time()
            if current_time - self.last_window_check < self.window_check_interval:
                return True
                
            self.last_window_check = current_time
            active_window = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(active_window)
            return "fortnite" in window_title.lower()
        except:
            return False

    def run(self):
        """Huvudloop med fönsterkontroll"""
        self.console.print("[bold green]Starting AFK bot...[/bold green]")
        self.console.print(f"[cyan]Press {self.config['pause_key'].upper()} to pause/resume[/cyan]")
        self.console.print(f"[cyan]Press {self.config['exit_key'].upper()} to exit[/cyan]")
        self.console.print("[yellow]Bot will only run when Fortnite window is active![/yellow]")
        
        def check_pause_key():
            while True:
                if keyboard.is_pressed(self.config['pause_key']):
                    if self.pause_event.is_set():
                        self.pause_event.clear()
                        self.start_running()  # Återuppta springandet
                        self.console.print("[green]Bot resumed![/green]")
                    else:
                        self.pause_event.set()
                        self.stop_running()  # Sluta springa
                        self.console.print("[yellow]Bot paused![/yellow]")
                    time.sleep(0.3)
                time.sleep(0.1)

        pause_thread = Thread(target=check_pause_key, daemon=True)
        pause_thread.start()

        try:
            while True:
                if keyboard.is_pressed(self.config['exit_key']):
                    break

                if not self.pause_event.is_set():
                    # Kontrollera om Fortnite är aktivt fönster
                    if not self.is_fortnite_window():
                        if self.w_pressed:  # Släpp W om vi tappar fokus
                            self.stop_running()
                        self.console.print("[yellow]Waiting for Fortnite window...[/yellow]")
                        time.sleep(1)
                        continue


                        
                    # Se till att W är intryckt när vi har rätt fönster
                    if not self.w_pressed:
                        self.start_running()
                        
                    # Gör random svängar
                    self.safe_movement()
                    time.sleep(random.uniform(
                        self.config["delay_between_moves"]["min"],
                        self.config["delay_between_moves"]["max"]
                    ))
                
                time.sleep(0.1)

        except KeyboardInterrupt:
            pass
        finally:
            self.console.print("[red]Stopping bot...[/red]")
            self.stop_running()  # Släpp W
            # Släpp andra tangenter
            for move in self.config["movements"]:
                self.kb.release(move["key"])

if __name__ == "__main__":
    bot = AFKBot()
    bot.edit_config()  # Låt användaren ändra inställningar innan start
    bot.run()

