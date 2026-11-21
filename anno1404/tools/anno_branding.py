"""Embed the bundled game logo in self-contained gallery HTML."""
import base64
from pathlib import Path


def add_game_logo(page, game):
    labels = {'anno117': 'Anno 117: Pax Romana', 'anno1800': 'Anno 1800',
              'anno1404': 'Anno 1404 History Edition'}
    label = labels[game]
    logo = Path(__file__).resolve().parents[1] / 'docs/images/game-logo.png'
    data = base64.b64encode(logo.read_bytes()).decode('ascii')
    background = ('background:#f1e5cc;padding:8px;border-radius:8px;' if game == 'anno117'
                  else 'background:#173345;padding:8px;border-radius:8px;')
    image = (f'<img class="game-logo" src="data:image/png;base64,{data}" alt="{label}" '
             'style="display:block;width:min(100%,270px);height:auto;max-height:130px;'
             f'object-fit:contain;object-position:left center;margin:0 0 16px;border:0;{background}">')
    return page.replace('<header>', '<header>' + image, 1)
