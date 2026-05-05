import ast


def parse_python_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            source_code = file.read()

        tree = ast.parse(source_code)
        return tree, source_code

    except FileNotFoundError:
        print(f"Error: File not found -> {file_path}")
        return None, None
    except SyntaxError as error:
        print(f"Syntax Error while parsing {file_path}: {error}")
        return None, None
    except Exception as error:
        print(f"Unexpected error while parsing file: {error}")
        return None, None