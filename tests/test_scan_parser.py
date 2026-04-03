import pytest

from services.scan_parser import CommandParseError, parse_dashboard_scan_command, parse_scan_command


def test_parse_google_maps_shorthand():
    req = parse_scan_command("google_maps restaurantes Franca SP")
    assert req.fonte == "google_maps"
    assert req.busca == "restaurantes Franca SP"
    assert req.meta_minima == 30


def test_parse_apontador_shorthand():
    req = parse_scan_command("apontador Franca SP bares-e-restaurantes/restaurantes")
    assert req.fonte == "apontador"
    assert req.cidade == "Franca"
    assert req.estado == "SP"
    assert req.categoria == "bares-e-restaurantes/restaurantes"


def test_parse_cli_google_maps_command():
    req = parse_scan_command('python main.py --fonte google_maps --busca "restaurantes Franca SP"')
    assert req.fonte == "google_maps"
    assert req.busca == "restaurantes Franca SP"


def test_parse_dashboard_google_maps_command():
    req = parse_dashboard_scan_command("google_maps", "restaurantes Franca SP")
    assert req.fonte == "google_maps"
    assert req.busca == "restaurantes Franca SP"


def test_parse_dashboard_apontador_command():
    req = parse_dashboard_scan_command("apontador", "Franca SP bares-e-restaurantes/restaurantes")
    assert req.fonte == "apontador"
    assert req.cidade == "Franca"
    assert req.estado == "SP"
    assert req.categoria == "bares-e-restaurantes/restaurantes"


def test_parse_invalid_command():
    with pytest.raises(CommandParseError):
        parse_scan_command("google_maps")


def test_parse_dashboard_invalid_apontador_command():
    with pytest.raises(CommandParseError):
        parse_dashboard_scan_command("apontador", "Franca SP")
