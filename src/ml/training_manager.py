import threading
from typing import Dict, Any, List, Optional
import time

class TrainingManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TrainingManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.is_training = False
        self.progress = 0
        self.status = "idle"
        self.logs: List[str] = []
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.start_time: Optional[float] = None
        self._initialized = True

    def start_training(self):
        self.is_training = True
        self.progress = 0
        self.status = "starting"
        self.logs = []
        self.result = None
        self.error = None
        self.start_time = time.time()

    def update_progress(self, progress: int, status: str = None, log: str = None):
        self.progress = progress
        if status:
            self.status = status
        if log:
            self.logs.append(f"[{time.strftime('%H:%M:%S')}] {log}")

    def complete_training(self, result: Dict[str, Any]):
        self.is_training = False
        self.progress = 100
        self.status = "completed"
        self.result = result
        duration = time.time() - self.start_time if self.start_time else 0
        self.logs.append(f"[{time.strftime('%H:%M:%S')}] Training completed in {duration:.2f}s")

    def fail_training(self, error: str):
        self.is_training = False
        self.status = "failed"
        self.error = error
        self.logs.append(f"[{time.strftime('%H:%M:%S')}] Error: {error}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_training": self.is_training,
            "progress": self.progress,
            "status": self.status,
            "logs": self.logs[-50:],  # Return last 50 logs
            "result": self.result,
            "error": self.error,
            "duration": time.time() - self.start_time if self.start_time and self.is_training else 0
        }

training_manager = TrainingManager()
