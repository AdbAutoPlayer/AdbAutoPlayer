class TestSnakeToPascal:
    def test_basic_snake_case(self):
        assert TestSnakeToPascal.snake_to_pascal("hello_world") == "HelloWorld"

    def test_single_word(self):
        assert TestSnakeToPascal.snake_to_pascal("hello") == "Hello"

    def test_multiple_underscores(self):
        assert TestSnakeToPascal.snake_to_pascal("hello___world") == "HelloWorld"

    def test_empty_string(self):
        assert TestSnakeToPascal.snake_to_pascal("") == ""

    def test_single_underscore(self):
        assert TestSnakeToPascal.snake_to_pascal("_") == ""

    def test_all_caps(self):
        assert TestSnakeToPascal.snake_to_pascal("HELLO_WORLD") == "HelloWorld"

    def test_mixed_case(self):
        assert TestSnakeToPascal.snake_to_pascal("hello_World_TEST") == "HelloWorldTest"

    @staticmethod
    def snake_to_pascal(s: str):
        """snake_case to PascalCase."""
        return "".join(word.capitalize() for word in s.split("_"))
