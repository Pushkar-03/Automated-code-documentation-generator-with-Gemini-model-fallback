import unittest

from code_utils import analyze_python_source, insert_docstrings


class CodeUtilsTests(unittest.TestCase):
    def test_detects_functions_and_classes(self):
        source = "class Example:\n    def run(self):\n        return True\n"
        result = analyze_python_source(source)
        self.assertEqual(result["class_count"], 1)
        self.assertEqual(result["function_count"], 1)

    def test_inserts_module_class_and_method_docstrings(self):
        source = "class Example:\n    def run(self):\n        return True\n"
        result = analyze_python_source(source)
        docs = {item["id"]: f"Documentation for {item['id']}." for item in result["targets"]}
        updated, count = insert_docstrings(source, result["targets"], docs)
        compile(updated, "generated.py", "exec")
        self.assertEqual(count, 3)
        self.assertIn('"Documentation for module."', updated)
        self.assertIn('"Documentation for Example."', updated)
        self.assertIn('"Documentation for Example.run."', updated)

    def test_preserves_existing_docstrings(self):
        source = 'def run():\n    """Existing documentation."""\n    return True\n'
        result = analyze_python_source(source)
        docs = {item["id"]: "New documentation." for item in result["targets"]}
        updated, count = insert_docstrings(source, result["targets"], docs)
        self.assertEqual(count, 1)
        self.assertIn('"""Existing documentation."""', updated)

    def test_handles_one_line_function(self):
        source = "def add(a, b): return a + b\n"
        result = analyze_python_source(source)
        docs = {item["id"]: f"Documentation for {item['id']}." for item in result["targets"]}
        updated, _ = insert_docstrings(source, result["targets"], docs)
        compile(updated, "one_line.py", "exec")
        self.assertIn('def add(a, b): "Documentation for add.";', updated)

    def test_rejects_invalid_python(self):
        with self.assertRaises(Exception):
            analyze_python_source("def broken(:\n    pass\n")


if __name__ == "__main__":
    unittest.main()
