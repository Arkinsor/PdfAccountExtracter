import re
import logging
from collections import defaultdict
import time

# Configure logging with more detailed format for better debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
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
    
    # Common patterns for account numbers - extended to catch more formats
    account_patterns = [
        r'Account\s+Number[:\s]+(\d+[\-\d]*)',
        r'A/C\s+No\.?[:\s]+(\d+[\-\d]*)',
        r'Account\s+No\.?[:\s]+(\d+[\-\d]*)',
        r'Account[:\s]+(\d+[\-\d]*)',
        r'A/C[:\s]+(\d+[\-\d]*)'
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
    This function identifies transaction data by looking for dates that start rows
    after the statement period text.
    
    Args:
        section_text (str): Section of text containing transactions
        
    Returns:
        list: List of extracted transactions
    """
    transactions = []
    
    # Find the statement period line to identify where transactions might start
    statement_pattern = re.compile(r'Statement\s+of\s+account\s+for\s+the\s+period\s+of\s+(.*?)(?:\n|$)', re.IGNORECASE)
    statement_match = statement_pattern.search(section_text)
    
    # Direct transaction detection mode - for cases where there might not be standard headers
    # This is particularly useful for formats where transactions follow immediately after statement period
    if statement_match or section_text.strip().startswith("Statement of account for the period of"):
        logger.debug("Statement period line found, attempting direct transaction detection")
        
        # Try direct date-based transaction detection
        direct_transactions = direct_transaction_extraction(section_text)
        if direct_transactions:
            logger.info(f"Successfully extracted {len(direct_transactions)} transactions directly")
            return direct_transactions
    else:
        logger.warning("Statement period line not found in section text")
        # Even if no statement period found, try direct extraction as a fallback
        direct_transactions = direct_transaction_extraction(section_text)
        if direct_transactions:
            logger.info(f"Extracted {len(direct_transactions)} transactions using fallback method")
            return direct_transactions
    
    # Split by lines to process each line after the statement period
    lines = section_text.split('\n')
    
    # Find the index of the line with the statement period
    statement_line_idx = -1
    for i, line in enumerate(lines):
        if statement_pattern.search(line):
            statement_line_idx = i
            break
    
    if statement_line_idx == -1:
        logger.warning("Could not locate statement period line in the text")
        return transactions
    
    # Find headers to determine the column structure
    # Look for headers after the statement period line
    header_idx = -1
    header_line = ""
    
    # Look for more header patterns with a wider search range
    for i in range(statement_line_idx + 1, min(statement_line_idx + 30, len(lines))):
        # Check for common transaction table headers
        if re.search(r'date|transaction date|value date|posting date', lines[i], re.IGNORECASE) and (
           re.search(r'description|particulars|narration|details|transaction|remarks', lines[i], re.IGNORECASE) or 
           re.search(r'amount|debit|credit|withdrawal|deposit', lines[i], re.IGNORECASE) or
           re.search(r'balance|closing balance|running balance', lines[i], re.IGNORECASE)):
            header_idx = i
            header_line = lines[i]
            logger.debug(f"Found transaction header at line {i+1}: {lines[i]}")
            break
        
        # If no clear header with multiple columns, look for any date-like pattern
        # This is a fallback as some statements may not have clear headers
        if header_idx == -1 and i > statement_line_idx + 5:  # Skip first few lines after statement
            # Check if line starts with a date pattern
            for date_pattern in [r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', r'^\d{2}[.]\d{2}[.]\d{2,4}']:
                if re.search(date_pattern, lines[i].strip()):
                    header_idx = i - 1  # Set the previous line as a virtual header
                    logger.debug(f"No explicit header found. Using line before first date as virtual header")
                    break
    
    # If we found headers, use them to determine the column structure
    if header_idx != -1:
        logger.debug(f"Found header line: {header_line}")
        
        # Start processing transaction lines after the header
        in_transaction_section = True
        
        for i in range(header_idx + 1, len(lines)):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Check if this is the end of transaction section
            if re.search(r'closing balance|total|end of statement', line, re.IGNORECASE):
                in_transaction_section = False
                break
            
            # Try to find a date at the beginning of the line (common transaction start)
            # Support various date formats: DD/MM/YY, DD-MM-YYYY, MM/DD/YYYY etc.
            date_patterns = [
                r'^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',     # Standard date formats like DD/MM/YYYY or MM/DD/YYYY
                r'^(\d{2}[./-]\d{2}[./-]\d{2,4})',        # DD.MM.YYYY format
                r'^(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})', # 10 Jan 2023 format
                r'^(\d{4}[/-]\d{1,2}[/-]\d{1,2})'         # YYYY-MM-DD format
            ]
            
            date_match = None
            for pattern in date_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    date_match = match
                    break
            
            if date_match and in_transaction_section:
                # This is a new transaction line
                date = date_match.group(1)
                
                # Extract other components from the line
                remaining_text = line[date_match.end():].strip()
                
                # Try to split the rest of the line into description, amount, and balance
                # This pattern needs to be adjusted based on your specific PDF format
                # Look for currency patterns or number patterns to identify amount and balance
                parts = re.split(r'\s{2,}', remaining_text)  # Split by 2 or more spaces
                
                if len(parts) >= 3:
                    # Assume format is: Date | Description | Amount | Balance
                    description = parts[0]
                    
                    # Check parts for numeric/currency values with improved patterns
                    amount_candidates = []
                    for part in parts[1:]:
                        # Enhanced patterns for currency and amount detection
                        if (re.search(r'[\$£€]?[\-+]?[\d,]+\.\d{2}', part) or  # Standard format ($123.45)
                            re.search(r'[\-+]?[\d,]+\.\d{2}', part) or         # Without currency (123.45)
                            re.search(r'[\$£€]?[\-+]?[\d,]+', part) or         # Whole numbers with currency ($123)
                            re.search(r'[\-+]?[\d,]+', part) or                # Whole numbers (123)
                            re.search(r'[\-+]?[\d]*\.?\d+', part)):            # Any numeric value
                            amount_candidates.append(part)
                    
                    if len(amount_candidates) >= 2:
                        amount = amount_candidates[-2]
                        balance = amount_candidates[-1]
                    elif len(amount_candidates) == 1:
                        # Only found one number, assume it's the amount
                        amount = amount_candidates[0]
                        balance = "N/A"
                    else:
                        # Fallback if we can't identify numeric values
                        if len(parts) >= 2:
                            amount = parts[-2]
                            balance = parts[-1]
                        else:
                            amount = "N/A"
                            balance = "N/A"
                            
                    # Join all parts except last two as description (if not already set)
                    if len(parts) > 2 and description == parts[0]:
                        description = ' '.join(parts[:-2])
                        
                elif len(parts) == 2:
                    # Assume format is: Date | Description | Amount
                    description = parts[0]
                    amount = parts[1]
                    balance = "N/A"
                else:
                    # Fallback for lines with minimal parsing
                    description = remaining_text
                    amount = "N/A"
                    balance = "N/A"
                
                # Create transaction record
                transactions.append({
                    "date": date,
                    "description": description,
                    "amount": amount,
                    "balance": balance
                })
            elif in_transaction_section:
                # This might be a continuation of the previous transaction description
                # or a line without a date that belongs to the previous transaction
                
                # First check if this line might be a continuation (no date, but has other transaction info)
                if transactions:
                    # Skip lines that look like section endings or headers
                    if re.search(r'total|balance|opening|closing|statement|period|page', line, re.IGNORECASE):
                        continue
                        
                    # Check if this line contains amount/balance info without a date
                    amount_patterns = [
                        r'[\$£€]?[\-+]?[\d,]+\.\d{2}',  # Common currency format
                        r'[\-+]?[\d,]+\.\d{2}',         # Number with decimal
                        r'[\-+]?[\d,]+'                 # Whole number
                    ]
                    
                    has_amount = False
                    for pattern in amount_patterns:
                        if re.search(pattern, line):
                            has_amount = True
                            break
                            
                    if has_amount and len(line.split()) <= 4:
                        # This might be just amount/balance information
                        # Add it to the amount or balance if those are missing or marked as N/A
                        if transactions[-1]["amount"] == "N/A":
                            transactions[-1]["amount"] = line.strip()
                        elif transactions[-1]["balance"] == "N/A":
                            transactions[-1]["balance"] = line.strip()
                    else:
                        # Otherwise treat it as continuation of description
                        transactions[-1]["description"] += " " + line.strip()
    else:
        logger.warning("No transaction headers found after statement period line")
    
    logger.debug(f"Extracted {len(transactions)} transactions")
    return transactions
