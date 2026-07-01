import sys

def main():
    try:
        # Try reading as UTF-16 LE
        with open("server_output.log", "r", encoding="utf-16-le") as f:
            lines = f.readlines()
            print("=== Last 100 lines of server log (UTF-16-LE) ===")
            for line in lines[-100:]:
                print(line, end="")
    except Exception as e:
        print(f"Failed to read as UTF-16-LE: {e}")
        try:
            with open("server_output.log", "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                print("=== Last 100 lines of server log (UTF-8) ===")
                for line in lines[-100:]:
                    print(line, end="")
        except Exception as e2:
            print(f"Failed to read as UTF-8: {e2}")

if __name__ == "__main__":
    main()
