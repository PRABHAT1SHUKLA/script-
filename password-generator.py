import random
import string
import pyperclip  # pip install pyperclip

def generate_password(length=16, use_upper=True, use_lower=True, 
                      use_digits=True, use_special=True):
    """Generate a secure random password."""
    characters = ""
    
    if use_upper:
        characters += string.ascii_uppercase
    if use_lower:
        characters += string.ascii_lowercase
    if use_digits:
        characters += string.digits
    if use_special:
        characters += string.punctuation
    
    if not characters:
        raise ValueError("At least one character type must be selected")
    
    # Ensure at least one of each selected type
    password = []
    if use_upper:
        password.append(random.choice(string.ascii_uppercase))
    if use_lower:
        password.append(random.choice(string.ascii_lowercase))
    if use_digits:
        password.append(random.choice(string.digits))
    if use_special:
        password.append(random.choice(string.punctuation))
    
    # Fill remaining length
    for _ in range(length - len(password)):
        password.append(random.choice(characters))
    
    random.shuffle(password)
    password = ''.join(password)
    
    # Copy to clipboard
    pyperclip.copy(password)
    print(f"Generated Password: {password}")
    print("✓ Password copied to clipboard!")
    
    return password

if __name__ == "__main__":
    generate_password(20)
