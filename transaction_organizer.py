import os
import csv
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt

class PDFOrganizer:
    def __init__(self):
        self.transactions = []
        self.categories = {
            'DEPOSIT': ['cash', 'credit', 'deposit', 'by cash', 'by imps'],
            'WITHDRAWAL': ['withdrawal', 'debit', 'to cash', 'paid'],
            'INTEREST': ['interest', 'int.coll'],
            'CHARGES': ['charge', 'fee', 'gst', 'cgst', 'inspection'],
            'TRANSFER': ['transfer', 'trf', 'imps', 'neft', 'rtgs'],
            'OTHER': []
        }
        self.monthly_totals = defaultdict(lambda: defaultdict(float))
        self.category_totals = defaultdict(float)

    def load_transactions(self, csv_file):
        """Load transactions from CSV file generated by the parser"""
        with open(csv_file, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Convert amount to float and clean balance
                amount = float(row['amount']) if row['amount'] != 'N/A' else 0
                balance = row['balance'].split()[0] if row['balance'] != 'N/A' else '0'

                # Extract month from date
                try:
                    date_obj = datetime.strptime(row['date'], '%d-%b-%Y')
                    month_year = date_obj.strftime('%Y-%m')
                except ValueError:
                    try:
                        date_obj = datetime.strptime(row['date'], '%d/%m/%Y')
                        month_year = date_obj.strftime('%Y-%m')
                    except ValueError:
                        month_year = 'Unknown'

                # Categorize transaction
                category = self._categorize_transaction(row['description'].lower())

                # Store transaction with additional metadata
                self.transactions.append({
                    'date': row['date'],
                    'description': row['description'],
                    'amount': amount,
                    'balance': balance,
                    'type': row['type'],
                    'month_year': month_year,
                    'category': category
                })

                # Update totals
                if amount > 0:
                    self.monthly_totals[month_year][category] += amount
                    self.category_totals[category] += amount

    def _categorize_transaction(self, description):
        """Categorize transaction based on description keywords"""
        for category, keywords in self.categories.items():
            if any(keyword in description for keyword in keywords):
                return category
        return 'OTHER'

    def generate_reports(self):
        """Generate various financial reports"""
        self._generate_category_report()
        self._generate_monthly_report()
        self._generate_visualizations()

    def _generate_category_report(self):
        """Generate category-wise spending report"""
        print("\nTransaction Categories Summary:")
        print("-" * 40)
        for category, total in sorted(self.category_totals.items(), key=lambda x: x[1], reverse=True):
            print(f"{category:<15}: ₹{total:,.2f}")

    def _generate_monthly_report(self):
        """Generate monthly transaction report"""
        print("\nMonthly Transaction Totals:")
        print("-" * 40)
        for month in sorted(self.monthly_totals.keys()):
            print(f"\n{month}:")
            for category, total in sorted(self.monthly_totals[month].items(), key=lambda x: x[1], reverse=True):
                print(f"  {category:<15}: ₹{total:,.2f}")

    def _generate_visualizations(self):
        """Generate visual charts of transaction data"""
        # Category Pie Chart
        plt.figure(figsize=(12, 6))

        plt.subplot(1, 2, 1)
        labels = [k for k in self.category_totals.keys()]
        sizes = [v for v in self.category_totals.values()]
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        plt.title('Transaction Categories')

        # Monthly Trend Chart
        plt.subplot(1, 2, 2)
        months = sorted(self.monthly_totals.keys())
        categories = set(self.category_totals.keys())

        bottom_values = [0] * len(months)
        for category in categories:
            values = [self.monthly_totals[month].get(category, 0) for month in months]
            plt.bar(months, values, bottom=bottom_values, label=category)
            bottom_values = [sum(x) for x in zip(bottom_values, values)]

        plt.xticks(rotation=45)
        plt.legend()
        plt.title('Monthly Transaction Trends')

        plt.tight_layout()
        plt.savefig('transaction_analysis.png')
        print("\nSaved visualization to 'transaction_analysis.png'")

    def export_organized_data(self, output_file):
        """Export organized transaction data to CSV"""
        with open(output_file, 'w', newline='', encoding='utf-8') as file:
            fieldnames = ['date', 'description', 'amount', 'balance', 'type', 'month_year', 'category']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.transactions)
        print(f"\nOrganized data saved to {output_file}")

def main():
    # Initialize organizer
    organizer = PDFOrganizer()

    # Input CSV file from the parser
    csv_file = "transactions.csv"

    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found. Please run the PDF parser first.")
        return

    try:
        # Load and organize transactions
        organizer.load_transactions(csv_file)

        # Generate reports
        organizer.generate_reports()

        # Export organized data
        organizer.export_organized_data("organized_transactions.csv")

    except Exception as e:
        print(f"\nError processing transactions: {str(e)}")

if __name__ == "__main__":
    main()