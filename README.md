# CerberAuth Authentication System

<div align="center">
  <img src="https://i.imgur.com/AovGvVT.png" alt="CerberAuth Logo" width="150"/>
  
  **A secure Flask-based license validation system with admin management**
  
  ![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
  ![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)
  ![License](https://img.shields.io/badge/License-MIT-yellow.svg)
</div>

---

## 🚀 Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Install Dependencies

```bash
pip install flask requests rich sqlite3
```

Or create a `requirements.txt` file:

```txt
Flask>=2.0.0
requests>=2.25.0
rich>=10.0.0
```

Then install:
```bash
pip install -r requirements.txt
```

### Download CerberAuth
1. Save the provided Python code as `cerberauth.py`
2. Make sure the file is in your working directory
3. Ensure proper file permissions for database creation

---

## ⚙️ Setup

### 1. Database Initialization
The system automatically creates a SQLite database (`licenses.db`) on first run with two tables:
- `licenses` - Stores license keys, HWIDs, expiration dates, and plans
- `usage_logs` - Tracks license usage with IP, user agent, and geolocation data

### 2. Admin Key Generation
Upon startup, CerberAuth generates a secure admin key that appears in:
- Console output (red panel)
- Live dashboard footer
- **⚠️ Keep this key secure - it provides full admin access!**

### 3. Start the Server
```bash
python cerberauth.py
```

The server will:
- Initialize the database
- Display the admin key
- Start the live dashboard
- Listen on `http://localhost:5000`

### 4. Environment Configuration (Optional)
You can customize the setup by modifying these variables in the code:
```python
# Database path
db = LicenseDB("custom_licenses.db")

# Server host and port
app.run(host='0.0.0.0', port=8080)
```

---

## 🎯 Demo

### Quick Test Workflow

1. **Start the server:**
   ```bash
   python cerberauth.py
   ```

2. **Copy the admin key** from the console output

3. **Generate a test license:**
   ```bash
   curl -X POST http://localhost:5000/api/generate \
     -H "Authorization: Bearer YOUR_ADMIN_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "hwid": "test-hardware-id-123",
       "expires_at": "2025-12-31",
       "plan": "premium"
     }'
   ```

4. **Verify the license:**
   ```bash
   curl -X POST http://localhost:5000/verify \
     -H "Content-Type: application/json" \
     -d '{
       "key": "LIC-GENERATED_KEY_HERE",
       "hwid": "test-hardware-id-123"
     }'
   ```

5. **Check license info:**
   ```bash
   curl -X GET "http://localhost:5000/api/keyinfo?key=LIC-GENERATED_KEY_HERE" \
     -H "Authorization: Bearer YOUR_ADMIN_KEY"
   ```

### Dashboard Features
The live dashboard displays:
- **System Information**: OS, CPU serial, host, uptime
- **API Statistics**: Request counts, success rates, error tracking
- **Admin Key**: Secure access credential (keep confidential!)

---

## 🛣️ Routes

### Public Endpoints

#### `POST /verify`
**Purpose:** Validate license keys and bind to hardware
**Authentication:** None required

**Request Body:**
```json
{
  "key": "LIC-XXXXXXXXXX",
  "hwid": "hardware-identifier"
}
```

**Responses:**
- `200` Success - License valid
- `400` Bad Request - Missing fields
- `401` Unauthorized - Invalid key
- `403` Forbidden - HWID mismatch
- `410` Gone - License expired

**Success Response:**
```json
{
  "valid": true,
  "expires_at": "2025-12-31",
  "plan": "premium"
}
```

### Admin Endpoints
**All admin endpoints require:** `Authorization: Bearer YOUR_ADMIN_KEY`

#### `POST /api/generate`
**Purpose:** Generate new license keys

**Request Body:**
```json
{
  "hwid": "hardware-identifier",
  "expires_at": "2025-12-31",
  "plan": "basic"
}
```

**Response:**
```json
{
  "key": "LIC-NEWGENERATEDKEY",
  "expires_at": "2025-12-31"
}
```

#### `DELETE /api/delete`
**Purpose:** Delete license keys

**Request Body:**
```json
{
  "key": "LIC-KEYTODELETE"
}
```

#### `PATCH /api/resethwid`
**Purpose:** Reset hardware ID binding

**Request Body:**
```json
{
  "key": "LIC-KEYTORESET"
}
```

#### `GET /api/keyinfo`
**Purpose:** Get license usage information

**Query Parameters:**
- `key` - License key to query

**Response:**
```json
{
  "ip": "192.168.1.100",
  "user_agent": "MyApp/1.0",
  "hwid": "hardware-id",
  "geo_country": "US",
  "first_login": "2025-01-01 10:00:00",
  "last_login": "2025-01-15 14:30:00",
  "login_count": 25
}
```

---

## 🎉 Enjoy

### Security Features
- **Hardware ID Binding**: Prevents license sharing across devices
- **Automatic HWID Detection**: Cross-platform hardware fingerprinting
- **Geolocation Tracking**: Monitor license usage by country
- **Usage Analytics**: Comprehensive logging and statistics
- **Secure Admin Access**: Token-based authentication for management

### Integration Examples

#### Python Client
```python
import requests

def verify_license(key, hwid):
    response = requests.post('http://localhost:5000/verify', json={
        'key': key,
        'hwid': hwid
    })
    return response.json() if response.status_code == 200 else None
```

#### JavaScript Client
```javascript
async function verifyLicense(key, hwid) {
    try {
        const response = await fetch('http://localhost:5000/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key, hwid })
        });
        return response.ok ? await response.json() : null;
    } catch (error) {
        console.error('License verification failed:', error);
        return null;
    }
}
```

### Production Deployment Tips
1. **Use HTTPS** in production environments
2. **Set up reverse proxy** (nginx/Apache) for better performance
3. **Configure firewall** to restrict admin endpoint access
4. **Regular database backups** to prevent license data loss
5. **Monitor logs** for suspicious activity
6. **Use environment variables** for sensitive configuration

### Support & Contributing
- **Issues**: Report bugs and feature requests
- **Documentation**: Expand examples and use cases  
- **Security**: Report vulnerabilities responsibly

---

**🔐 CerberAuth - Securing your software, one license at a time!**
