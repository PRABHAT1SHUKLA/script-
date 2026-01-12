import sys

def greet(name):
    print(f"Hello, {name}!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        greet(sys.argv[1])
    else:
        print("Usage: python $PYTHON_SCRIPT <name>")
EOF

# Make the Python script executable
chmod +x $PYTHON_SCRIPT

# Run the Python script using bash to execute it
./$PYTHON_SCRIPT World

# Clean up the created script file
rm $PYTHON_SCRIPT
