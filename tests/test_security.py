from app.core.security import get_password_hash, verify_password

def test_password_hash_is_salted_and_verifiable():
    first = get_password_hash("StrongPassword123!")
    second = get_password_hash("StrongPassword123!")
    assert first != second
    assert verify_password("StrongPassword123!", first)
    assert not verify_password("wrong", first)
