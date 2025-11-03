print("\n" + "=" * 70)
print("CLEANING UP DEMO FILES")
print("=" * 70)

for f in ['sample.txt', 'data.json']:
    if os.path.exists(f):
        os.remove(f)
        print(f"  Removed {f}")

print("\n✓ All demonstrations completed!")
print("\nKey Takeaways:")
print("  1. Use 'with' statement for file operations")
print("  2. argparse for professional CLI tools")
print("  3. subprocess for running external commands")
print("  4. logging instead of print for production")
print("  5. Always handle errors with try-except")
print("  6. Use pathlib for cross-platform file paths")
print("  7. Regular expressions for text processing")
print("  8. Environment variables for configuration")
