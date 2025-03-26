# This file is included as a placeholder based on the provided development guidelines.
# For this specific application, we're not using database models, but keeping this file
# to maintain consistency with the suggested structure.

class Transaction:
    """
    Class to represent a bank transaction.
    While not a database model, this provides structure for our transaction data.
    """
    def __init__(self, date=None, description=None, amount=None, balance=None):
        self.date = date
        self.description = description
        self.amount = amount
        self.balance = balance
    
    def __repr__(self):
        return f"Transaction({self.date}, {self.description}, {self.amount}, {self.balance})"
