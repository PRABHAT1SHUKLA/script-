print("\n" + "=" * 70)
print("6. ERROR HANDLING")
print("=" * 70)

def safe_divide(a, b):
    """Division with error handling"""
    try:
        result = a / b
        print(f"  {a} / {b} = {result}")
        return result
    except ZeroDivisionError:
        print(f"  Error: Cannot divide {a} by zero!")
        return None
    except TypeError:
        print(f"  Error: Invalid types - {type(a)}, {type(b)}")
        return None
    finally:
        print(f"  Division operation completed")

print("\nError Handling Examples:")
safe_divide(10, 2)
safe_divide(10, 0)
safe_divide("10", 2)

