import re
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def organize_transactions(text):
    """
    Organize transactions by account number based on statement headers.
    
    Args:
        text (str): Text extracted from the PDF
        
    Returns:
        dict: Dictionary with account numbers as keys and transaction data as values
    """
    logger.debug("Starting to organize transactions")
    
    # Dictionary to store transactions by account number
    accounts_data = defaultdict(lambda: {"statement_period": "", "transactions": [], "raw_text": ""})
    
    # Pattern to find statement headers and account numbers
    statement_pattern = re.compile(r'Statement\s+of\s+account\s+for\s+the\s+period\s+of\s+(.*?)(?:\n|$)', re.IGNORECASE)
    
    # Common patterns for account numbers
    account_patterns = [
        r'Account\s+Number[:\s]+(\d+[\-\d]*)',
        r'A/C\s+No\.?[:\s]+(\d+[\-\d]*)',
        r'Account\s+No\.?[:\s]+(\d+[\-\d]*)'
    ]
    
    # Compile account patterns for reuse
    account_regex_list = [re.compile(pattern, re.IGNORECASE) for pattern in account_patterns]
    
    # Split the text by statement headers
    sections = []
    last_pos = 0
    
    for match in statement_pattern.finditer(text):
        # Get the position of the current match
        start_pos = match.start()
        
        # If this isn't the first match, add the previous section
        if start_pos > 0 and last_pos < start_pos:
            sections.append(text[last_pos:start_pos])
        
        # Update the last position
        last_pos = start_pos
    
    # Add the last section
    if last_pos < len(text):
        sections.append(text[last_pos:])
    
    logger.debug(f"Found {len(sections)} sections in the document")
    
    # Process each section
    for i, section in enumerate(sections):
        # Try to find account number in this section
        account_number = None
        for account_regex in account_regex_list:
            match = account_regex.search(section)
            if match:
                account_number = match.group(1).strip()
                # Remove any non-alphanumeric characters
                account_number = re.sub(r'[^a-zA-Z0-9]', '', account_number)
                break
        
        # If no account number found, generate a placeholder
        if not account_number:
            account_number = f"unknown_account_{i+1}"
            logger.warning(f"No account number found in section {i+1}, using placeholder {account_number}")
        
        # Find statement period
        statement_match = statement_pattern.search(section)
        statement_period = statement_match.group(1).strip() if statement_match else "Unknown period"
        
        # Store the data
        accounts_data[account_number]["statement_period"] = statement_period
        accounts_data[account_number]["raw_text"] = section
        
        # Extract transactions
        transactions = extract_transactions_from_section(section)
        accounts_data[account_number]["transactions"] = transactions
        
        logger.debug(f"Processed account {account_number} with {len(transactions)} transactions")
    
    return dict(accounts_data)

def extract_transactions_from_section(section_text):
    """
    Extract transactions from a section of text.
    This function attempts to identify transaction data using common patterns.
    
    Args:
        section_text (str): Section of text containing transactions
        
    Returns:
        list: List of extracted transactions
    """
    transactions = []
    
    # Try to find transaction rows
    # This pattern needs to be customized based on the actual format of transactions in the PDF
    # Common transaction pattern: Date | Description | Amount | Balance
    # transaction_pattern = re.compile(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.*?)\s+(\-?\$?\d+[\.,]\d{2})\s+(\$?\d+[\.,]\d{2})')
    
    # Split the text by lines to process each line
    lines = section_text.split('\n')
    
    # Skip header lines and process transaction lines
    in_transaction_section = False
    headers_found = False
    
    for line in lines:
        # Check if this line contains transaction headers
        if not headers_found and re.search(r'date|description|amount|balance|debit|credit', line, re.IGNORECASE):
            headers_found = True
            in_transaction_section = True
            continue
        
        if in_transaction_section:
            # Skip empty lines
            if not line.strip():
                continue
                
            # Check if this is the end of transaction section
            if re.search(r'closing balance|total|end of statement', line, re.IGNORECASE):
                in_transaction_section = False
                continue
            
            # Try to parse this line as a transaction
            # This is a simplified example - real implementation would need to handle various formats
            
            # Try to find a date at the beginning of the line (common transaction start)
            date_match = re.search(r'^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', line)
            
            if date_match:
                # This looks like a transaction line
                date = date_match.group(1)
                
                # Extract other components from the line
                # This is simplified and would need to be customized based on actual format
                parts = line[date_match.end():].strip().split()
                
                if len(parts) >= 2:
                    # Assuming the last two fields are amount and balance
                    balance = parts[-1]
                    amount = parts[-2]
                    description = ' '.join(parts[:-2])
                    
                    transactions.append({
                        "date": date,
                        "description": description,
                        "amount": amount,
                        "balance": balance
                    })
    
    logger.debug(f"Extracted {len(transactions)} transactions")
    return transactions
