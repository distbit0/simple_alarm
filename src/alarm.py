import sys
from utils import getAbsPath
from subprocess import run
import sounddevice as sd
import soundfile as sf
import argparse
import time
import re
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import simpledialog
from load_dotenv import load_dotenv

load_dotenv()


alarmFile = Path(getAbsPath("../alarm.wav"))


class Timer:
    def __init__(self):
        self.pause_file = Path(getAbsPath('../tmp/.timer_pause'))
        self.kill_file = Path(getAbsPath('../tmp/.timer_kill'))
        self.out_file = Path(getAbsPath('../tmp/OUT.txt'))  # Use absolute path

    def parse_time(self, time_str: str) -> int:
        """Convert time string (e.g., '1h30m') to seconds"""
        if not time_str:
            return 0
            
        total_seconds = 0
        pattern = r'(\d+)([hms])'
        matches = re.findall(pattern, time_str.lower())
        
        for value, unit in matches:
            if unit == 'h':
                total_seconds += int(value) * 3600
            elif unit == 'm':
                total_seconds += int(value) * 60
            elif unit == 's':
                total_seconds += int(value)
                
        return total_seconds

    def play_alarm(self):
        """Play alarm sound and show notification"""
        # Show notification (works on most Linux systems)
        try:
            run(['notify-send', 'Timer', 'Time is up!'])
        except (FileNotFoundError, ImportError) as e:
            print(f"Notification failed: {e}", flush=True)
        
        for i in range(5):
            try:
                data, fs = sf.read(alarmFile)
                sd.play(data * 0.2, fs)  # multiply data by value between 0 and 1 for volume
                sd.wait()
                time.sleep(0.3)  # Short pause between beeps for reliability
            except Exception as e:
                print(f"Failed to play alarm sound: {e}", flush=True)

    def start(self, seconds: int):
        """Start a new timer with dynamic remaining time calculation"""
        # Check if kill flag exists and remove it
        if self.kill_file.exists():
            self.kill_file.unlink()
            
        start_time = datetime.now()
        total_paused_duration = 0
        end_time = start_time + timedelta(seconds=seconds)
        pause_time = 0

        while True:
            current_time = datetime.now()
            if self.pause_file.exists() and pause_time == 0:
                pause_time = pickle.load(open(self.pause_file, 'rb'))
                print("Timer paused")
            if not self.pause_file.exists() and pause_time != 0:
                pause_duration = current_time - pause_time
                total_paused_duration += pause_duration.total_seconds()
                pause_time = 0
                print("Timer resumed")

            if pause_time:
                current_time = pause_time
            remaining = end_time.timestamp() - current_time.timestamp() + total_paused_duration

            if remaining <= 0:
                try:
                    with open(self.out_file, 'w') as f:
                        f.write("")
                except Exception as e:
                    print(f"Failed to clear output file: {e}", flush=True)
                self.play_alarm()
                break
        
            if self.kill_file.exists():
                break
                
            time_str = self.format_time(remaining)
            prefix = "[PAUSE] " if self.pause_file.exists() else ""
            try:
                with open(self.out_file, 'w') as f:
                    f.write(f"{prefix}{time_str}")
            except Exception as e:
                print(f"Failed to write to output file: {e}", flush=True)
            time.sleep(0.25)
        sys.exit(0)

    def toggle_pause(self):
        """Toggle pause state of the timer"""

        if not self.pause_file.exists():
            pause_time = datetime.now()
            try:
                with open(self.pause_file, 'wb') as f:
                    pickle.dump(pause_time, f)
                print("Timer paused")
            except Exception as e:
                print(f"Failed to pause timer: {e}", flush=True)
        else:
            try:
                self.pause_file.unlink()
            except FileNotFoundError:
                pass
            print("Timer resumed")

    def format_time(self, seconds):
        """Format seconds into HH:MM:SS"""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def is_timer_running(self):
        """Check if a timer is currently running by checking output file"""
        if self.out_file.exists():
            try:
                with open(self.out_file, 'r') as f:
                    content = f.read().strip()
                    return bool(content and ':' in content)
            except Exception:
                pass
        return False

def main():
    parser = argparse.ArgumentParser(description='Command line timer application')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--pause', '-p', action='store_true', help='Pause/unpause current timer')

    args = parser.parse_args()
    timer = Timer()

    if args.pause:
        timer.toggle_pause()
    else:
        time_input = simpledialog.askstring(
            "Timer Input",
            "Enter timer duration (e.g., '1h30m20s', '45m10s', '30s'):"
        )
        
        if time_input:
            seconds = timer.parse_time(time_input)
            if seconds > 0:
                if timer.is_timer_running():
                    print("Timer already running. Creating kill flag to stop it...")
                    with open(timer.kill_file, 'w') as f:
                        f.write('')
                    time.sleep(1)  # Give existing timer time to quit
                timer.start(seconds)
            else:
                print("Invalid time format. Use format like '1h30m20s', '45m10s' or '30s'")
        else:
            print("Timer cancelled")

if __name__ == "__main__":
    main()
