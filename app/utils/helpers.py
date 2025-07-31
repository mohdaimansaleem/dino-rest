"""
Helper utility functions
"""
import re
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import hashlib
import secrets
import string


def generate_unique_id() -> str:
    """Generate a unique ID"""
    return str(uuid.uuid4())


def generate_short_id(length: int = 8) -> str:
    """Generate a short unique ID"""
    return secrets.token_urlsafe(length)[:length]


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    # Check if it's between 10-15 digits
    return 10 <= len(digits_only) <= 15


def format_phone(phone: str) -> str:
    """Format phone number to standard format"""
    digits_only = re.sub(r'\D', '', phone)
    if len(digits_only) == 10:
        return f"+1{digits_only}"  # Assume US number
    elif len(digits_only) == 11 and digits_only.startswith('1'):
        return f"+{digits_only}"
    else:
        return f"+{digits_only}"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove or replace unsafe characters
    filename = re.sub(r'[^\w\s-.]', '', filename)
    filename = re.sub(r'[-\s]+', '-', filename)
    return filename.strip('-.')


def generate_slug(text: str) -> str:
    """Generate URL-friendly slug from text"""
    # Convert to lowercase and replace spaces with hyphens
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in kilometers"""
    from math import radians, cos, sin, asin, sqrt
    
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format amount as currency"""
    if currency == "USD":
        return f"${amount:.2f}"
    elif currency == "EUR":
        return f"€{amount:.2f}"
    elif currency == "GBP":
        return f"£{amount:.2f}"
    elif currency == "INR":
        return f"₹{amount:.2f}"
    else:
        return f"{amount:.2f} {currency}"


def format_time_ago(dt: datetime) -> str:
    """Format datetime as 'time ago' string"""
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 0:
        if diff.days == 1:
            return "1 day ago"
        else:
            return f"{diff.days} days ago"
    
    hours = diff.seconds // 3600
    if hours > 0:
        if hours == 1:
            return "1 hour ago"
        else:
            return f"{hours} hours ago"
    
    minutes = (diff.seconds % 3600) // 60
    if minutes > 0:
        if minutes == 1:
            return "1 minute ago"
        else:
            return f"{minutes} minutes ago"
    
    return "Just now"


def format_duration(minutes: int) -> str:
    """Format duration in minutes to human readable format"""
    if minutes < 60:
        return f"{minutes} min"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if remaining_minutes == 0:
        return f"{hours}h"
    else:
        return f"{hours}h {remaining_minutes}m"


def generate_order_number() -> str:
    """Generate a unique order number"""
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    random_part = ''.join(secrets.choice(string.digits) for _ in range(4))
    return f"ORD{timestamp}{random_part}"


def hash_string(text: str, salt: str = "") -> str:
    """Generate hash of a string with optional salt"""
    return hashlib.sha256((text + salt).encode()).hexdigest()


def mask_email(email: str) -> str:
    """Mask email for privacy (e.g., j***@example.com)"""
    if '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        masked_local = local[0] + '*'
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    """Mask phone number for privacy"""
    digits_only = re.sub(r'\D', '', phone)
    if len(digits_only) < 4:
        return phone
    
    return f"***-***-{digits_only[-4:]}"


def validate_password_strength(password: str) -> Dict[str, Any]:
    """Validate password strength and return feedback"""
    feedback = {
        "is_valid": True,
        "score": 0,
        "issues": []
    }
    
    # Check length
    if len(password) < 8:
        feedback["issues"].append("Password must be at least 8 characters long")
        feedback["is_valid"] = False
    else:
        feedback["score"] += 1
    
    # Check for uppercase
    if not re.search(r'[A-Z]', password):
        feedback["issues"].append("Password must contain at least one uppercase letter")
    else:
        feedback["score"] += 1
    
    # Check for lowercase
    if not re.search(r'[a-z]', password):
        feedback["issues"].append("Password must contain at least one lowercase letter")
    else:
        feedback["score"] += 1
    
    # Check for digits
    if not re.search(r'\d', password):
        feedback["issues"].append("Password must contain at least one number")
    else:
        feedback["score"] += 1
    
    # Check for special characters
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        feedback["issues"].append("Password must contain at least one special character")
    else:
        feedback["score"] += 1
    
    # Overall strength
    if feedback["score"] >= 4 and len(password) >= 8:
        feedback["strength"] = "Strong"
    elif feedback["score"] >= 3:
        feedback["strength"] = "Medium"
    else:
        feedback["strength"] = "Weak"
        feedback["is_valid"] = False
    
    return feedback


def paginate_results(items: List[Any], page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    """Paginate a list of items"""
    total_items = len(items)
    total_pages = (total_items + per_page - 1) // per_page
    
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    
    paginated_items = items[start_index:end_index]
    
    return {
        "items": paginated_items,
        "pagination": {
            "current_page": page,
            "per_page": per_page,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


def clean_dict(data: Dict[str, Any], remove_none: bool = True, remove_empty: bool = False) -> Dict[str, Any]:
    """Clean dictionary by removing None or empty values"""
    cleaned = {}
    
    for key, value in data.items():
        if remove_none and value is None:
            continue
        if remove_empty and value == "":
            continue
        if isinstance(value, dict):
            cleaned_value = clean_dict(value, remove_none, remove_empty)
            if cleaned_value:  # Only add if not empty
                cleaned[key] = cleaned_value
        else:
            cleaned[key] = value
    
    return cleaned


def get_business_hours_status(current_time: datetime = None) -> Dict[str, Any]:
    """Get business hours status (can be customized per cafe)"""
    if current_time is None:
        current_time = datetime.utcnow()
    
    # Default business hours (can be made configurable)
    open_hour = 9  # 9 AM
    close_hour = 22  # 10 PM
    
    current_hour = current_time.hour
    is_open = open_hour <= current_hour < close_hour
    
    if is_open:
        close_time = current_time.replace(hour=close_hour, minute=0, second=0, microsecond=0)
        time_until_close = close_time - current_time
        status = "Open"
        message = f"Closes in {format_duration(int(time_until_close.total_seconds() // 60))}"
    else:
        if current_hour < open_hour:
            # Before opening
            open_time = current_time.replace(hour=open_hour, minute=0, second=0, microsecond=0)
            time_until_open = open_time - current_time
            status = "Closed"
            message = f"Opens in {format_duration(int(time_until_open.total_seconds() // 60))}"
        else:
            # After closing
            next_open = (current_time + timedelta(days=1)).replace(hour=open_hour, minute=0, second=0, microsecond=0)
            time_until_open = next_open - current_time
            status = "Closed"
            message = f"Opens in {format_duration(int(time_until_open.total_seconds() // 60))}"
    
    return {
        "is_open": is_open,
        "status": status,
        "message": message,
        "open_hour": open_hour,
        "close_hour": close_hour
    }