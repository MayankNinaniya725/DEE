# 🔬 PDF Data Extractor System

A comprehensive Django-based application for automated PDF data extraction from steel industry test certificates using OCR, pattern recognition, and vendor-specific configurations.

## 📋 Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Core Features](#core-features)
- [Installation & Setup](#installation--setup)
- [File Structure](#file-structure)
- [Core Components](#core-components)
- [Vendor Configuration System](#vendor-configuration-system)
- [Data Flow](#data-flow)
- [API Documentation](#api-documentation)
- [Testing & Debugging](#testing--debugging)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

---

## 🌟 Overview

The PDF Data Extractor System is designed to automatically extract structured data from steel industry test certificates. It supports multiple vendors (POSCO, Hengrun, Iraeta, JSW, CITIC) and handles various document formats, OCR quality issues, and complex table structures.

### Key Capabilities
- **Multi-vendor Support**: Configurable extraction patterns for different certificate formats
- **OCR Enhancement**: Advanced text recognition with fallback strategies
- **Quality Assurance**: Automated data validation and quality indicators
- **Batch Processing**: Asynchronous processing with Celery workers
- **Admin Interface**: Django admin with Jazzmin theme for data management
- **API Access**: RESTful APIs for integration and downloads

---

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Django App    │    │   Background    │
│   (Upload UI)   │◄──►│   (Core Logic)  │◄──►│   (Celery)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │◄──►│   File System   │    │   Redis         │
│   (Database)    │    │   (PDF Storage) │    │   (Cache/Queue) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

**Technology Stack:**
- **Backend**: Django 5.0.7, Python 3.x
- **Database**: PostgreSQL (Production) / SQLite (Development)
- **Queue**: Redis + Celery for async processing
- **OCR**: Tesseract, pdfplumber, PyPDF2
- **Frontend**: Django templates with Jazzmin admin theme
- **Deployment**: Docker + Docker Compose

---

## 🚀 Core Features

### 1. **Intelligent PDF Processing**
- Multi-format PDF support (scanned images, text PDFs, complex layouts)
- OCR quality detection and fallback strategies
- Vendor-specific pattern recognition
- Table structure analysis and data extraction

### 2. **Vendor Configuration System**
- JSON-based vendor configurations
- Regex pattern matching for different data fields
- Multilingual support (English/Chinese)
- Fallback strategies for poor OCR quality

### 3. **Data Management**
- Structured data storage with relationships
- Excel export functionality with page numbers
- Bulk download and packaging
- Data validation and quality indicators

### 4. **Admin Interface**
- Jazzmin-themed Django admin
- User management and authentication
- Real-time processing dashboard
- Comprehensive data visualization

---

## 📦 Installation & Setup

### Prerequisites
- Docker and Docker Compose
- Git

### Quick Start

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd extractor_project
   ```

2. **Environment Setup**
   ```bash
   # Copy environment file
   cp .env.docker .env
   
   # Edit environment variables as needed
   nano .env
   ```

3. **Docker Deployment**
   ```bash
   # Build and start services
   docker-compose up -d --build
   
   # Run migrations
   docker-compose exec web python manage.py migrate
   
   # Create superuser
   docker-compose exec web python manage.py createsuperuser
   ```

4. **Access the Application**
   - Main Interface: http://localhost:8000
   - Admin Panel: http://localhost:8000/admin
   - Upload Page: http://localhost:8000/upload

### Manual Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Setup database
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

---

## 📁 File Structure

### Root Directory
```
extractor_project/
├── 📄 manage.py                    # Django management script
├── 📄 requirements.txt             # Python dependencies
├── 📄 docker-compose.yml          # Docker orchestration
├── 📄 Dockerfile                  # Docker container definition
├── 📄 README.md                   # This documentation
├── 📄 .gitignore                  # Git ignore patterns
├── 📄 start.sh                    # Application startup script
└── 📄 db.sqlite3                  # SQLite database (development)
```

### Core Application (`extractor/`)
```
extractor/
├── 📁 models/                      # Database models
│   ├── 📄 __init__.py             # Model exports
│   └── 📄 user.py                 # Custom user model
├── 📁 views/                       # View controllers
│   ├── 📄 core.py                 # Main processing views
│   ├── 📄 auth.py                 # Authentication views
│   ├── 📄 downloads.py            # Download handlers
│   └── 📄 api_views.py            # API endpoints
├── 📁 utils/                       # Utility modules
│   ├── 📄 pattern_extractor.py    # Text pattern matching
│   ├── 📄 config_loader.py        # Vendor config loading
│   ├── 📄 ocr_helper.py           # OCR processing
│   ├── 📄 extractor.py            # PDF text extraction
│   ├── 📄 excel_helper.py         # Excel generation
│   └── 📄 posco_corrections.py    # POSCO-specific fixes
├── 📁 vendor_configs/              # Vendor-specific patterns
│   ├── 📄 posco_steel.json        # POSCO configuration
│   ├── 📄 hengrum_steel.json      # Hengrun configuration
│   ├── 📄 iraeta_steel.json       # Iraeta configuration
│   ├── 📄 jsw_steel.json          # JSW configuration
│   └── 📄 citic_steel.json        # CITIC configuration
├── 📁 templates/                   # HTML templates
├── 📁 static/                      # Static files (CSS/JS)
├── 📁 migrations/                  # Database migrations
├── 📄 models.py                    # Main models file
├── 📄 views.py                     # Main views file
├── 📄 urls.py                      # URL routing
├── 📄 admin.py                     # Admin configuration
├── 📄 tasks.py                     # Celery tasks
└── 📄 forms.py                     # Django forms
```

### Project Configuration (`extractor_project/`)
```
extractor_project/
├── 📄 settings.py                 # Django settings
├── 📄 urls.py                     # Root URL configuration
├── 📄 wsgi.py                     # WSGI application
├── 📄 asgi.py                     # ASGI application
└── 📄 celery.py                   # Celery configuration
```

### Test & Debug Scripts
```
├── 📄 test_posco_extraction.py    # POSCO extraction tests
├── 📄 test_hengrun_patterns.py    # Hengrun pattern tests
├── 📄 validate_iraeta_system.py   # Iraeta validation
├── 📄 debug_config_loading.py     # Config debugging
├── 📄 final_hengrun_demo.py       # Complete system demo
└── 📄 completion_summary.py       # System overview
```

---

## 🔧 Core Components

### 1. **Models** (`extractor/models/`)

#### CustomUser Model
```python
# User management with admin privileges
class CustomUser(AbstractUser):
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

#### Vendor Model
```python
# Vendor configuration management
class Vendor(models.Model):
    name = models.CharField(max_length=200)
    config_path = models.CharField(max_length=500)  # Path to JSON config
    is_active = models.BooleanField(default=True)
```

#### UploadedPDF Model
```python
# PDF file tracking and metadata
class UploadedPDF(models.Model):
    file = models.FileField(upload_to='uploaded_files/')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    upload_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending')
    processed_at = models.DateTimeField(null=True, blank=True)
```

#### ExtractedData Model
```python
# Extracted certificate data storage
class ExtractedData(models.Model):
    pdf = models.ForeignKey(UploadedPDF, on_delete=models.CASCADE)
    plate_no = models.CharField(max_length=100)
    heat_no = models.CharField(max_length=100)
    test_cert_no = models.CharField(max_length=100)
    page_number = models.IntegerField(default=1)
    extraction_quality = models.CharField(max_length=50, default='NORMAL')
```

### 2. **Views** (`extractor/views/`)

#### Core Processing Views (`core.py`)
- **`upload_pdf`**: Handles PDF file uploads with vendor detection
- **`process_pdf`**: Initiates asynchronous PDF processing
- **`dashboard`**: Main dashboard with processing statistics
- **`task_progress`**: Real-time processing status updates

#### Authentication Views (`auth.py`)
- **`login_view`**: Custom login with admin verification
- **`logout_view`**: Secure logout handling
- **`admin_dashboard`**: Administrative dashboard with analytics

#### Download Views (`downloads.py`)
- **`download_package`**: Bulk download of processed files
- **`download_excel`**: Excel export with page numbers
- **`download_pdf_package`**: PDF packaging with metadata

### 3. **Utilities** (`extractor/utils/`)

#### Pattern Extractor (`pattern_extractor.py`)
```python
def extract_patterns_from_text(text: str, vendor_config: Dict) -> List[Dict]:
    """
    Core extraction engine that:
    - Applies vendor-specific regex patterns
    - Handles multiple extraction modes (global, line-by-line)
    - Implements fallback strategies for poor OCR
    - Returns structured data with quality indicators
    """
```

#### Config Loader (`config_loader.py`)
```python
def load_vendor_config(vendor_path: str) -> Dict:
    """
    Loads JSON vendor configurations with:
    - UTF-8 encoding support
    - Error handling for malformed configs
    - Validation of required fields
    """
```

#### OCR Helper (`ocr_helper.py`)
```python
def extract_text_with_ocr(pdf_path: str, page_num: int) -> str:
    """
    Advanced OCR processing with:
    - Tesseract integration
    - Image preprocessing
    - Multiple language support
    - Quality enhancement filters
    """
```

### 4. **Tasks** (`tasks.py`)

#### Celery Background Tasks
```python
@shared_task(bind=True)
def process_pdf_file(self, pdf_id: int) -> Dict:
    """
    Asynchronous PDF processing:
    - PDF text extraction
    - Pattern matching and data extraction
    - Database storage
    - Error handling and retry logic
    """
```

---

## 🎯 Vendor Configuration System

### Configuration Structure
Each vendor has a JSON configuration file defining extraction patterns:

```json
{
  "vendor_id": "hengrun",
  "vendor_name": "Jiangyin Hengrun Ring Forging",
  "extraction_mode": "table",
  "multi_match": true,
  "multilingual": true,
  "fallback_strategy": {
    "enabled": true,
    "fallback_entries": [
      {"PLATE_NO": "6-0003", "description": "Standard part"},
      {"PLATE_NO": "6-0002", "description": "Standard part"}
    ],
    "conditions": {
      "ocr_quality_threshold": 500
    }
  },
  "fields": {
    "PLATE_NO": {
      "pattern": "\\b([6-9]\\-\\d{4})\\b",
      "match_type": "line_by_line",
      "extract_all": true
    },
    "HEAT_NO": {
      "pattern": "\\b(S\\d+[A-Z]*X?)\\b",
      "match_type": "global",
      "share_value": true,
      "fallback_value": "S_UNKNOWN"
    },
    "TEST_CERT_NO": {
      "pattern": "\\b(HR\\d{11})\\b",
      "match_type": "first",
      "share_value": true
    }
  }
}
```

### Supported Vendors

1. **POSCO Steel** (`posco_steel.json`)
   - 8-digit plate numbers (PP########)
   - Heat numbers with OCR corrections (SU30682→SU30882)
   - Complex table layouts with multilingual support

2. **Hengrun Steel** (`hengrum_steel.json`)
   - 6-#### format plate numbers
   - S-series heat numbers
   - HR certificate numbers with fallback strategy

3. **Iraeta Energy** (`iraeta_steel.json`)
   - 24-3765-## format plate numbers
   - SI24-4260 heat numbers
   - 2024-3765-### certificate numbers

4. **JSW Steel** (`jsw_steel.json`)
   - Standard JSW certificate patterns
   - Multi-format support

5. **CITIC Steel** (`citic_steel.json`)
   - CITIC-specific extraction patterns
   - Chinese/English bilingual support

### Pattern Types

- **`global`**: Search entire document
- **`line_by_line`**: Process each line individually
- **`first`**: Use first match found
- **`table`**: Extract from table structures

### Fallback Strategies

For documents with poor OCR quality:
- **Quality Detection**: Text length thresholds
- **Fallback Entries**: Predefined data when extraction fails
- **Quality Flags**: Mark entries requiring manual review

---

## 🔄 Data Flow

### 1. PDF Upload Process
```
User Upload → Vendor Detection → File Storage → Queue Processing
```

### 2. Processing Pipeline
```
PDF File → Text Extraction → Pattern Matching → Data Validation → Database Storage
```

### 3. Text Extraction Methods
1. **pdfplumber**: Primary text extraction
2. **PyPDF2**: Fallback for complex layouts
3. **Tesseract OCR**: For scanned images
4. **Manual Review**: For failed extractions

### 4. Pattern Matching Engine
1. **Vendor Detection**: Auto-identify certificate type
2. **Config Loading**: Load appropriate JSON patterns
3. **Pattern Application**: Apply regex patterns to text
4. **Quality Assessment**: Evaluate extraction confidence
5. **Fallback Handling**: Use predefined values if needed

---

## 🔌 API Documentation

### Core Endpoints

#### Upload API
```http
POST /upload/
Content-Type: multipart/form-data

Parameters:
- file: PDF file
- vendor: Vendor ID (optional, auto-detected)
```

#### Processing Status
```http
GET /task-progress/<task_id>/
Response: {
    "status": "processing|completed|failed",
    "progress": 0-100,
    "result": {...}
}
```

#### Download Package
```http
POST /download-package/
Content-Type: application/json

Body: {
    "pdf_ids": [1, 2, 3],
    "format": "excel|pdf|both"
}
```

#### Data Retrieval
```http
GET /api/extracted-files-status/
Response: [
    {
        "pdf_id": 1,
        "filename": "certificate.pdf",
        "status": "completed",
        "entries_count": 5
    }
]
```

### Authentication
- Session-based authentication
- Admin privileges required for sensitive operations
- CSRF protection enabled

---

## 🧪 Testing & Debugging

### Test Scripts

#### System Validation
- **`validate_posco_system.py`**: POSCO extraction validation
- **`validate_hengrun_system.py`**: Hengrun system validation
- **`validate_iraeta_system.py`**: Iraeta system validation

#### Pattern Testing
- **`test_posco_extraction.py`**: POSCO pattern testing
- **`test_hengrun_patterns.py`**: Hengrun pattern validation
- **`test_iraeta_patterns.py`**: Iraeta pattern testing

#### Debug Tools
- **`debug_config_loading.py`**: Configuration debugging
- **`debug_hengrun_pdf.py`**: PDF-specific debugging
- **`final_hengrun_demo.py`**: Complete system demonstration

### Running Tests

```bash
# Validate all vendors
python validate_posco_system.py
python validate_hengrun_system.py
python validate_iraeta_system.py

# Test specific patterns
python test_posco_extraction.py
python test_hengrun_patterns.py

# Debug configuration
python debug_config_loading.py
```

### Common Issues & Solutions

#### OCR Quality Issues
- **Problem**: Poor text extraction from scanned PDFs
- **Solution**: Fallback strategy with predefined values
- **Debug**: Use `debug_hengrun_pdf.py` to analyze OCR output

#### Pattern Matching Failures
- **Problem**: Regex patterns not matching expected data
- **Solution**: Update vendor configuration patterns
- **Debug**: Test patterns with `test_*_patterns.py` scripts

#### Processing Timeouts
- **Problem**: Large files causing Celery task timeouts
- **Solution**: Increase task timeout in settings
- **Debug**: Monitor Celery logs for processing status

---

## 🚀 Deployment

### Docker Production Setup

1. **Environment Configuration**
   ```bash
   # Production environment
   cp .env.docker .env
   
   # Edit production settings
   nano .env
   ```

2. **SSL and Security**
   ```yaml
   # docker-compose.prod.yml
   services:
     nginx:
       image: nginx:alpine
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf
         - ./ssl:/etc/nginx/ssl
   ```

3. **Database Backup**
   ```bash
   # Backup PostgreSQL
   docker-compose exec db pg_dump -U extractor_user extractor_db > backup.sql
   
   # Restore
   docker-compose exec -T db psql -U extractor_user extractor_db < backup.sql
   ```

### Performance Optimization

#### Celery Workers
```bash
# Scale workers based on load
docker-compose up --scale celery=4
```

#### Redis Configuration
```python
# settings.py
CELERY_WORKER_CONCURRENCY = 4
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 240
```

#### Database Optimization
```sql
-- Index optimization
CREATE INDEX idx_extracted_data_pdf ON extractor_extracteddata(pdf_id);
CREATE INDEX idx_uploaded_pdf_status ON extractor_uploadedpdf(status);
```

---

## 🔧 Configuration Files

### Django Settings (`settings.py`)
Key configurations:
- **Database**: PostgreSQL/SQLite support
- **Celery**: Redis broker configuration
- **Media**: File storage settings
- **Jazzmin**: Admin theme customization
- **Authentication**: Custom user model

### Celery Configuration (`celery.py`)
- Task routing and queues
- Result backend configuration
- Worker settings and monitoring

### Docker Configuration
- **`Dockerfile`**: Python environment setup
- **`docker-compose.yml`**: Service orchestration
- **`start.sh`**: Application startup script

---

## 📊 Monitoring & Logging

### Log Locations
```
logs/
├── 📄 django.log              # Django application logs
├── 📄 celery.log              # Celery worker logs
├── 📄 extraction.log          # PDF processing logs
└── 📄 error.log               # Error tracking
```

### Health Checks
- **Database**: PostgreSQL health monitoring
- **Redis**: Queue status monitoring
- **Celery**: Worker status and task monitoring
- **File System**: Storage space monitoring

### Performance Metrics
- **Processing Time**: Average PDF processing duration
- **Success Rate**: Extraction success percentage
- **Queue Length**: Pending task monitoring
- **Error Rate**: Failed processing tracking

---

## 🆘 Troubleshooting

### Common Issues

#### 1. Docker Container Issues
```bash
# Check service status
docker-compose ps

# View service logs
docker-compose logs web
docker-compose logs celery
docker-compose logs db

# Restart services
docker-compose restart web
```

#### 2. Database Connection Issues
```bash
# Check database connectivity
docker-compose exec web python manage.py dbshell

# Run migrations
docker-compose exec web python manage.py migrate

# Check migration status
docker-compose exec web python manage.py showmigrations
```

#### 3. Celery Task Issues
```bash
# Check Celery status
docker-compose exec celery celery -A extractor_project status

# Monitor active tasks
docker-compose exec celery celery -A extractor_project active

# Clear task queue
docker-compose exec celery celery -A extractor_project purge
```

#### 4. PDF Processing Failures
```python
# Debug PDF extraction
python debug_hengrun_pdf.py

# Test vendor patterns
python test_posco_extraction.py

# Validate configurations
python debug_config_loading.py
```

### Error Messages

#### "Config for vendor 'X' not found"
- **Cause**: Missing or incorrect vendor configuration
- **Solution**: Check `vendor_configs/` directory and file naming

#### "'NoneType' object has no attribute 'strip'"
- **Cause**: Pattern matching returning None values
- **Solution**: Updated with robust None handling in pattern extractor

#### "Task timeout exceeded"
- **Cause**: Large PDF files taking too long to process
- **Solution**: Increase `CELERY_TASK_TIME_LIMIT` in settings

---

## 📈 Future Enhancements

### Planned Features
1. **Machine Learning Integration**: AI-powered pattern recognition
2. **Real-time Processing**: WebSocket-based live updates
3. **Advanced OCR**: Custom OCR models for steel certificates
4. **Multi-language Support**: Extended language support
5. **API Rate Limiting**: Enhanced security and performance
6. **Audit Trail**: Comprehensive activity logging

### Scaling Considerations
- **Horizontal Scaling**: Multiple Celery workers
- **Database Sharding**: Large-scale data partitioning
- **CDN Integration**: Static file delivery optimization
- **Load Balancing**: Multi-instance deployment

---

## 📚 Additional Resources

### Dependencies
- **Django 5.0.7**: Web framework
- **Celery 5.3.4**: Asynchronous task queue
- **pdfplumber 0.10.2**: PDF text extraction
- **Tesseract**: OCR engine
- **Redis 5.0.1**: Message broker and cache
- **PostgreSQL**: Production database

### Documentation Links
- [Django Documentation](https://docs.djangoproject.com/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [pdfplumber Documentation](https://github.com/jsvine/pdfplumber)
- [Tesseract OCR](https://tesseract-ocr.github.io/)

### Support
For issues and questions:
1. Check the troubleshooting section
2. Review log files for error details
3. Run appropriate debug scripts
4. Consult vendor configuration documentation

---

## 📄 License

This project is proprietary software developed for steel industry certificate processing.

---

*Last Updated: September 2025*
*Version: 2.0.0*
*Maintainer: PDF Extractor Development Team*