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
