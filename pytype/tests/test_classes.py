"""Tests for classes."""

import unittest

from pytype import utils
from pytype.tests import test_inference


class ClassesTest(test_inference.InferenceTest):
  """Tests for classes."""

  def testClassDecorator(self):
    ty = self.Infer("""
      @__any_object__
      class MyClass(object):
        def method(self, response):
          pass
      def f():
        return MyClass()
    """, deep=True, solve_unknowns=True, extract_locals=False)
    self.assertTypesMatchPytd(ty, """
      # "function" because it gets called in f()
      MyClass = ...  # type: function
      def f() -> ?
    """)

  def testClassName(self):
    ty = self.Infer("""
      class MyClass(object):
        def __init__(self, name):
          pass
      def f():
        factory = MyClass
        return factory("name")
      f()
    """, deep=False, solve_unknowns=False, extract_locals=False)
    self.assertTypesMatchPytd(ty, """
    class MyClass(object):
      def __init__(self, name: str) -> NoneType

    def f() -> MyClass
    """)

  def testInheritFromUnknown(self):
    ty = self.Infer("""
      class A(__any_object__):
        pass
    """, deep=False, solve_unknowns=False, extract_locals=True)
    self.assertTypesMatchPytd(ty, """
    class A(?):
      pass
    """)

  def testInheritFromUnknownAndCall(self):
    ty = self.Infer("""
      x = __any_object__
      class A(x):
        def __init__(self):
          x.__init__(self)
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
    x = ...  # type: ?
    class A(?):
      def __init__(self) -> NoneType
    """)

  def testInheritFromUnknownAndSetAttr(self):
    ty = self.Infer("""
      class Foo(__any_object__):
        def __init__(self):
          setattr(self, "test", True)
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
    class Foo(?):
      def __init__(self) -> NoneType
    """)

  def testInheritFromUnknownAndInitialize(self):
    ty = self.Infer("""
      class Foo(object):
        pass
      class Bar(Foo, __any_object__):
        pass
      x = Bar(duration=0)
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
      class Foo(object):
        pass
      class Bar(Foo, Any):
        pass
      x = ...  # type: Bar
    """)

  def testInheritFromUnsolvable(self):
    with utils.Tempdir() as d:
      d.create_file("a.pyi", """
        def __getattr__(name) -> Any
      """)
      ty = self.Infer("""
        import a
        class Foo(object):
          pass
        class Bar(Foo, a.A):
          pass
        x = Bar(duration=0)
      """, pythonpath=[d.path], deep=True, solve_unknowns=True)
      self.assertTypesMatchPytd(ty, """
        a = ...  # type: module
        class Foo(object):
          pass
        class Bar(Foo, Any):
          pass
        x = ...  # type: Bar
      """)

  def testClassMethod(self):
    ty = self.Infer("""
      module = __any_object__
      class Foo(object):
        @classmethod
        def bar(cls):
          module.bar("", '%Y-%m-%d')
      def f():
        return Foo.bar()
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
    module = ...  # type: ?
    def f() -> NoneType
    class Foo(object):
      # TODO(kramm): pytd needs better syntax for classmethods
      bar = ...  # type: classmethod
    """)

  def testInheritFromUnknownAttributes(self):
    ty = self.Infer("""
      class Foo(__any_object__):
        def f(self):
          self.x = [1]
          self.y = list(self.x)
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
    class Foo(?):
      x = ...  # type: List[int, ...]
      y = ...  # type: List[int, ...]
      def f(self) -> NoneType
    """)

  def testInnerClass(self):
    ty = self.Infer("""
      def f():
        class Foo(object):
          x = 3
        l = Foo()
        return l.x
    """, deep=True, solve_unknowns=False, extract_locals=False)
    self.assertTypesMatchPytd(ty, """
      def f() -> int
    """)

  def testSuper(self):
    ty = self.Infer("""
      class Base(object):
        def __init__(self, x, y):
          pass
      class Foo(Base):
        def __init__(self, x):
          super(Foo, self).__init__(x, y='foo')
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
    class Base(object):
      def __init__(self, x, y) -> NoneType
    class Foo(Base):
      def __init__(self, x) -> NoneType
    """)

  @unittest.skip("Fails, needs 'raises' support.")
  def testSuperError(self):
    self.assertNoErrors("""
      class Base(object):
        def __init__(self, x, y, z):
          pass
      class Foo(Base):
        def __init__(self, x):
          super(Foo, self).__init__()
    """, raises=ValueError)

  def testSuperInInit(self):
    ty = self.Infer("""
      class A(object):
        def __init__(self):
          self.x = 3

      class B(A):
        def __init__(self):
          super(B, self).__init__()

        def get_x(self):
          return self.x
    """, deep=True, solve_unknowns=False, extract_locals=False)
    self.assertTypesMatchPytd(ty, """
        class A(object):
          x = ...  # type: int

        class B(A):
          # TODO(kramm): optimize this out
          x = ...  # type: int
          def get_x(self) -> int
    """)

  def testSuperDiamond(self):
    ty = self.Infer("""
      class A(object):
        x = 1
      class B(A):
        y = 4
      class C(A):
        y = "str"
        z = 3j
      class D(B, C):
        def get_x(self):
          return super(D, self).x
        def get_y(self):
          return super(D, self).y
        def get_z(self):
          return super(D, self).z
    """, deep=True, solve_unknowns=False, extract_locals=True)
    self.assertTypesMatchPytd(ty, """
      class A(object):
          x = ...  # type: int
      class B(A):
          y = ...  # type: int
      class C(A):
          y = ...  # type: str
          z = ...  # type: complex
      class D(B, C):
          def get_x(self) -> int
          def get_y(self) -> int
          def get_z(self) -> complex
    """)

  def testInheritFromList(self):
    ty = self.Infer("""
      class MyList(list):
        def foo(self):
          return getattr(self, '__str__')
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
      class MyList(list):
        def foo(self) -> ?
    """)

  def testClassAttr(self):
    ty = self.Infer("""
      class Foo(object):
        pass
      OtherFoo = Foo().__class__
      Foo.x = 3
      OtherFoo.x = "bar"
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
      class Foo(object):
        # TODO(kramm): should be just "str". Also below.
        x = ...  # type: int or str
      # TODO(kramm): Should this be an alias?
      class OtherFoo(object):
        x = ...  # type: int or str
    """)

  def testCallClassAttr(self):
    ty = self.Infer("""
      class Flag(object):
        convert_method = int
        def convert(self, value):
          return self.convert_method(value)
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
      class Flag(object):
        convert_method = ...  # type: Type[int]
        def convert(self, value: float or str) -> int
    """)

  def testBoundMethod(self):
    ty = self.Infer("""
      class Random(object):
          def seed(self):
            pass

      _inst = Random()
      seed = _inst.seed
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
    class Random(object):
       def seed(self) -> None: ...

    _inst = ...  # type: Random
    seed = ...  # type: function
    """)

  def testMROWithUnsolvables(self):
    ty = self.Infer("""
      from nowhere import X, Y  # pytype: disable=import-error
      class Foo(Y):
        pass
      class Bar(X, Foo, Y):
        pass
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
      X = ...  # type: ?
      Y = ...  # type: ?
      class Foo(?):
        ...
      class Bar(?, Foo, ?):
        ...
    """)

  def testProperty(self):
    ty = self.Infer("""
      class Foo(object):
        def __init__(self):
          self._name = "name"
        def test(self):
          return self.name
        name = property(fget=lambda self: self._name)
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
      class Foo(object):
        _name = ...  # type: str
        name = ...  # type: property
        def test(self) -> str: ...
    """)

  def testDescriptorSelf(self):
    ty = self.Infer("""
      class Foo(object):
        def __init__(self):
          self._name = "name"
        def __get__(self, obj, objtype):
          return self._name
      class Bar(object):
        def test(self):
          return self.foo
        foo = Foo()
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
      class Foo(object):
        _name = ...  # type: str
        def __get__(self, obj, objtype) -> str: ...
      class Bar(object):
        foo = ...  # type: Foo
        def test(self) -> str: ...
    """)

  def testDescriptorInstance(self):
    ty = self.Infer("""
      class Foo(object):
        def __get__(self, obj, objtype):
          return obj._name
      class Bar(object):
        def __init__(self):
          self._name = "name"
        def test(self):
          return self.foo
        foo = Foo()
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
      class Foo(object):
        def __get__(self, obj, objtype) -> Any: ...
      class Bar(object):
        _name = ...  # type: str
        foo = ...  # type: Foo
        def test(self) -> str: ...
    """)

  def testDescriptorClass(self):
    ty = self.Infer("""
      class Foo(object):
        def __get__(self, obj, objtype):
          return objtype._name
      class Bar(object):
        def test(self):
          return self.foo
        _name = "name"
        foo = Foo()
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
      class Foo(object):
        def __get__(self, obj, objtype) -> Any: ...
      class Bar(object):
        _name = ...  # type: str
        foo = ...  # type: Foo
        def test(self) -> str: ...
    """)

  def testGetAttr(self):
    ty = self.Infer("""
      class Foo(object):
        def __getattr__(self, name):
          return "attr"
      def f():
        return Foo().foo
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
      class Foo(object):
        def __getattr__(self, name) -> str: ...
      def f() -> str: ...
    """)

  def testGetAttrPyi(self):
    with utils.Tempdir() as d:
      d.create_file("foo.pyi", """
        class Foo(object):
          def __getattr__(self, name) -> str
      """)
      ty = self.Infer("""
        import foo
        def f():
          return foo.Foo().foo
      """, pythonpath=[d.path], deep=True, solve_unknowns=True)
      self.assertTypesMatchPytd(ty, """
        foo = ...  # type: module
        def f() -> str
      """)

  def testGetAttribute(self):
    ty = self.Infer("""
      class A(object):
        def __getattribute__(self, name):
          return 42
      x = A().x
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
      class A(object):
        def __getattribute__(self, name) -> int
      x = ...  # type: int
    """)

  def testGetAttributePyi(self):
    with utils.Tempdir() as d:
      d.create_file("a.pyi", """
        class A(object):
          def __getattribute__(self, name) -> int
      """)
      ty = self.Infer("""
        import a
        x = a.A().x
      """, pythonpath=[d.path], deep=True, solve_unknowns=True)
      self.assertTypesMatchPytd(ty, """
        a = ...  # type: module
        x = ...  # type: int
      """)

  def testInheritFromClassobj(self):
    with utils.Tempdir() as d:
      d.create_file("a.pyi", """
        class A():
          pass
      """)
      ty = self.Infer("""
        import a
        class C(a.A):
          pass
        name = C.__name__
      """, pythonpath=[d.path], deep=True, solve_unknowns=True)
      self.assertTypesMatchPytd(ty, """
        a = ... # type: module
        class C(a.A):
          pass
        name = ... # type: str
      """)

  def testMetaclassGetAttribute(self):
    with utils.Tempdir() as d:
      d.create_file("enum.pyi", """
        class EnumMeta(type):
          def __getattribute__(self, name) -> Any
        class Enum(metaclass=EnumMeta): ...
        class IntEnum(int, Enum): ...
      """)
      ty = self.Infer("""
        import enum
        class A(enum.Enum):
          x = 1
        class B(enum.IntEnum):
          x = 1
        enum1 = A.x
        name1 = A.x.name
        enum2 = B.x
        name2 = B.x.name
      """, pythonpath=[d.path])
      self.assertTypesMatchPytd(ty, """
        enum = ...  # type: module
        class A(enum.Enum):
          x = ...  # type: int
        class B(enum.IntEnum):
          x = ...  # type: int
        enum1 = ...  # type: Any
        name1 = ...  # type: Any
        enum2 = ...  # type: Any
        name2 = ...  # type: Any
      """)

  def testReturnClassType(self):
    with utils.Tempdir() as d:
      d.create_file("a.pyi", """
        class A(object):
          x = ...  # type: int
        class B(object):
          x = ...  # type: str
        def f(x: Type[A]) -> Type[A]
        def g() -> Type[A or B]
        def h() -> Type[int or B]
      """)
      ty = self.Infer("""
        import a
        x1 = a.f(a.A).x
        x2 = a.g().x
        x3 = a.h().x
      """, pythonpath=[d.path], deep=True, solve_unknowns=True)
      self.assertTypesMatchPytd(ty, """
        a = ...  # type: module
        x1 = ...  # type: int
        x2 = ...  # type: int or str
        x3 = ...  # type: str
      """)

  def testCallClassType(self):
    with utils.Tempdir() as d:
      d.create_file("a.pyi", """
        class A(object): ...
        class B(object):
          MyA = ...  # type: Type[A]
      """)
      ty = self.Infer("""
        import a
        x = a.B.MyA()
      """, pythonpath=[d.path], deep=True, solve_unknowns=True)
      self.assertTypesMatchPytd(ty, """
        a = ...  # type: module
        x = ...  # type: a.A
      """)

  def testCallAlias(self):
    ty = self.Infer("""
      class A: pass
      B = A
      x = B()
    """)
    # We don't care whether the type of x is inferred as A or B, but we want it
    # to always be the same.
    self.assertTypesMatchPytd(ty, """
      class A: ...
      class B: ...
      x = ...  # type: A
    """)

  def testNew(self):
    with utils.Tempdir() as d:
      d.create_file("a.pyi", """
        class A(object):
          def __new__(cls, x: int) -> B
        class B: ...
      """)
      ty = self.Infer("""
        import a
        class C(object):
          def __new__(cls):
            return "hello world"
        x1 = a.A(42)
        x2 = C()
        x3 = object.__new__(bool)
      """, pythonpath=[d.path], deep=True, solve_unknowns=True)
      self.assertTypesMatchPytd(ty, """
        a = ...  # type: module
        class C(object):
          def __new__(cls) -> str
        x1 = ...  # type: a.B
        x2 = ...  # type: str
        x3 = ...  # type: bool
      """)

  def testNewAndInit(self):
    ty = self.Infer("""
      class A(object):
        def __new__(cls, a, b):
          return super(A, cls).__new__(cls, a, b)
        def __init__(self, a, b):
          self.x = a + b
      class B(object):
        def __new__(cls, x):
          v = A(x, 0)
          v.y = False
          return v
        # __init__ should not be called
        def __init__(self, x):
          pass
      x1 = A("hello", "world")
      x2 = x1.x
      x3 = B(3.14)
      x4 = x3.x
      x5 = x3.y
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
      class A(object):
        x = ...  # type: str or int or long or float or complex
        y = ...  # type: bool
        def __new__(cls, a, b) -> Any
        def __init__(self, a: str, b: str) -> None
        def __init__(self, a: float or long or complex, b: float or long or complex) -> None
      class B(object):
        def __new__(cls, x: float or long or complex) -> A
        def __init__(self, x) -> None
      x1 = ...  # type: A
      x2 = ...  # type: str
      x3 = ...  # type: A
      x4 = ...  # type: float
      x5 = ...  # type: bool
    """)

  def testNewAndInitPyi(self):
    with utils.Tempdir() as d:
      d.create_file("a.pyi", """
        T = TypeVar("T")
        N = TypeVar("N")
        class A(Generic[T]):
          def __new__(cls, x) -> A[nothing]
          def __init__(self, x: N):
            self := A[N]
        class B(object):
          def __new__(cls) -> A[str]
          # __init__ should not be called
          def __init__(self, x, y) -> None
      """)
      ty = self.Infer("""
        import a
        x1 = a.A(0)
        x2 = a.B()
      """, pythonpath=[d.path], deep=True, solve_unknowns=True)
      self.assertTypesMatchPytd(ty, """
        a = ...  # type: module
        x1 = ...  # type: a.A[int]
        x2 = ...  # type: a.A[str]
      """)

  def testGetType(self):
    ty = self.Infer("""
      class A:
        x = 3
      def f():
        return A() if __any_object__ else ""
      B = type(A())
      C = type(f())
      D = type(int)
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
      class A:
        x = ...  # type: int
      def f() -> A or str
      class B:
        x = ...  # type: int
      C = ...  # type: Type[A or str]
      D = ...  # type: Type[type]
    """)

  def testTypeAttribute(self):
    ty = self.Infer("""
      class A:
        x = 3
      B = type(A())
      x = B.x
      mro = B.mro()
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
      class A:
        x = ...  # type: int
      class B:
        x = ...  # type: int
      x = ...  # type: int
      mro = ...  # type: list
    """)

  def testTypeSubclass(self):
    ty = self.Infer("""
      class A(type): pass
      Int = A(0)
    """, deep=True, solve_unknowns=True)
    self.assertTypesMatchPytd(ty, """
      class A(type): ...
      Int = ...  # type: Type[int]
    """)


if __name__ == "__main__":
  test_inference.main()
