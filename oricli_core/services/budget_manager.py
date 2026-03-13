import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class BudgetManager:
    """Manages virtual compute budget for sovereign execution."""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # Default to oricli_core/data
            self.data_dir = Path(__file__).resolve().parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)
            
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.budget_file = self.data_dir / "compute_budget.json"
        self._ensure_budget_file()
        
    def _ensure_budget_file(self):
        if not self.budget_file.exists():
            default_state = {
                "balance": 100.0,
                "currency": "credits",
                "transactions": []
            }
            self._save_state(default_state)
            
    def _load_state(self) -> Dict[str, Any]:
        try:
            with open(self.budget_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load budget state: {e}")
            return {"balance": 0.0, "currency": "credits", "transactions": []}
            
    def _save_state(self, state: Dict[str, Any]):
        try:
            with open(self.budget_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save budget state: {e}")
            
    def get_balance(self) -> float:
        """Get current budget balance."""
        state = self._load_state()
        return state.get("balance", 0.0)
        
    def deduct(self, amount: float, reason: str = "compute") -> bool:
        """Deduct amount from budget. Returns True if successful, False if insufficient funds."""
        if amount <= 0:
            return True
            
        state = self._load_state()
        current_balance = state.get("balance", 0.0)
        
        if current_balance < amount:
            logger.warning(f"Insufficient budget. Have {current_balance}, need {amount} for {reason}")
            return False
            
        state["balance"] = current_balance - amount
        
        # Log transaction
        import time
        state.setdefault("transactions", []).append({
            "timestamp": time.time(),
            "type": "deduction",
            "amount": amount,
            "reason": reason,
            "balance_after": state["balance"]
        })
        
        # Keep only last 100 transactions to prevent file bloat
        if len(state["transactions"]) > 100:
            state["transactions"] = state["transactions"][-100:]
            
        self._save_state(state)
        logger.info(f"Deducted {amount} for {reason}. New balance: {state['balance']}")
        return True
        
    def add(self, amount: float, reason: str = "deposit"):
        """Add amount to budget."""
        if amount <= 0:
            return
            
        state = self._load_state()
        current_balance = state.get("balance", 0.0)
        
        state["balance"] = current_balance + amount
        
        import time
        state.setdefault("transactions", []).append({
            "timestamp": time.time(),
            "type": "deposit",
            "amount": amount,
            "reason": reason,
            "balance_after": state["balance"]
        })
        
        if len(state["transactions"]) > 100:
            state["transactions"] = state["transactions"][-100:]
            
        self._save_state(state)
        logger.info(f"Added {amount} for {reason}. New balance: {state['balance']}")
