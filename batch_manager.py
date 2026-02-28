"""
Batch Manager for factory deployment.
Handles generation of unique Batch IDs, timestamps, and metadata tracing.
"""
from datetime import datetime
import uuid
from logger import logger

class BatchManager:
    def __init__(self, operator_name: str = "AUTO_SYSTEM", machine_id: str = "SYS_01"):
        """
        Initializes a new batch manager.
        """
        self.batch_id = self._generate_batch_id()
        self.timestamp = datetime.now()
        self.operator_name = operator_name
        self.machine_id = machine_id
        self.metadata = {}
    
    def _generate_batch_id(self) -> str:
        """Generates a factory-unique batch ID (Timestamp + partial UUID)."""
        dt_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        uid_str = str(uuid.uuid4())[:8].upper()
        return f"BATCH_{dt_str}_{uid_str}"

    def set_metadata(self, key: str, value: any):
        """Attaches arbitrary tracing metadata to the batch."""
        self.metadata[key] = value

    def get_context(self) -> dict:
        """Returns the tracable context of the run."""
        return {
            "batch_id": self.batch_id,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "operator": self.operator_name,
            "machine_id": self.machine_id,
            "metadata": self.metadata
        }

    def log_context(self, message: str = "Starting batch processing"):
        """Emits a log entry describing the current batch context."""
        ctx = self.get_context()
        logger.info(f"[{self.batch_id}] {message} | Operator: {self.operator_name} | Machine: {self.machine_id}")

