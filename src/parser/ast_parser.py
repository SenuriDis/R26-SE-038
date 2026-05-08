import ast


# parse_python_file reads and parses a Python source file
# into an AST (Abstract Syntax Tree).
#
# AST allows the system to analyze code structure
# without executing the program.
def parse_python_file(file_path):

    try:

        # Open Python source file using UTF-8 encoding
        with open(file_path, "r", encoding="utf-8") as file:

            # Read entire source code as text
            source_code = file.read()

        # Convert source code into AST representation
        tree = ast.parse(source_code)

        # Return both AST tree and raw source code
        return tree, source_code

    # Handles missing file errors
    except FileNotFoundError:

        print(f"Error: File not found -> {file_path}")

        return None, None

    # Handles invalid Python syntax errors
    except SyntaxError as error:

        print(f"Syntax Error while parsing {file_path}: {error}")

        return None, None

    # Handles any unexpected runtime errors
    except Exception as error:

        print(f"Unexpected error while parsing file: {error}")

        return None, None