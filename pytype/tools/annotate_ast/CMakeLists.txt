add_package()

py_library(
  NAME
    annotate_ast
  SRCS
    annotate_ast.py
  DEPS
    pytype.io
    pytype.libvm
)

py_test(
  NAME
    annotate_ast_test
  SRCS
    annotate_ast_test.py
  DEPS
    .annotate_ast
    pytype.config
    pytype.tests.test_base
)
