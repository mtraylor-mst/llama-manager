from services.command_builder import int_bool, neg_bool, float_fmt


class TestIntBool:
    def test_true_value(self):
        assert int_bool(1) == 1

    def test_false_value(self):
        assert int_bool(0) == 0

    def test_string_true(self):
        assert int_bool("yes") == 1

    def test_none(self):
        assert int_bool(None) is None


class TestNegBool:
    def test_true_becomes_one(self):
        assert neg_bool(True) == 1

    def test_false_becomes_zero(self):
        assert neg_bool(False) == 0

    def test_none_stays_none(self):
        assert neg_bool(None) is None


class TestFloatFmt:
    def test_simple_float(self):
        assert float_fmt(0.8) == "0.8"

    def test_integer_value(self):
        assert float_fmt(1.0) == "1"

    def test_trailing_zeros_stripped(self):
        assert float_fmt(1.500) == "1.5"

    def test_none_input(self):
        assert float_fmt(None) is None

    def test_small_float(self):
        result = float_fmt(0.0001)
        assert "." in result

    def test_whole_number_no_trailing_dot(self):
        assert float_fmt(5.0) == "5"
