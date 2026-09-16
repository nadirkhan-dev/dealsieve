from app.ingest import normalize_domain, normalize_name, parse_csv, parse_employees


def test_normalize_domain_variants():
    assert normalize_domain("https://www.Acme.com/about") == "acme.com"
    assert normalize_domain("acme.com") == "acme.com"
    assert normalize_domain("owner@acme.com") == "acme.com"
    assert normalize_domain("not a website") is None


def test_normalize_name_strips_legal_suffixes():
    assert normalize_name("Reyes Comfort Heating & Air LLC") == normalize_name("Reyes Comfort Heating and Air")


def test_parse_employees_ranges():
    assert parse_employees("11-50") == 30
    assert parse_employees("1,200") == 1200
    assert parse_employees("") is None


def test_parse_csv_dedupes_and_merges():
    csv_bytes = (b"Company,URL,Phone\n"
                 b"Acme Plumbing,acme.test,\n"
                 b"Acme Plumbing LLC,https://www.acme.test/,555-123-4567\n"
                 b",nameless.test,\n")
    leads, report = parse_csv(csv_bytes)
    assert len(leads) == 1
    assert leads[0]["phone"] == "555-123-4567"  # merged from the duplicate
    assert report["duplicates_in_file"] == 1
    assert report["skipped_missing_name"] == 1
