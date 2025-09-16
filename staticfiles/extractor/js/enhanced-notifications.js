/**
 * Enhanced notification system using SweetAlert2
 */

// Main notification function that handles different notification types
function showEnhancedNotification(message, type = 'info', options = {}) {
    // Default configuration
    const defaultConfig = {
        title: getDefaultTitle(type),
        text: message,
        icon: type,
        position: 'top-end',
        toast: true,
        timer: options.duration || 5000,
        timerProgressBar: true,
        showConfirmButton: false,
        showCloseButton: true,
        customClass: {
            popup: 'animated fadeInRight'
        }
    };
    
    // Merge user options with defaults
    const config = {...defaultConfig, ...options};
    
    // Show the notification
    return Swal.fire(config);
}

// Helper function to get default titles based on notification type
function getDefaultTitle(type) {
    switch(type) {
        case 'success':
            return 'Success!';
        case 'error':
            return 'Error!';
        case 'warning':
            return 'Warning!';
        case 'info':
        default:
            return 'Information';
    }
}

// Function to show extraction results notification
function showExtractionNotification(extractedCount, status = 'completed') {
    let title, icon, text;
    
    switch(status) {
        case 'completed':
            title = 'Extraction Complete';
            icon = 'success';
            text = `Successfully extracted ${extractedCount} entries`;
            break;
        case 'partial_success_ocr':
            title = 'Partial Extraction';
            icon = 'warning';
            text = `Extracted ${extractedCount} entries with some OCR fallback`;
            break;
        case 'failed_ocr':
            title = 'Extraction Limited';
            icon = 'warning';
            text = 'OCR fallback was needed but could not extract all data';
            break;
        default:
            title = 'Extraction Finished';
            icon = 'info';
            text = `Extraction process completed with ${extractedCount} entries`;
    }
    
    return Swal.fire({
        title: title,
        text: text,
        icon: icon,
        position: 'center',
        showConfirmButton: true,
        confirmButtonText: 'View Results',
        showCancelButton: true,
        cancelButtonText: 'Dismiss',
        customClass: {
            popup: 'animated fadeInDown'
        }
    }).then((result) => {
        if (result.isConfirmed) {
            // Refresh the page to show results
            location.reload();
        }
    });
}

// Function to check if a file exists and update UI accordingly
function validateFileLink(linkElement, fallbackText = 'File not available') {
    const filePath = linkElement.href;
    
    // Check if the file path is valid
    fetch(filePath, { method: 'HEAD' })
        .then(response => {
            if (!response.ok) {
                handleBrokenLink(linkElement, fallbackText);
            }
        })
        .catch(() => {
            handleBrokenLink(linkElement, fallbackText);
        });
}

// Helper function to handle broken links
function handleBrokenLink(linkElement, fallbackText) {
    // Store original styling
    const originalClass = linkElement.className;
    const originalHtml = linkElement.innerHTML;
    
    // Add broken link styling
    linkElement.classList.add('broken-link');
    
    // Add warning icon
    linkElement.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${fallbackText}`;
    
    // Prevent default action
    linkElement.addEventListener('click', function(e) {
        e.preventDefault();
        
        showEnhancedNotification(
            'The requested file is not available or has been moved.', 
            'warning',
            {
                title: 'File Not Found',
                position: 'center',
                timer: 4000
            }
        );
        
        return false;
    });
}

// Validate all download links on page load
function validateAllFileLinks() {
    // Selector for file download links
    const fileLinks = document.querySelectorAll('a[href*="download"], a[href*="media"], a[href*="uploads"]');
    
    fileLinks.forEach(link => {
        // Skip links with data-skip-validation attribute
        if (link.hasAttribute('data-skip-validation')) {
            return;
        }
        
        validateFileLink(link);
    });
}

// Function to show detailed error for ZIP creation failures
function showZipCreationError(errorMessage) {
    Swal.fire({
        title: 'Download Error',
        html: `
            <div class="text-left">
                <p><strong>Could not create ZIP archive of PDFs and Excel data.</strong></p>
                <p>This could be due to one of the following reasons:</p>
                <ul>
                    <li>One or more source files (PDFs or Excel) are missing or corrupted</li>
                    <li>The destination directory does not exist or isn't writable</li>
                    <li>Files required for the ZIP are locked or lack permissions</li>
                    <li>The Excel file contains duplicate sheet names or is corrupted</li>
                </ul>
                <p class="mt-3">The system reported: <br><code>${errorMessage}</code></p>
                <p class="mt-3">The error has been logged. Please contact support if this issue persists.</p>
            </div>
        `,
        icon: 'error',
        confirmButtonText: 'OK',
        width: '600px'
    });
}
