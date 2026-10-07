from app.services.order_extractor import OrderExtractor


def test_extract_amount_rub_symbol():
    extractor = OrderExtractor()
    result = extractor.extract("Товар стоит 1500.50₽")
    assert result is not None
    assert result["amount"] == 1500.50
    assert result["confidence"] == 0.7


def test_extract_amount_rub_text():
    extractor = OrderExtractor()
    result = extractor.extract("Сумма: 2500 руб")
    assert result is not None
    assert result["amount"] == 2500.0


def test_extract_amount_rus_r():
    extractor = OrderExtractor()
    result = extractor.extract("Итого 3200 р.")
    assert result is not None
    assert result["amount"] == 3200.0


def test_extract_amount_kopecks():
    extractor = OrderExtractor()
    result = extractor.extract("цена 199.99руб")
    assert result is not None
    assert result["amount"] == 199.99


def test_extract_amount_summa_keyword():
    extractor = OrderExtractor()
    result = extractor.extract("сумма: 5000")
    assert result is not None
    assert result["amount"] == 5000.0


def test_extract_amount_itogo_keyword():
    extractor = OrderExtractor()
    result = extractor.extract("итого 12300")
    assert result is not None
    assert result["amount"] == 12300.0


def test_extract_amount_comma_decimal():
    extractor = OrderExtractor()
    result = extractor.extract("Оплата 750,50₽")
    assert result is not None
    assert result["amount"] == 750.50


def test_extract_amount_no_match():
    extractor = OrderExtractor()
    result = extractor.extract("Привет, как дела?")
    assert result is None


def test_extract_amount_empty():
    extractor = OrderExtractor()
    result = extractor.extract("")
    assert result is None


def test_extract_amount_whitespace():
    extractor = OrderExtractor()
    result = extractor.extract("   ")
    assert result is None


def test_extract_amount_large_number():
    extractor = OrderExtractor()
    result = extractor.extract("Сумма контракта 9999999")
    assert result is not None
    assert result["amount"] == 9999999.0


def test_extract_amount_too_large():
    extractor = OrderExtractor()
    result = extractor.extract("Сумма 15000000")
    assert result is None


def test_extract_amount_zero():
    extractor = OrderExtractor()
    result = extractor.extract("Сумма 0 руб")
    assert result is not None
    assert result["amount"] == 0.0
    assert result["confidence"] == 0.3


def test_extract_amount_multiple_same():
    extractor = OrderExtractor()
    result = extractor.extract("Товар 1: 500₽, Товар 2: 500₽, Итого 1000₽")
    assert result is not None
    assert result["amount"] == 500.0


def test_extract_amount_stoimost_keyword():
    extractor = OrderExtractor()
    result = extractor.extract("стоимость: 8900 рублей")
    assert result is not None
    assert result["amount"] == 8900.0


def test_fallback_extract():
    extractor = OrderExtractor()
    result = extractor.extract_from_fallback("Нужно заплатить 4500 за услуги")
    assert result is not None
    assert result == 4500.0


def test_fallback_extract_no_match():
    extractor = OrderExtractor()
    result = extractor.extract_from_fallback("Привет")
    assert result is None


def test_fallback_skips_small_numbers():
    extractor = OrderExtractor()
    result = extractor.extract_from_fallback("Номер заказа 5, цена 300")
    assert result is not None
    assert result == 300.0
