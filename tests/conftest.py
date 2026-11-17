# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Aucune connexion réseau réelle dans les tests ordinaires."""

import socket

import pytest


@pytest.fixture(autouse=True)
def forbid_real_network(monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError('Connexion réseau réelle interdite dans les tests; simuler la source')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(socket.socket,'connect_ex',forbidden)
    monkeypatch.setattr(socket,'create_connection',forbidden)
