import eel

eel.init("frontend/build", [".tsx", ".ts", ".jsx", ".js", ".html", ".svelte"])


@eel.expose
def say_hello_py(x: str) -> None:
    print("Hello from %s" % x)


if __name__ == "__main__":
    say_hello_py("test")
    eel.start("", port=8888)
