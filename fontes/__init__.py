"""Cada tipo de fonte do config.yaml aponta para uma função buscar(fonte, http)."""
from . import ashby, greenhouse, html_generico, lever

BUSCADORES = {
    "greenhouse": greenhouse.buscar,
    "lever": lever.buscar,
    "ashby": ashby.buscar,
    "html": html_generico.buscar,
    "rss": html_generico.buscar_rss,
}
