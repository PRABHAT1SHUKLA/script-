def read_numbers(n):
    """Generate numbers"""
    for i in range(1, n + 1):
        yield i

def filter_even(numbers):
    """Filter even numbers"""
    for num in numbers:
        if num % 2 == 0:
            yield num

def square(numbers):
    """Square each number"""
    for num in numbers:
        yield num ** 2

def format_output(numbers):
    """Format as string"""
    for num in numbers:
        yield f"Result: {num}"

print("4. GENERATOR PIPELINE")
pipeline = format_output(square(filter_even(read_numbers(10))))
for item in pipeline:
    print(f"  {item}")
print()
