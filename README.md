# mail-mock

Local SMTP server to capture, inspect, and test emails during development. Like Mailhog/MailPit, but simpler.

## Installation

```bash
pip install mail-mock
```

## Usage

```bash
# Start SMTP server (port 1025) + Web dashboard (port 8025)
mail-mock serve

# Custom ports
mail-mock serve --smtp-port 2525 --http-port 9025

# List captured emails
mail-mock list

# View a specific email
mail-mock view 1

# Clear all captured emails
mail-mock clear

# Forward a captured email to a real address (via external SMTP)
mail-mock forward 1 real@email.com --smtp-host smtp.gmail.com --smtp-port 587
```

## Configure Your App

Point your application's SMTP settings to mail-mock:

```
SMTP_HOST=localhost
SMTP_PORT=1025
```

### Python (smtplib)
```python
import smtplib
from email.mime.text import MIMEText

msg = MIMEText("<h1>Hello</h1>", "html")
msg["Subject"] = "Test Email"
msg["From"] = "dev@example.com"
msg["To"] = "user@example.com"

with smtplib.SMTP("localhost", 1025) as server:
    server.send_message(msg)
```

### Node.js (nodemailer)
```javascript
const transporter = nodemailer.createTransport({
  host: "localhost",
  port: 1025,
  secure: false,
});
```

## Web Dashboard

Open http://localhost:8025 to view captured emails with:
- Inbox list with sender, subject, timestamp
- HTML email preview
- Plain text view
- Raw source viewer
- Search by sender, recipient, or subject

## License

MIT
