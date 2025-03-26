# 📊 PDF Transaction Extractor

## Overview
A Python application to extract and organize financial transactions from PDF bank statements using PyPDF2, Flask, and PyXML.

## Features
- 📄 Extract transactions from PDF statements
- 🌐 Web-based interface
- 📊 Convert to tabular format

## Tech Stack
- Python
- PyPDF2
- Flask
- PyXML
- Pandas

## Installation
```bash
pip install PyPDF2 flask pyxml pandas
```

## Usage
```bash
python app.py
```
Open browser at `http://localhost:5000`

## Project Structure
```
pdf-transaction-extractor/
├── app.py
├── pdf_parser.py
├── models.py
└── transaction_organizer.py
```

## Contribution
1. Fork repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open Pull Request

## Limitations
- Varies with PDF formatting
- Extraction accuracy depends on document quality

## License
MIT License
