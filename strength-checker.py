import re

def check_password_strength(password):
    score = 0
    feedback = []
    
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Use at least 8 characters")
    
    if re.search(r"[a-z]", password) and re.search(r"[A-Z]", password):
        score += 1
    else:
        feedback.append("Use both uppercase and lowercase")
    
    if re.search(r"\d", password):
        score += 1
    else:
        feedback.append("Include numbers")
    
    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        score += 1
    else:
        feedback.append("Include special characters")
    
    strength = ["Weak", "Fair", "Good", "Strong"][min(score-1, 3)] if score > 0 else "Very Weak"
    print(f"Strength: {strength}")
    for tip in feedback:
        print(f"- {tip}")

check_password_strength("Test123!")
