from app.executor import execute_tests

if __name__ == "__main__":
    report = execute_tests()
    print("Report generated:")
    print(report)