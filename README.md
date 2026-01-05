# PDF Signature - MVP

A web application for signing PDF documents, ready for deployment.

## Overview

This Flask-based application provides a simple interface for uploading PDF documents, adding signatures by drawing directly on the document, and storing both original and signed versions.

## Features

- PDF file upload with drag-and-drop support
- Interactive signature drawing on documents
- Document storage and management

## Requirements

- Python 3.9 or higher

## Local Development

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the application:
```bash
python app.py
```

3. Open your browser and navigate to: http://localhost:5000

## Project Structure

```
podpis/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── templates/
│   ├── upload.html     # PDF upload page
└── README.md           # This file
```

## Future Enhancements

Possible extensions for future development:
- User authentication and authorization
- Document history and list view
- Download functionality for signed PDFs
- Digital signature verification (HMAC)
- Multi-page signature support
- Email notifications
- Audit trail and logging

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
