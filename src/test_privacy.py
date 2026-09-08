from src.privacy import mask_identifiers


def test_privacy_masking_removes_common_identifiers():
    source = (
        "Patient Name: Jane Smith\n"
        "Date of Birth: 12 March 1980\n"
        "MRN: 123456789\n"
        "Phone: +44 7700 900123\n"
        "Email: jane.smith@example.com\n"
        "Diagnosis: Hypertension."
    )
    masked = mask_identifiers(source)

    for identifier in (
        "Jane Smith",
        "12 March 1980",
        "123456789",
        "7700 900123",
        "jane.smith@example.com",
    ):
        assert identifier not in masked

    assert "Diagnosis: Hypertension." in masked
