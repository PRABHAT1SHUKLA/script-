import subprocess

print("\n" + "=" * 70)
print("3. SUBPROCESS - Running External Commands")
print("=" * 70)

def run_commands():
    """Execute external commands"""
    print("\nRunning system commands:")
    
    # Simple command
    result = subprocess.run(['echo', 'Hello from subprocess'], 
                          capture_output=True, text=True)
    print(f"  Output: {result.stdout.strip()}")
    print(f"  Return code: {result.returncode}")
    
    # Get directory listing (cross-platform)
    cmd = ['dir'] if os.name == 'nt' else ['ls', '-la']
    result = subprocess.run(cmd, capture_output=True, text=True, shell=(os.name == 'nt'))
    print(f"\n  Directory listing (first 5 lines):")
    for line in result.stdout.split('\n')[:5]:
        if line.strip():
            print(f"    {line}")

run_commands()

