import os
import logging
import re
from flask import Flask, render_template, request, redirect, url_for, flash, session
import tempfile
import uuid
from werkzeug.utils import secure_filename

from pdf_parser import parse_pdf, extract_account_numbers, extract_multiple_statements

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "development_secret_key")

# Configure upload settings
ALLOWED_EXTENSIONS = {'pdf'}
TEMP_FOLDER = tempfile.gettempdir()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if the post request has the file part
    if 'pdfFile' not in request.files:
        flash('No file part', 'danger')
        return redirect(request.url)
    
    file = request.files['pdfFile']
    
    # If user does not select file, browser also submits an empty part without filename
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        try:
            # Generate a unique filename
            unique_filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
            filepath = os.path.join(TEMP_FOLDER, unique_filename)
            
            # Save the file to disk temporarily
            file.save(filepath)
            logger.debug(f"Saved file to {filepath}")
            
            # Parse the PDF
            try:
                extracted_text = parse_pdf(filepath)
                
                # Extract multiple statement sections
                statements = extract_multiple_statements(extracted_text)
                
                # Store the statements and full text in session
                session['statements'] = statements
                session['raw_text'] = extracted_text
                
                # Redirect to results page
                return redirect(url_for('show_results'))
                
            except Exception as e:
                logger.error(f"Error processing PDF: {str(e)}")
                flash(f"Error processing PDF: {str(e)}", 'danger')
                return redirect(url_for('index'))
            finally:
                # Clean up - remove the temporary file
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.debug(f"Removed temp file: {filepath}")
        
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            flash(f"Error uploading file: {str(e)}", 'danger')
            return redirect(url_for('index'))
    else:
        flash('File type not allowed. Please upload PDF files only.', 'danger')
        return redirect(url_for('index'))

@app.route('/results')
def show_results():
    statements = session.get('statements', None)
    
    # Debug logging
    logger.debug(f"Session contents: {session.keys()}")
    logger.debug(f"Statements data: {statements}")
    
    if not statements:
        flash('No data available. Please upload a PDF file first.', 'warning')
        return redirect(url_for('index'))
    
    return render_template('results.html', statements=statements)

@app.route('/clear')
def clear_data():
    # Clear all session data related to PDF parsing
    session.pop('statements', None)
    session.pop('raw_text', None)
    session.pop('relevant_text', None)
    session.pop('accounts_data', None)  # Clear old format data if exists
    
    flash('Data cleared successfully', 'success')
    return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error="404 - Page Not Found"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error="500 - Internal Server Error"), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
