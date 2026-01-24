import re
from urllib.parse import urlparse
import tldextract

class SuspiciousURLDetector:
    def __init__(self):
        self.suspicious_keywords = [
            'login', 'signin', 'account', 'verify', 'secure', 'update',
            'confirm', 'banking', 'paypal', 'amazon', 'apple', 'microsoft',
            'suspended', 'limited', 'urgent', 'alert', 'winner'
        ]
        
        self.suspicious_tlds = [
            '.tk', '.ml', '.ga', '.cf', '.gq', '.xyz', '.top', '.work'
        ]
        
        self.trusted_domains = [
            'google.com', 'facebook.com', 'amazon.com', 'paypal.com',
            'microsoft.com', 'apple.com', 'github.com', 'linkedin.com'
        ]
    
    def analyze_url(self, url):
        score = 0
        flags = []
        
        parsed = urlparse(url)
        extracted = tldextract.extract(url)
        domain = extracted.domain + '.' + extracted.suffix
        
        if self._check_ip_address(parsed.netloc):
            score += 30
            flags.append("Uses IP address instead of domain name")
        
        if self._check_suspicious_length(url):
            score += 20
            flags.append("Unusually long URL (potential obfuscation)")
        
        if self._check_suspicious_tld(extracted.suffix):
            score += 25
            flags.append(f"Suspicious TLD: .{extracted.suffix}")
        
        if self._check_excessive_subdomains(extracted.subdomain):
            score += 15
            flags.append("Excessive subdomains")
        
        if self._check_suspicious_keywords(url):
            score += 20
            flags.append("Contains suspicious keywords")
        
        if self._check_homograph_attack(domain):
            score += 35
            flags.append("Possible homograph/lookalike attack")
        
        if self._check_url_shortener(domain):
            score += 10
            flags.append("URL shortener detected")
        
        if self._check_special_characters(url):
            score += 15
            flags.append("Contains special characters (@, -, _)")
        
        if self._check_https(parsed.scheme):
            score -= 10
        else:
            flags.append("No HTTPS encryption")
        
        risk_level = self._calculate_risk_level(score)
        
        return {
            'url': url,
            'score': max(0, score),
            'risk_level': risk_level,
            'flags': flags,
            'domain': domain
        }
    
    def _check_ip_address(self, netloc):
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        return bool(re.search(ip_pattern, netloc))
    
    def _check_suspicious_length(self, url):
        return len(url) > 75
    
    def _check_suspicious_tld(self, tld):
        return f'.{tld}' in self.suspicious_tlds
    
    def _check_excessive_subdomains(self, subdomain):
        if not subdomain:
            return False
        return subdomain.count('.') >= 3
    
    def _check_suspicious_keywords(self, url):
        url_lower = url.lower()
        return any(keyword in url_lower for keyword in self.suspicious_keywords)
    
    def _check_homograph_attack(self, domain):
        suspicious_chars = ['х', 'с', 'е', 'а', 'р', 'о', 'у', 'і']
        return any(char in domain for char in suspicious_chars)
    
    def _check_url_shortener(self, domain):
        shorteners = ['bit.ly', 'tinyurl.com', 'goo.gl', 't.co', 'ow.ly']
        return domain in shorteners
    
    def _check_special_characters(self, url):
        return '@' in url or url.count('-') > 4 or url.count('_') > 3
    
    def _check_https(self, scheme):
        return scheme == 'https'
    
    def _calculate_risk_level(self, score):
        if score >= 60:
            return "HIGH"
        elif score >= 30:
            return "MEDIUM"
        elif score >= 10:
            return "LOW"
        else:
            return "SAFE"
    
    def print_report(self, result):
        print(f"\n{'='*60}")
        print(f"URL Analysis Report")
        print(f"{'='*60}")
        print(f"URL: {result['url']}")
        print(f"Domain: {result['domain']}")
        print(f"Risk Score: {result['score']}/100")
        print(f"Risk Level: {result['risk_level']}")
        print(f"\nFlags Detected ({len(result['flags'])}):")
        if result['flags']:
            for flag in result['flags']:
                print(f"  - {flag}")
        else:
            print("  No suspicious indicators found")
        print(f"{'='*60}\n")

def main():
    detector = SuspiciousURLDetector()
    
    test_urls = [
        "https://www.google.com",
        "http://paypal-verify-account.tk/login",
        "https://192.168.1.1/admin",
        "http://secure-login-microsoft-account-verify.com/update",
        "https://amaz0n.com/winner",
        "http://subdomain.another.third.example.com/page"
    ]
    
    print("Suspicious Website Detection Tool")
    print("Analyzing test URLs...\n")
    
    for url in test_urls:
        result = detector.analyze_url(url)
        detector.print_report(result)

if __name__ == "__main__":
    main()
