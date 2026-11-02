import httpx

from app.services import nhtsa_service


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _ok_response(**row):
    base = {"Make": "", "Model": "", "ModelYear": "", "ErrorCode": "0", "ErrorText": "0 - VIN decoded clean."}
    base.update(row)
    return httpx.Response(200, json={"Count": 1, "Results": [base]})


def test_decodes_make_model_year():
    requests = []

    def handler(request):
        requests.append(request)
        return _ok_response(Make="HONDA", Model="Accord", ModelYear="2003")

    decoded = nhtsa_service.decode_vin("1HGCM82633A004352", http_client=_client(handler))
    assert decoded.make == "HONDA"
    assert decoded.model == "Accord"
    assert decoded.model_year == 2003
    assert requests[0].url.path.endswith("/DecodeVinValues/1HGCM82633A004352")
    assert requests[0].url.params["format"] == "json"


def test_caches_by_vin():
    calls = []

    def handler(request):
        calls.append(request)
        return _ok_response(Make="HONDA")

    client = _client(handler)
    nhtsa_service.decode_vin("1HGCM82633A004352", http_client=client)
    nhtsa_service.decode_vin("1HGCM82633A004352", http_client=client)
    assert len(calls) == 1


def test_returns_none_on_timeout_and_does_not_cache():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ConnectTimeout("timeout", request=request)

    client = _client(handler)
    assert nhtsa_service.decode_vin("1HGCM82633A004352", http_client=client) is None
    assert nhtsa_service.decode_vin("1HGCM82633A004352", http_client=client) is None
    assert len(calls) == 2


def test_returns_none_on_server_error():
    decoded = nhtsa_service.decode_vin(
        "1HGCM82633A004352", http_client=_client(lambda request: httpx.Response(503))
    )
    assert decoded is None


def test_describes_unregistered_manufacturer_in_spanish():
    decoded = nhtsa_service.decode_vin(
        "JTDBR32E720123456",
        http_client=_client(lambda request: _ok_response(ErrorCode="7", ErrorText="7 - Manufacturer is not registered")),
    )
    assert decoded.make is None
    assert "fabricante" in nhtsa_service.describe_problem(decoded)
