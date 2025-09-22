# Download Package API Endpoint Documentation

## Overview

The new `/download/package/<file_id>` endpoint allows users to download all extracted files for a specific PDF as a ZIP package.

## Endpoint Details

- **URL:** `/download/package/<file_id>/`
- **Method:** GET
- **Authentication:** Required (login_required decorator)
- **Content-Type:** `application/zip` (success) or `application/json` (error)

## Parameters

- `file_id` (int): The ID of the uploaded PDF file (corresponds to `UploadedPDF.id`)

## Response

### Success Response (200)
Returns a ZIP file download with filename `{file_id}_package.zip`

**Content Structure:**
```
outputs/
└── {file_id}/
    ├── original_{filename}.pdf          # Original uploaded PDF
    ├── {filename}_page_1.pdf           # Extracted individual pages
    ├── {filename}_page_2.pdf
    ├── ...
    ├── {filename}_extraction_summary.xlsx  # Excel with extraction data
    └── README.txt                       # Package information
```

### Error Responses

#### 404 - File Not Found
```json
{
    "error": "File with ID {file_id} not found",
    "status": 404
}
```

#### 404 - No Extracted Files
```json
{
    "error": "No extracted files found for file ID {file_id}",
    "status": 404
}
```

#### 500 - Server Error
```json
{
    "error": "Internal server error while creating package",
    "status": 500
}
```

## Usage Examples

### Using cURL
```bash
# Download package for file ID 12345
curl -X GET "http://localhost:8000/download/package/12345/" \
     -H "Cookie: sessionid=your_session_id" \
     -o "12345_package.zip"
```

### Using Python requests
```python
import requests

# Authenticate first (login)
session = requests.Session()
session.post('http://localhost:8000/login/', {
    'username': 'your_username',
    'password': 'your_password'
})

# Download package
response = session.get('http://localhost:8000/download/package/12345/')

if response.status_code == 200:
    with open('12345_package.zip', 'wb') as f:
        f.write(response.content)
    print("Package downloaded successfully!")
else:
    print(f"Error: {response.json()}")
```

### JavaScript/AJAX
```javascript
fetch('/download/package/12345/', {
    method: 'GET',
    credentials: 'include',  // Include cookies for authentication
})
.then(response => {
    if (response.ok) {
        return response.blob();
    } else {
        return response.json().then(err => Promise.reject(err));
    }
})
.then(blob => {
    // Create download link
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '12345_package.zip';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
})
.catch(error => {
    console.error('Download failed:', error);
});
```

## Features

### ✅ Clean and Reusable Code
- Modular function design with proper error handling
- Comprehensive logging for debugging
- Follows existing codebase patterns

### ✅ Docker Compatibility
- Uses container-relative paths
- Works with mounted volumes
- Handles file permissions correctly

### ✅ On-the-Fly ZIP Creation
- No permanent storage of ZIP files
- Memory-efficient streaming
- Proper cleanup of temporary files

### ✅ Comprehensive Error Handling
- Validates file existence
- Checks for extracted data
- Returns appropriate HTTP status codes
- Provides detailed error messages

### ✅ Organized File Structure
- Maintains `outputs/<file_id>/` structure as requested
- Preserves original filenames
- Includes metadata and documentation

## Integration with Existing System

The endpoint seamlessly integrates with the existing download functionality:

1. **Reuses existing functions:** Uses `create_extraction_excel()` for Excel generation
2. **Follows same patterns:** Similar to `download_pdfs_with_excel()` but simplified
3. **Maintains compatibility:** Works with existing authentication and middleware
4. **Database integration:** Uses existing models (`UploadedPDF`, `ExtractedData`)

## Testing

Run the test script to verify functionality:

```bash
cd /path/to/project
python test_download_package_api.py
```

### Manual Testing Steps

1. **Start the server:**
   ```bash
   python manage.py runserver
   ```

2. **Test valid file_id:**
   - Visit: `http://localhost:8000/download/package/1/`
   - Should download: `1_package.zip`

3. **Test invalid file_id:**
   - Visit: `http://localhost:8000/download/package/99999/`
   - Should return: JSON error with 404 status

4. **Verify ZIP contents:**
   - Extract the downloaded ZIP
   - Verify `outputs/1/` structure exists
   - Check all expected files are present

## Differences from Existing Download Functions

| Feature | New `/download/package/<file_id>` | Existing `download_pdfs_with_excel` |
|---------|----------------------------------|--------------------------------------|
| URL Pattern | `/download/package/{file_id}/` | `/download/pdfs-with-excel/?pdf_id={id}` |
| Structure | `outputs/{file_id}/` | Flat structure with folders |
| API Style | RESTful with file_id in URL | Query parameter based |
| Error Format | JSON with proper HTTP codes | Redirects with messages |
| Purpose | API endpoint for automation | UI download for users |

## Security Considerations

- ✅ Requires authentication (`login_required`)
- ✅ Validates file ownership (checks database)
- ✅ Prevents path traversal (uses safe file operations)
- ✅ Limits to extracted files only (no arbitrary file access)
- ✅ Proper error messages (no information leakage)

## Performance Notes

- **Memory Usage:** Efficient streaming, minimal memory footprint
- **Disk Usage:** Temporary files cleaned up automatically
- **Network:** ZIP compression reduces download size
- **CPU:** On-the-fly compression may use CPU, but optimized for typical file sizes

## Troubleshooting

### Common Issues

1. **Authentication Required**
   - Ensure you're logged in before accessing the endpoint
   - Check session cookies are being sent

2. **File Not Found (404)**
   - Verify the file_id exists in the database
   - Check that the PDF has associated extracted data

3. **Permission Errors**
   - Ensure Django has read permissions on media files
   - Check Docker volume mounts if using containers

4. **Large File Handling**
   - For very large packages, consider implementing streaming responses
   - Monitor server memory usage under load

### Logging

Check Django logs for detailed error information:
```bash
# In your Django settings, ensure logging is configured
tail -f /path/to/django.log | grep download_package
```