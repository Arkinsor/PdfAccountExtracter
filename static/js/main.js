// Wait for the document to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    
    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // Toggle raw text display
    const toggleButtons = document.querySelectorAll('.toggle-raw-text');
    
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const targetElement = document.getElementById(targetId);
            
            if (targetElement.style.display === 'none') {
                targetElement.style.display = 'block';
                this.innerHTML = '<i class="fas fa-code me-1"></i>Hide Raw Text';
            } else {
                targetElement.style.display = 'none';
                this.innerHTML = '<i class="fas fa-code me-1"></i>Toggle Raw Text';
            }
        });
    });
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Add tooltip functionality
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    
    // File input enhancements
    const fileInput = document.getElementById('pdfFile');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const fileName = this.files[0]?.name;
            const fileInfo = document.querySelector('.form-text');
            
            if (fileName) {
                fileInfo.innerHTML = '<i class="fas fa-file-pdf me-1 text-primary"></i> Selected file: <strong>' + fileName + '</strong>';
            } else {
                fileInfo.innerHTML = '<i class="fas fa-info-circle me-1"></i>Only PDF files are supported.';
            }
        });
    }
});
