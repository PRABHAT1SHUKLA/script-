class Transaction:
    """Context manager simulating database transactions"""
    def __init__(self, db_name):
        self.db_name = db_name
        self.changes = []
    
    def __enter__(self):
        print(f"  BEGIN TRANSACTION on {self.db_name}")
        return self
    
    def execute(self, query):
        self.changes.append(query)
        print(f"  EXECUTE: {query}")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            print(f"  COMMIT: {len(self.changes)} changes")
        else:
            print(f"  ROLLBACK: Error occurred - {exc_val}")
            return True  # Suppress exception

print("3. CONTEXT MANAGER - TRANSACTION")
with Transaction("users_db") as tx:
    tx.execute("INSERT INTO users VALUES (1, 'Alice')")
    tx.execute("UPDATE users SET name='Bob' WHERE id=1")
print()

