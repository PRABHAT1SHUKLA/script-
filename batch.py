print("\n" + "=" * 70)
print("9. BATCH FILE PROCESSING")
print("=" * 70)

def batch_process():
    """Process multiple files"""
    print("\nBatch Processing Example:")
    
    # Create test files
    for i in range(1, 4):
        with open(f'test_{i}.txt', 'w') as f:
            f.write(f"Test file {i}\n")
    
    # Process all test files
    test_files = [f for f in os.listdir('.') if f.startswith('test_')]
    print(f"  Found {len(test_files)} test files")
    
    for filename in test_files:
        with open(filename, 'r') as f:
            content = f.read()
            print(f"  {filename}: {content.strip()}")
    
    # Cleanup
    for filename in test_files:
        os.remove(filename)
    print("  ✓ Cleaned up test files")

batch_process()

