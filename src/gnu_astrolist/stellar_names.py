# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Notation des lettres grecques et reconnaissance stricte des désignations."""

import re
import unicodedata

GREEK = dict(
    zip(
        "Alp Bet Gam Del Eps Zet Eta The Iot Kap Lam Mu Nu Xi Omi Pi Rho Sig Tau Ups Phi Chi Psi Ome".split(),
        "αβγδεζηθικλμνξοπρστυφχψω",
    )
)
WORDS = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega".split()
TOKENS = {}
for (abbreviation, symbol), word in zip(GREEK.items(), WORDS):
    for token in (abbreviation.casefold(), symbol, word):
        TOKENS[token] = abbreviation.casefold()
# « alf » est une abréviation courante de alpha; elle ne crée aucun lien de position.
TOKENS["alf"] = "alp"


def bayer_label(token: str, constellation: str) -> str:
    match = re.fullmatch(r"([A-Za-z]+)(?:-(\d+))?", token)
    if match is None or match[1] not in GREEK:
        raise ValueError(f"Désignation Bayer HYG inconnue : {token}")
    index = (match[2] or "").translate(str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹"))
    return f"{GREEK[match[1]]}{index} {constellation}"


def normalize_stellar_name(value: str) -> str | None:
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    # La constellation doit être un mot de trois lettres complet, avec séparation.
    flam = re.fullmatch(r"(\d+)[ _-]+([a-z]{3})", value)
    if flam:
        return f"FLAM:{int(flam[1])}:{flam[2]}"
    bayer = re.fullmatch(r"([a-zα-ω]+)[ -]*(\d*)[ _]+([a-z]{3})", value)
    if bayer and bayer[1] in TOKENS:
        return f"BAYER:{TOKENS[bayer[1]]}{bayer[2]}:{bayer[3]}"
    return None
