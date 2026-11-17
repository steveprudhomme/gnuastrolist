# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""La requête météo doit annoncer la version réelle, avec un transport simulé."""

import io

from gnu_astrolist import __version__, weather


def test_weather_request_identifies_current_application_version(monkeypatch):
    class Response(io.BytesIO):
        status = 200
        headers = {}

    def open_response(request, timeout):
        assert request.get_header('User-agent') == f'GNU-Astrolist/{__version__}'
        assert timeout == weather.WEATHER_TIMEOUT_SECONDS
        return Response(b'{"synthetic": true}')

    monkeypatch.setattr(weather, 'urlopen', open_response)
    assert weather._read_json('https://example.invalid/synthetic') == {'synthetic': True}
