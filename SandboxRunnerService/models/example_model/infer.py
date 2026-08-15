import sys

if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else ""
    print("MODEL OUTPUT:", text.upper())