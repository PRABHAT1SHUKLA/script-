import sys

print("\n" + "=" * 70)
print("2. COMMAND LINE ARGUMENTS")
print("=" * 70)

# Simple sys.argv example
def simple_cli():
    """Basic command line argument handling"""
    print("\nSimple CLI using sys.argv:")
    print(f"  Script name: {sys.argv[0]}")
    print(f"  Arguments: {sys.argv[1:]}")
    print(f"  Total args: {len(sys.argv) - 1}")

simple_cli()

# Advanced argparse example
import argparse

def advanced_cli_example():
    """Argparse demonstration"""
    print("\nArgparse Example:")
    print("  Usage: python script.py --name Alice --age 30 --verbose")
    
    parser = argparse.ArgumentParser(description='Process user data')
    parser.add_argument('--name', type=str, help='User name')
    parser.add_argument('--age', type=int, help='User age')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    # Simulate arguments for demo
    args = parser.parse_args(['--name', 'Bob', '--age', '25', '--verbose'])
    
    print(f"  Parsed: name={args.name}, age={args.age}, verbose={args.verbose}")

advanced_cli_example()
