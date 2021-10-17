__all__ = ['CCOFPTestCase']
import unittest
import sys
from io import StringIO
from ccofp import get_code_complexity


sequential = """\
def f(n):
    k = n + 4
    s = k + n
    return s
"""


sequential_unencapsulated = """\
k = 2 + 4
s = k + 3
"""


if_elif_else_dead_path = """\
def f(n):
    if n > 3:
        return "bigger than three"
    elif n > 4:
        return "is never executed"
    else:
        return "smaller than or equal to three"
"""


for_loop = """\
def f():
    for i in range(10):
        print(i)
"""


for_else = """\
def f(mylist):
    for i in mylist:
        print(i)
    else:
        print(None)
"""


recursive = """\
def f(n):
    if n > 4:
        return f(n - 1)
    else:
        return n
"""


def get_complexity_number(snippet, strio, max=0):
    """Get the complexity number from the printed string."""
    # Report from the lowest complexity number.
    get_code_complexity(snippet, max)
    strio_val = strio.getvalue()
    if strio_val:
        return int(strio_val.split()[-1].strip("()"))
    else:
        return None


class CCOFPTestCase(unittest.TestCase):
    def setUp(self):
        self._orig_stdout = sys.stdout
        sys.stdout = self.strio = StringIO()

    def tearDown(self):
        self.strio.close()
        sys.stdout = self._orig_stdout

    def assert_complexity(self, snippet, max):
        complexity = get_complexity_number(snippet, self.strio)
        self.assertEqual(complexity, max)

        infunc = 'def f():\n    ' + snippet.replace('\n', '\n    ')
        complexity = get_complexity_number(infunc, self.strio)
        self.assertEqual(complexity, max)

    def test_sequential_snippet(self):
        complexity = get_complexity_number(sequential, self.strio)
        self.assertEqual(complexity, 1)

    def test_sequential_unencapsulated_snippet(self):
        complexity = get_complexity_number(sequential_unencapsulated, self.strio)
        self.assertEqual(complexity, None)

    def test_if_elif_else_dead_path_snippet(self):
        complexity = get_complexity_number(if_elif_else_dead_path, self.strio)
        self.assertEqual(complexity, 3)

    def test_for_loop_snippet(self):
        complexity = get_complexity_number(for_loop, self.strio)
        self.assertEqual(complexity, 2)

    def test_for_else_snippet(self):
        complexity = get_complexity_number(for_else, self.strio)
        self.assertEqual(complexity, 2)

