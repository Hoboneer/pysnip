class Foo:
    def bar(self):
        pass

def baz():
    pass

abc = "this is unrelated"

def qux():
    def quz():
        pass
    def quz():
        print('because i am evil')
    print("hi")
