"""
Registro de todos os coletores ativos.
Para desativar um coletor: comente a linha correspondente.
Para adicionar um novo: importe e acrescente à lista COLLECTORS.
"""
from collectors.remotive import RemotiveCollector
from collectors.remoteok import RemoteOKCollector
from collectors.adzuna import AdzunaCollector
from collectors.serpapi_google import SerpAPIGoogleJobsCollector
from collectors.jsearch import JSearchCollector
from collectors.arbeitnow import ArbeitnowCollector
from collectors.themuse import TheMuseCollector

COLLECTORS = [
    SerpAPIGoogleJobsCollector(),   # ← mais importante; agrega Gupy, LinkedIn, Indeed BR
    AdzunaCollector(),
    JSearchCollector(),
    ArbeitnowCollector(),
    RemotiveCollector(),
    RemoteOKCollector(),
    TheMuseCollector(),
]
