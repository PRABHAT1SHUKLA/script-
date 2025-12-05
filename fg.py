"""
Advanced Personal Finance Analyzer
Demonstrates: OOP, Decorators, Context Managers, Type Hints, Data Classes,
Exception Handling, Collections, Generators, File I/O, and more.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Union
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from functools import wraps
from enum import Enum
import json
import csv
from pathlib import Path
import statistics
from abc import ABC, abstractmethod


class TransactionType(Enum):
    """Enum for transaction types"""
    INCOME = "income"
    EXPENSE = "expense"
    INVESTMENT = "investment"
    TRANSFER = "transfer"


class Category(Enum):
    """Enum for expense/income categories"""
    SALARY = "salary"
    FOOD = "food"
    TRANSPORT = "transport"
    ENTERTAINMENT = "entertainment"
    UTILITIES = "utilities"
    HEALTHCARE = "healthcare"
    INVESTMENT_RETURN = "investment_return"
    OTHER = "other"


def validate_positive(func: Callable) -> Callable:
    """Decorator to validate that amount is positive"""
    @wraps(func)
    def wrapper(self, amount: float, *args, **kwargs):
        if amount <= 0:
            raise ValueError(f"Amount must be positive, got {amount}")
        return func(self, amount, *args, **kwargs)
    return wrapper


def log_transaction(func: Callable) -> Callable:
    """Decorator to log transactions"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        print(f"[LOG] Transaction executed: {func.__name__}")
        return result
    return wrapper


class InsufficientFundsError(Exception):
    """Custom exception for insufficient funds"""
    pass


@dataclass
class Transaction:
    """Data class representing a financial transaction"""
    date: datetime
    amount: float
    transaction_type: TransactionType
    category: Category
    description: str
    transaction_id: str = field(default_factory=lambda: str(datetime.now().timestamp()))
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert transaction to dictionary"""
        return {
            'date': self.date.isoformat(),
            'amount': self.amount,
            'type': self.transaction_type.value,
            'category': self.category.value,
            'description': self.description,
            'id': self.transaction_id,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Transaction':
        """Create transaction from dictionary"""
        return cls(
            date=datetime.fromisoformat(data['date']),
            amount=data['amount'],
            transaction_type=TransactionType(data['type']),
            category=Category(data['category']),
            description=data['description'],
            transaction_id=data['id'],
            tags=data.get('tags', [])
        )


class Account(ABC):
    """Abstract base class for financial accounts"""
    
    def __init__(self, name: str, initial_balance: float = 0.0):
        self._name = name
        self._balance = initial_balance
        self._transactions: List[Transaction] = []
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def balance(self) -> float:
        return self._balance
    
    @abstractmethod
    def apply_interest(self) -> None:
        """Apply interest to account (implementation varies by account type)"""
        pass
    
    @validate_positive
    @log_transaction
    def deposit(self, amount: float, category: Category, description: str) -> None:
        """Deposit money into account"""
        self._balance += amount
        transaction = Transaction(
            date=datetime.now(),
            amount=amount,
            transaction_type=TransactionType.INCOME,
            category=category,
            description=description
        )
        self._transactions.append(transaction)
    
    @validate_positive
    @log_transaction
    def withdraw(self, amount: float, category: Category, description: str) -> None:
        """Withdraw money from account"""
        if amount > self._balance:
            raise InsufficientFundsError(
                f"Insufficient funds: tried to withdraw {amount}, balance is {self._balance}"
            )
        self._balance -= amount
        transaction = Transaction(
            date=datetime.now(),
            amount=amount,
            transaction_type=TransactionType.EXPENSE,
            category=category,
            description=description
        )
        self._transactions.append(transaction)
    
    def get_transactions(self, 
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None,
                        category: Optional[Category] = None) -> List[Transaction]:
        """Filter transactions by date and/or category"""
        filtered = self._transactions
        
        if start_date:
            filtered = [t for t in filtered if t.date >= start_date]
        if end_date:
            filtered = [t for t in filtered if t.date <= end_date]
        if category:
            filtered = [t for t in filtered if t.category == category]
        
        return filtered
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self._name}', balance={self._balance:.2f})"


class SavingsAccount(Account):
    """Savings account with interest rate"""
    
    def __init__(self, name: str, initial_balance: float = 0.0, interest_rate: float = 0.02):
        super().__init__(name, initial_balance)
        self.interest_rate = interest_rate
    
    def apply_interest(self) -> None:
        """Apply annual interest to balance"""
        interest = self._balance * self.interest_rate
        self._balance += interest
        print(f"Interest applied: ${interest:.2f}")


class CheckingAccount(Account):
    """Checking account with no interest"""
    
    def apply_interest(self) -> None:
        """Checking accounts don't earn interest"""
        pass


