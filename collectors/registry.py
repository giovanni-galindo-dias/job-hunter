"""
Registro de todos os coletores ativos — em ordem de PRIORIDADE.

Fontes BR têm prioridade sobre fontes internacionais.
Para desativar um coletor: comente a linha correspondente.
Para adicionar um novo: importe e acrescente à lista COLLECTORS.
"""
from collectors.gupy import GupyCollector               # BR #1 — sem chave
from collectors.serpapi_google import SerpAPIGoogleJobsCollector  # BR via Google
from collectors.adzuna import AdzunaCollector           # BR — chave gratuita
from collectors.jsearch import JSearchCollector         # multi-portal — chave gratuita
from collectors.arbeitnow import ArbeitnowCollector     # remoto — sem chave
from collectors.remotive import RemotiveCollector       # remoto — sem chave
from collectors.remoteok import RemoteOKCollector       # remoto — sem chave
from collectors.themuse import TheMuseCollector         # entry-level — sem chave

# Fontes BR-first, depois internacionais
COLLECTORS = [
    GupyCollector(),               # principal plataforma RH do Brasil
    SerpAPIGoogleJobsCollector(),  # agrega Gupy/LinkedIn/Indeed/Vagas.com BR
    AdzunaCollector(),             # Brasil endpoint (chave gratuita)
    JSearchCollector(),            # LinkedIn/Indeed/Glassdoor (chave gratuita)
    ArbeitnowCollector(),          # remoto internacional
    RemotiveCollector(),           # remoto internacional
    RemoteOKCollector(),           # remoto internacional
    TheMuseCollector(),            # entry-level filtrado
]

# Fontes nativas do Brasil (jobs dessas fontes passam automaticamente no geo-filter)
BR_NATIVE_SOURCES = {"Gupy", "Adzuna"}
