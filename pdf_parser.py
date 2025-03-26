import pdfplumber
import logging
import os
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def parse_pdf(pdf_path):
    """
    Parse a PDF file and extract all text content.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text from the PDF
        
    Raises:
        FileNotFoundError: If the PDF file does not exist
        Exception: For any other errors during parsing
    """
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    logger.debug(f"Parsing PDF: {pdf_path}")
    
    extracted_text = ""
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Get number of pages
            num_pages = len(pdf.pages)
            logger.debug(f"PDF has {num_pages} pages")
            
            # Process each page
            for i, page in enumerate(pdf.pages):
                logger.debug(f"Processing page {i+1} of {num_pages}")
                
                try:
                    # Extract text from the page
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n\n"
                    else:
                        logger.warning(f"No text extracted from page {i+1}")
                except Exception as e:
                    logger.error(f"Error extracting text from page {i+1}: {str(e)}")
                    # Continue with other pages even if one fails
                    continue
    
    except Exception as e:
        logger.error(f"Error parsing PDF: {str(e)}")
        raise Exception(f"Error parsing PDF: {str(e)}")
    
    if not extracted_text:
        logger.warning("No text was extracted from the PDF")
    else:
        logger.debug(f"Successfully extracted {len(extracted_text)} characters")
    
    return extracted_text

def extract_account_numbers(text):
    """
    Extract account numbers from the text.
    This is a helper function that can be used for more specific account number extraction.
    
    Args:
        text (str): Text extracted from the PDF
        
    Returns:
        list: List of extracted account numbers
    """
    # Common patterns for account numbers (customize based on actual format)
    # This is a basic example - modify based on the actual account number format
    account_patterns = [
        r'Account\s+Number[:\s]+(\d+[\-\d]*)',  # Account Number: 12345678
        r'A/C\s+No\.?[:\s]+(\d+[\-\d]*)',       # A/C No.: 12345678
        r'Account\s+No\.?[:\s]+(\d+[\-\d]*)'    # Account No: 12345678
    ]
    
    account_numbers = []
    for pattern in account_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            account_number = match.group(1).strip()
            # Remove any non-alphanumeric characters for consistency
            account_number = re.sub(r'[^a-zA-Z0-9]', '', account_number)
            if account_number and account_number not in account_numbers:
                account_numbers.append(account_number)
    
    return account_numbers

def extract_transactions(raw_text):
    """
    Extract transactions from raw text where each transaction starts with a date.
    
    Args:
        raw_text (str): Raw text containing transaction data
        
    Returns:
        list: List of transaction dictionaries with date, description, amount, and balance
    """
    transactions = []
    lines = raw_text.split('\n')
    
    # Date patterns to identify transaction lines
    date_patterns = [
        r'^(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',                        # DD/MM/YYYY or MM/DD/YYYY
        r'^(\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4})',                     # DD-MMM-YYYY
        r'^(\d{1,2}[.]?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[.]?\s+\d{2,4})'  # DD Jan YYYY
    ]
    
    # Pattern for balance at the end that includes formats like "30,38234.66dr" 
    balance_pattern = r'([\d,]+\.\d{2}(?:Dr|Cr|dr|cr)?)$'
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if line starts with a date
        is_transaction_line = False
        date_match = None
        
        for pattern in date_patterns:
            match = re.match(pattern, line)
            if match:
                is_transaction_line = True
                date_match = match
                break
                
        if is_transaction_line:
            # Extract the date
            date = date_match.group(1)
            
            # Check if we have a balance at the end (like "30,38234.66dr")
            balance_match = re.search(balance_pattern, line)
            balance = None
            balance_pos = None
            
            if balance_match:
                balance = balance_match.group(1)
                balance_pos = balance_match.start()
            
            # Extract the parts between the date and balance
            if balance_pos:
                # Get the content between date and balance
                mid_content = line[date_match.end():balance_pos].strip()
                
                # We need to extract the amount which is typically right before the balance
                # Let's split by whitespace and look for the amount
                parts = re.split(r'\s+', mid_content)
                
                # The amount is typically right before the balance
                # But if there are type codes like "T" or "C", they might be right after the date
                amount = parts[-1] if parts else 'N/A'
                
                # Extract description (everything between date and amount)
                description = ' '.join(parts[:-1]) if len(parts) > 1 else ''
                
                # Check if we have a type code (T or C) right after the date
                type_match = re.match(r'^([TC])\s', mid_content)
                type_code = ''
                
                if type_match:
                    type_code = type_match.group(1)
                    # If we found a type code, update the description
                    description = mid_content[type_match.end():].strip()
                    if amount in description:
                        # Remove the amount from the description
                        description = description.replace(amount, '').strip()
            else:
                # If no balance found, just split the line by whitespace
                parts = re.split(r'\s+', line[date_match.end():].strip())
                
                # Look for numbers that might be amounts
                amount_candidates = []
                for part in parts:
                    if re.match(r'[\d,]+\.\d{2}', part):
                        amount_candidates.append(part)
                
                # If we found potential amounts, use the last one as balance and second-to-last as amount
                if len(amount_candidates) >= 2:
                    amount = amount_candidates[-2]
                    balance = amount_candidates[-1]
                elif len(amount_candidates) == 1:
                    # Only one numeric value found
                    balance = amount_candidates[0]
                    amount = 'N/A'
                else:
                    # No numeric values found
                    amount = 'N/A'
                    balance = 'N/A'
                
                # Extract description (everything that's not the date, amount, or balance)
                description_parts = []
                skip_parts = [date]
                if amount != 'N/A':
                    skip_parts.append(amount)
                if balance != 'N/A':
                    skip_parts.append(balance)
                
                for part in parts:
                    if part not in skip_parts:
                        description_parts.append(part)
                
                description = ' '.join(description_parts)
            
            # Create transaction object
            transaction = {
                'date': date,
                'description': description,
                'amount': amount,
                'balance': balance if balance else 'N/A'
            }
            
            transactions.append(transaction)
    
    return transactions

def extract_multiple_statements(text):
    """
    Extract multiple statement sections from the PDF text.
    This helps handle PDFs with multiple people's account information.
    
    Args:
        text (str): Text extracted from the PDF
        
    Returns:
        list: List of dictionaries containing statement details for each person
    """
    statement_pattern = r'Statement\s+of\s+account\s+for\s+the\s+period\s+of\s+(.*?)(?:\n|$)'
    statement_matches = list(re.finditer(statement_pattern, text, re.IGNORECASE))
    
    statements = []
    
    # If we find statement declarations
    if statement_matches:
        # Process each statement match and the text that follows it
        for i, match in enumerate(statement_matches):
            start_idx = match.end()
            statement_period = match.group(1).strip()
            
            # If this is not the last match, get text until the next statement
            if i < len(statement_matches) - 1:
                next_start = statement_matches[i + 1].start()
                section_text = text[start_idx:next_start].strip()
            else:
                # For the last statement, get all remaining text
                section_text = text[start_idx:].strip()
            
            # Extract account numbers from this section
            account_numbers = extract_account_numbers(section_text)
            
            # Extract transactions from this section
            transactions = extract_transactions(section_text)
            
            # Store details for this statement
            statements.append({
                "statement_period": statement_period,
                "account_numbers": account_numbers,
                "raw_text": section_text,
                "transactions": transactions
            })
    else:
        # If no statement pattern matches found, treat the entire text as one statement
        logger.warning("No statement period declarations found, treating as a single statement")
        statements.append({
            "statement_period": "Not specified",
            "account_numbers": extract_account_numbers(text),
            "raw_text": text,
            "transactions": extract_transactions(text)
        })
    
    return statements