class InvestmentAccount(Account):
    """Investment account with variable returns"""
    
    def __init__(self, name: str, initial_balance: float = 0.0):
        super().__init__(name, initial_balance)
        self.portfolio: Dict[str, float] = {}
    
    def buy_asset(self, asset_name: str, amount: float) -> None:
        """Buy investment asset"""
        if amount > self._balance:
            raise InsufficientFundsError("Not enough funds to buy asset")
        
        self._balance -= amount
        self.portfolio[asset_name] = self.portfolio.get(asset_name, 0) + amount
        
        transaction = Transaction(
            date=datetime.now(),
            amount=amount,
            transaction_type=TransactionType.INVESTMENT,
            category=Category.OTHER,
            description=f"Bought {asset_name}",
            tags=['investment', asset_name]
        )
        self._transactions.append(transaction)
    
    def apply_interest(self) -> None:
        """Simulate investment returns"""
        returns = sum(self.portfolio.values()) * 0.07
        self._balance += returns
        print(f"Investment returns: ${returns:.2f}")


class FinanceManager:
    """Main class to manage multiple accounts and provide analytics"""
    
    def __init__(self, owner: str):
        self.owner = owner
        self.accounts: Dict[str, Account] = {}
        self._budget: Dict[Category, float] = {}
    
    def add_account(self, account: Account) -> None:
        """Add an account to the manager"""
        self.accounts[account.name] = account
    
    def set_budget(self, category: Category, amount: float) -> None:
        """Set budget limit for a category"""
        self._budget[category] = amount
    
    def get_total_balance(self) -> float:
        """Calculate total balance across all accounts"""
        return sum(account.balance for account in self.accounts.values())
    
    def get_net_worth(self) -> float:
        """Calculate net worth (simplified, same as total balance here)"""
        return self.get_total_balance()
    
    def get_spending_by_category(self, days: int = 30) -> Dict[Category, float]:
        """Get spending breakdown by category for last N days"""
        start_date = datetime.now() - timedelta(days=days)
        spending = defaultdict(float)
        
        for account in self.accounts.values():
            transactions = account.get_transactions(start_date=start_date)
            for transaction in transactions:
                if transaction.transaction_type == TransactionType.EXPENSE:
                    spending[transaction.category] += transaction.amount
        
        return dict(spending)
    
    def check_budget_status(self, days: int = 30) -> Dict[Category, Dict[str, float]]:
        """Check if spending is within budget"""
        spending = self.get_spending_by_category(days)
        status = {}
        
        for category, budget in self._budget.items():
            spent = spending.get(category, 0)
            status[category] = {
                'budget': budget,
                'spent': spent,
                'remaining': budget - spent,
                'percentage': (spent / budget * 100) if budget > 0 else 0
            }
        
        return status
    
    def get_monthly_summary(self) -> Dict[str, Union[float, Dict]]:
        """Get comprehensive monthly financial summary"""
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        total_income = 0
        total_expenses = 0
        
        for account in self.accounts.values():
            transactions = account.get_transactions(start_date=thirty_days_ago)
            for transaction in transactions:
                if transaction.transaction_type == TransactionType.INCOME:
                    total_income += transaction.amount
                elif transaction.transaction_type == TransactionType.EXPENSE:
                    total_expenses += transaction.amount
        
        return {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_savings': total_income - total_expenses,
            'savings_rate': (total_income - total_expenses) / total_income * 100 if total_income > 0 else 0,
            'spending_by_category': self.get_spending_by_category(30),
            'net_worth': self.get_net_worth()
        }
    
    def transaction_generator(self, account_name: str):
        """Generator that yields transactions one by one"""
        if account_name not in self.accounts:
            raise ValueError(f"Account '{account_name}' not found")
        
        for transaction in self.accounts[account_name]._transactions:
            yield transaction
    
    def export_to_json(self, filepath: str) -> None:
        """Export all data to JSON file"""
        data = {
            'owner': self.owner,
            'export_date': datetime.now().isoformat(),
            'accounts': {}
        }
        
        for name, account in self.accounts.items():
            data['accounts'][name] = {
                'type': account.__class__.__name__,
                'balance': account.balance,
                'transactions': [t.to_dict() for t in account._transactions]
            }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Data exported to {filepath}")
    
    def export_to_csv(self, filepath: str) -> None:
        """Export transactions to CSV file"""
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Account', 'Type', 'Category', 'Amount', 'Description'])
            
            for account_name, account in self.accounts.items():
                for transaction in account._transactions:
                    writer.writerow([
                        transaction.date.strftime('%Y-%m-%d %H:%M:%S'),
                        account_name,
                        transaction.transaction_type.value,
                        transaction.category.value,
                        transaction.amount,
                        transaction.description
                    ])
        
        print(f"Transactions exported to {filepath}")
    
    def __enter__(self):
        """Context manager entry"""
        print(f"Starting finance session for {self.owner}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        print(f"Ending finance session. Total net worth: ${self.get_net_worth():.2f}")
        return False


def demo_usage():
    """Demonstrate the usage of the finance analyzer"""
    
    print("=" * 60)
    print("ADVANCED PERSONAL FINANCE ANALYZER DEMO")
    print("=" * 60)
    
    with FinanceManager("John Doe") as manager:
        
        checking = CheckingAccount("Main Checking", initial_balance=5000)
        savings = SavingsAccount("Emergency
