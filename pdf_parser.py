import pdfplumber
import logging
import os
import re
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BankStatementParser:

    def __init__(self):
        self.account_data = {
            'bank_name': 'Punjab and Sind Bank',
            'branch': 'Jalandhar SME',
            'account_number': '',
            'account_name': '',
            'address': '',
            'opening_date': '',
            'sanction_limit': '',
            'interest_rate': '',
            'statement_period': '',
            'transactions': []
        }

    def parse_pdf(self, pdf_path: str) -> Dict:
        """
        Parse the PDF and extract account information and transactions.

        Args:
            pdf_path (str): Path to the PDF file

        Returns:
            dict: Dictionary containing account details and transactions
        """
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"

            self._extract_account_info(text)
            self.account_data['transactions'] = self._extract_transactions(
                text)

            logger.info(
                f"Successfully parsed account statement for {self.account_data['account_name']}"
            )
            return self.account_data

        except Exception as e:
            logger.error(f"Error parsing PDF: {str(e)}")
            raise

    def _extract_account_info(self, text: str) -> None:
        """Extract account information from the text."""
        # Extract account number
        acct_match = re.search(r'Account No\s*:\s*(\d+)', text)
        if acct_match:
            self.account_data['account_number'] = acct_match.group(1)

        # Extract account name
        name_match = re.search(r'A/C Name\s*:\s*(M/S[^\n]+)', text)
        if name_match:
            self.account_data['account_name'] = name_match.group(1).strip()

        # Extract address
        addr_match = re.search(r'Address\s*:\s*([^\n]+)\s*City', text,
                               re.DOTALL)
        if addr_match:
            self.account_data['address'] = addr_match.group(1).strip()

        # Extract opening date
        open_match = re.search(r'Open Date\s*:\s*([^\n]+)', text)
        if open_match:
            self.account_data['opening_date'] = open_match.group(1).strip()

        # Extract sanction limit
        limit_match = re.search(r'Sanction Limit\s*:\s*([^\n]+)', text)
        if limit_match:
            self.account_data['sanction_limit'] = limit_match.group(1).strip()

        # Extract interest rate
        rate_match = re.search(r'Interest Rate\s*:\s*([^\n]+)', text)
        if rate_match:
            self.account_data['interest_rate'] = rate_match.group(1).strip()

        # Extract statement period
        period_match = re.search(
            r'Statement of account for the period of\s*([^\n]+)', text)
        if period_match:
            self.account_data['statement_period'] = period_match.group(
                1).strip()

    def _extract_transactions(self, text: str) -> List[Dict]:
        """
        Extract transactions from the bank statement text.

        Args:
            text (str): Text extracted from the PDF

        Returns:
            list: List of dictionaries containing transaction details
        """
        transactions = []
        lines = text.split('\n')

        # Find the start of transactions
        start_idx = 0
        for i, line in enumerate(lines):
            if "Statement of account for the period of" in line:
                start_idx = i + 1
                break

        # Process each transaction line
        for line in lines[start_idx:]:
            line = line.strip()
            if not line:
                continue

            # Skip non-transaction lines
            if (line.startswith(
                ("Grand Total:", "Please examine", "***END OF STATEMENT***",
                 "NOTE:", "REPORT!MAILID#")) or "Page No:" in line):
                continue

            # Check for transaction line (starts with date)
            date_match = self._match_date(line)
            if date_match:
                transaction = self._parse_transaction_line(line, date_match)
                if transaction:
                    transactions.append(transaction)

        return transactions

    def _match_date(self, line: str) -> Optional[re.Match]:
        """Match date patterns at the start of a line."""
        date_patterns = [
            r'^(\d{2}-[A-Za-z]{3}-\d{4})',  # DD-MMM-YYYY
            r'^(\d{2}/\d{2}/\d{4})',  # DD/MM/YYYY
            r'^(\d{2}-[A-Za-z]{3}-\d{2})',  # DD-MMM-YY
            r'^(\d{2}-[A-Za-z]{3}-\d{4})'  # DD-MMM-YYYY (duplicate pattern for priority)
        ]

        for pattern in date_patterns:
            match = re.match(pattern, line)
            if match:
                return match
        return None

    def _parse_transaction_line(self, line: str,
                                date_match: re.Match) -> Optional[Dict]:
        """Parse a single transaction line."""
        date = date_match.group(1)
        remaining = line[date_match.end():].strip()

        # Split transaction components
        parts = re.split(r'\s{2,}', remaining)  # Split by multiple spaces

        if len(parts) >= 3:
            # Format: Description | Amount | Balance
            description, amount, balance = parts[0], parts[1], parts[2]
        elif len(parts) == 2:
            # Format: Description | Amount
            description, amount = parts[0], parts[1]
            balance = "N/A"
        else:
            # Unusual format
            description = remaining
            amount = balance = "N/A"

        # Clean and validate amounts
        amount = self._clean_amount(amount)
        balance = self._clean_balance(balance)

        if amount == "N/A" and balance == "N/A":
            # Skip lines that don't contain financial data
            return None

        return {
            'date': date,
            'description': description,
            'amount': amount,
            'balance': balance,
            'type': self._get_transaction_type(balance)
        }

    def _clean_amount(self, amount: str) -> str:
        """Clean and validate amount string."""
        if amount == "N/A":
            return amount

        # Remove commas and currency symbols
        cleaned = re.sub(r'[^\d.]', '', amount)

        # Validate numeric format
        if not re.match(r'^\d+\.?\d{0,2}$', cleaned):
            return "N/A"

        return cleaned

    def _clean_balance(self, balance: str) -> str:
        """Clean and validate balance string."""
        if balance == "N/A":
            return balance

        # Extract Dr/Cr indicator
        dr_cr = ""
        if 'Dr' in balance:
            dr_cr = "Dr"
        elif 'Cr' in balance:
            dr_cr = "Cr"

        # Remove non-numeric characters except decimal point
        cleaned = re.sub(r'[^\d.]', '', balance)

        # Validate numeric format
        if not re.match(r'^\d+\.?\d{0,2}$', cleaned):
            return "N/A"

        return f"{cleaned} {dr_cr}" if dr_cr else cleaned

    def _get_transaction_type(self, balance: str) -> str:
        """Determine if transaction is debit or credit."""
        if 'Dr' in balance:
            return 'Debit'
        elif 'Cr' in balance:
            return 'Credit'
        return 'N/A'

    def save_to_csv(self, output_file: str) -> None:
        """
        Save the transaction data to a CSV file.

        Args:
            output_file (str): Path to the output CSV file
        """
        import csv

        try:
            with open(output_file, 'w', newline='',
                      encoding='utf-8') as csvfile:
                fieldnames = [
                    'date', 'description', 'amount', 'balance', 'type'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for transaction in self.account_data['transactions']:
                    writer.writerow(transaction)

            logger.info(f"Transaction data saved to {output_file}")
        except Exception as e:
            logger.error(f"Error saving to CSV: {str(e)}")
            raise


def main():
    # Initialize parser
    parser = BankStatementParser()

    # Input PDF file path
    pdf_path = "test3 (1).pdf"

    try:
        # Parse the PDF
        account_data = parser.parse_pdf(pdf_path)

        # Print summary
        print("\nAccount Summary:")
        print("----------------")
        print(f"Account Number: {account_data['account_number']}")
        print(f"Account Name: {account_data['account_name']}")
        print(f"Statement Period: {account_data['statement_period']}")
        print(f"Total Transactions: {len(account_data['transactions'])}")

        # Print sample transactions
        print("\nSample Transactions:")
        print("-------------------")
        for i, tx in enumerate(account_data['transactions'][:5]):
            print(
                f"{i+1}. {tx['date']} | {tx['description'][:30]}... | {tx['amount']} | {tx['balance']} | {tx['type']}"
            )

        # Save to CSV
        csv_path = "transactions.csv"
        parser.save_to_csv(csv_path)
        print(f"\nTransactions saved to {csv_path}")

    except Exception as e:
        print(f"\nError processing PDF: {str(e)}")


if __name__ == "__main__":
    main()
