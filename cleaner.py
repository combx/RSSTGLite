import re
from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse

# List of tracking parameters to remove
TRACKING_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'fbclid', 'gclid', 'yclid', '_openstat', 'action', 'ref', 'from'
}

def clean_url(url: str) -> str:
    """
    Removes tracking parameters from a URL.
    """
    try:
        parsed = urlparse(url)
        query_params = parse_qsl(parsed.query, keep_blank_values=True)
        
        # Filter out tracking parameters
        cleaned_params = [
            (key, value) for key, value in query_params
            if key.lower() not in TRACKING_PARAMS
        ]
        
        # Reconstruct the query string
        clean_query = urlencode(cleaned_params)
        
        # Reconstruct the full URL
        clean_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            clean_query,
            parsed.fragment
        ))
        
        # Remove trailing '?' if query is empty
        if clean_url.endswith('?') and not clean_query:
            clean_url = clean_url[:-1]
            
        return clean_url
    except Exception:
        # If parsing fails, return original URL
        return url
