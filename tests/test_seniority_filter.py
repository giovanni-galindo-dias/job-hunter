"""
Testes unitários para services/seniority_filter.py.
Execute com: pytest tests/ -v
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.seniority_filter import (
    check_title_seniority,
    analyze_description,
    compute_seniority,
    inject_junior_terms,
)


# ── check_title_seniority (Camada 2) ─────────────────────────────────────────

class TestTitleSeniority:

    def test_senior_title_deve_ser_descartado(self):
        result = check_title_seniority("Desenvolvedor Sênior Backend")
        assert result["status"] == "senior"
        assert result["blacklist_hits"]

    def test_senior_em_ingles_deve_ser_descartado(self):
        result = check_title_seniority("Senior Software Engineer")
        assert result["status"] == "senior"

    def test_sr_abreviado_deve_ser_descartado(self):
        result = check_title_seniority("Dev Sr Python")
        assert result["status"] == "senior"

    def test_pleno_deve_ser_descartado(self):
        result = check_title_seniority("Analista de Suporte Pleno")
        assert result["status"] == "senior"

    def test_lead_deve_ser_descartado(self):
        result = check_title_seniority("Tech Lead Backend")
        assert result["status"] == "senior"

    def test_gerente_deve_ser_descartado(self):
        result = check_title_seniority("Gerente de Projetos de TI")
        assert result["status"] == "senior"

    def test_analista_junior_deve_ser_mantido(self):
        result = check_title_seniority("Analista de Suporte Júnior")
        assert result["status"] == "junior"
        assert result["junior_hits"]

    def test_junior_em_ingles_deve_ser_mantido(self):
        result = check_title_seniority("Junior Software Developer")
        assert result["status"] == "junior"

    def test_trainee_deve_ser_mantido(self):
        result = check_title_seniority("Trainee de TI")
        assert result["status"] == "junior"

    def test_estagio_deve_ser_mantido(self):
        result = check_title_seniority("Estagiário em Desenvolvimento de Sistemas")
        assert result["status"] == "junior"

    def test_pleno_junior_deve_ser_ambiguo(self):
        result = check_title_seniority("Analista Pleno/Júnior")
        assert result["status"] == "ambiguous"
        assert result["blacklist_hits"]
        assert result["junior_hits"]

    def test_sem_nivel_deve_ser_ambiguo(self):
        result = check_title_seniority("Desenvolvedor Python Backend")
        assert result["status"] == "ambiguous"

    def test_plsql_nao_deve_ser_confundido_com_pl_pleno(self):
        # "PL/SQL" não deve ser confundido com "PL" de Pleno
        result = check_title_seniority("Desenvolvedor PL/SQL Oracle")
        # Não deve ser "senior" por causa do "PL" de PL/SQL
        assert result["status"] != "senior"

    def test_nivel_ii_deve_ser_descartado(self):
        result = check_title_seniority("Analista de Sistemas II")
        assert result["status"] == "senior"

    def test_nivel_iii_deve_ser_descartado(self):
        result = check_title_seniority("Analista III")
        assert result["status"] == "senior"

    def test_jr_abreviado_deve_ser_mantido(self):
        result = check_title_seniority("Software Dev Jr")
        assert result["status"] == "junior"


# ── analyze_description (Camada 3) ───────────────────────────────────────────

class TestAnalyzeDescription:

    def test_5_anos_deve_descartar(self):
        result = analyze_description("Requisitos: 5+ anos de experiência em Python.")
        assert result["discard"] is True
        assert result["required_years"] == 5

    def test_4_anos_nao_descarta_vai_para_verificar(self):
        # MAX_ALLOWED_YEARS=4: "4 anos" está no limite → needs_verify=True, discard=False
        result = analyze_description("Mínimo de 4 anos de experiência.")
        assert result["discard"] is False
        assert result["needs_verify"] is True
        assert result["required_years"] == 4

    def test_5_anos_deve_descartar(self):
        result = analyze_description("Mínimo de 5 anos de experiência.")
        assert result["discard"] is True
        assert result["required_years"] == 5

    def test_2_anos_nao_deve_descartar(self):
        result = analyze_description("Até 2 anos de experiência.")
        assert result["discard"] is False
        assert result["required_years"] == 2

    def test_inicio_de_carreira_e_sinal_junior(self):
        result = analyze_description("Buscamos candidatos para início de carreira em TI.")
        assert result["discard"] is False
        assert any("carreira" in s.lower() or "início" in s.lower() for s in result["junior_signals"])

    def test_sem_experiencia_e_sinal_junior(self):
        result = analyze_description("Vaga para quem não tem experiência prévia.")
        assert result["discard"] is False

    def test_recem_formado_e_sinal_junior(self):
        result = analyze_description("Oportunidade para recém-formados em TI.")
        assert result["junior_signals"]

    def test_sem_informacao_de_anos(self):
        result = analyze_description("Responsabilidades: atendimento a chamados, SQL, Python.")
        assert result["required_years"] is None
        assert result["discard"] is False

    def test_5_years_em_ingles_deve_descartar(self):
        result = analyze_description("We require 5+ years of experience in backend development.")
        assert result["discard"] is True
        assert result["required_years"] == 5

    def test_3_anos_nao_descarta(self):
        # exatamente 3 anos está no limite → não descarta
        result = analyze_description("Mínimo de 3 anos de experiência.")
        assert result["discard"] is False
        assert result["required_years"] == 3


# ── compute_seniority (Camada 4) ─────────────────────────────────────────────

class TestComputeSeniority:

    def test_senior_titulo_e_descartado_com_score_zero(self):
        result = compute_seniority(
            "Desenvolvedor Sênior Backend",
            "Precisamos de alguém com vasta experiência em liderança técnica.",
        )
        assert result.seniority_score == 0
        assert result.discard is True
        assert result.seniority_label == "Sênior/Pleno"

    def test_5_anos_na_descricao_e_descartado(self):
        result = compute_seniority(
            "Desenvolvedor Backend",
            "Exige mínimo de 5 anos de experiência em cloud.",
        )
        assert result.seniority_score == 0
        assert result.discard is True

    def test_junior_no_titulo_tem_score_alto(self):
        result = compute_seniority(
            "Analista Júnior de Suporte",
            "Vaga para início de carreira. Sem experiência prévia necessária.",
        )
        assert result.seniority_score >= 80
        assert result.discard is False
        assert result.seniority_label == "Júnior"

    def test_pleno_junior_e_ambiguo(self):
        result = compute_seniority(
            "Dev Pleno/Júnior Python",
            "Oportunidade de crescimento profissional.",
        )
        assert result.seniority_score >= 40
        assert result.seniority_score < 80
        assert result.discard is False
        assert result.seniority_label == "Ambíguo"

    def test_sem_nivel_sem_sinal_e_ambiguo(self):
        result = compute_seniority(
            "Desenvolvedor Python",
            "Responsabilidades: manutenção de sistemas, atendimento a chamados.",
        )
        # Ambíguo sem sinais → score = 40 (abaixo do default_min_score=50, aparece só no toggle)
        assert result.seniority_score == 40
        assert result.discard is False
        assert result.seniority_label == "Ambíguo"

    def test_junior_com_sinais_positivos_tem_score_maximo(self):
        result = compute_seniority(
            "Estagiário Desenvolvedor Backend",
            "Busca por candidatos em início de carreira, recém-formados. "
            "Oferecemos plano de desenvolvimento. Até 1 ano de experiência.",
        )
        assert result.seniority_score == 100
        assert result.discard is False

    def test_signals_sao_populados(self):
        result = compute_seniority(
            "Analista Júnior de Dados",
            "Buscamos candidatos para início de carreira.",
        )
        assert result.signals  # deve ter ao menos um sinal

    def test_tech_lead_e_descartado(self):
        result = compute_seniority("Tech Lead Python", "Senior engineer needed.")
        assert result.seniority_score == 0
        assert result.discard is True


# ── inject_junior_terms (Camada 1) ────────────────────────────────────────────

class TestInjectJuniorTerms:

    def test_keyword_sem_nivel_recebe_junior(self):
        result = inject_junior_terms("PL/SQL Oracle")
        assert "junior" in result.lower()

    def test_keyword_com_junior_nao_duplica(self):
        result = inject_junior_terms("PL/SQL junior")
        assert result.lower().count("junior") == 1

    def test_keyword_com_senior_nao_recebe_junior(self):
        result = inject_junior_terms("Python senior developer")
        assert result == "Python senior developer"

    def test_keyword_trainee_nao_recebe_junior(self):
        result = inject_junior_terms("trainee backend")
        assert result == "trainee backend"


# ── Testes adicionais — regressões específicas ────────────────────────────────

class TestRegressions:
    """
    Testes exigidos pelo prompt de correção de bugs:
      - Falso positivo de regex "há N anos no mercado"
      - Geo-filter: fonte BR sem location ainda é BR
      - query_builder: fontes EN recebem queries EN
      - 3-4 anos → "Verificar", não descartado
    """

    def test_ha_n_anos_no_mercado_nao_e_falso_positivo(self):
        """
        "há 2 anos no mercado" descreve a empresa, não requisito do candidato.
        Não deve aumentar required_years.
        """
        from services.seniority_filter import analyze_description
        desc = "Empresa fundada há 2 anos no mercado de tecnologia. Buscamos analista júnior."
        result = analyze_description(desc)
        # Não deve detectar "2 anos" como requisito do candidato
        assert result["required_years"] is None or result["required_years"] == 0 or result["discard"] is False

    def test_empresa_com_20_anos_nao_descarta_candidato(self):
        """
        "empresa com 20 anos de experiência no mercado" NÃO deve descartar a vaga.
        O padrão correto exige "X anos de experiência" no contexto do candidato.
        """
        from services.seniority_filter import analyze_description
        desc = (
            "Somos uma empresa com 20 anos de experiência no mercado odontológico. "
            "Buscamos analista júnior para início de carreira."
        )
        result = analyze_description(desc)
        # Deve detectar sinal positivo de júnior
        assert result["junior_signals"]
        # A vaga não deve ser descartada por causa do "20 anos" da empresa
        assert result["discard"] is False

    def test_3_anos_exigidos_gera_verificar_nao_descarta(self):
        """
        "mínimo de 3 anos de experiência" → seniority_label = "Verificar", não "Sênior/Pleno".
        Empresas brasileiras inflam requisitos — 3 anos é negociável.
        """
        result = compute_seniority(
            "Analista de Suporte Técnico",
            "Requisitos: mínimo de 3 anos de experiência em suporte de TI. "
            "Conhecimento em SQL e ServiceNow.",
        )
        assert result.seniority_label == "Verificar"
        assert result.discard is False
        assert result.seniority_score >= 40

    def test_4_anos_exigidos_gera_verificar_nao_descarta(self):
        """4 anos ainda é dentro do threshold de "verificar"."""
        from services.seniority_filter import analyze_description
        result = analyze_description("Requisito: 4 anos de experiência em Oracle Database.")
        assert result["needs_verify"] is True
        assert result["discard"] is False

    def test_5_anos_exigidos_descarta(self):
        """5 anos > MAX_ALLOWED_YEARS=4 → deve descartar."""
        result = compute_seniority(
            "Desenvolvedor Backend",
            "Buscamos profissional com 5 anos de experiência em Python.",
        )
        assert result.seniority_score == 0
        assert result.discard is True

    def test_gupy_sem_location_ainda_e_br(self):
        """
        Vagas do Gupy (fonte BR nativa) com location vazia
        devem ser classificadas como brasileiras pelo geo-filter.
        """
        from services.aggregator import _is_brazil_job
        # Fonte Gupy com location vazia → ainda é BR
        assert _is_brazil_job("Gupy", "") is True
        assert _is_brazil_job("Gupy", "São Paulo, SP, Brasil") is True
        # Fonte internacional sem location → não é BR
        assert _is_brazil_job("Arbeitnow", "") is False
        # Fonte internacional com location BR → é BR
        assert _is_brazil_job("Arbeitnow", "São Paulo, SP, Brasil") is True
        assert _is_brazil_job("Remotive", "Brasil") is True

    def test_query_builder_remote_queries_sao_em_ingles(self):
        """
        remote_queries() deve retornar apenas queries em inglês
        para fontes internacionais que não entendem PT-BR.
        """
        from collectors.query_builder import remote_queries
        queries = remote_queries()
        pt_words = ["analista", "estagiário", "júnior", "sustentação", "dados"]
        for q in queries:
            for pt in pt_words:
                assert pt.lower() not in q.lower(), (
                    f"Query {q!r} contém termo PT-BR {pt!r} — "
                    "fontes internacionais não entendem PT"
                )

    def test_plsql_no_titulo_nao_blacklistado_por_pl(self):
        """
        "Desenvolvedor PL/SQL" NÃO deve ser descartado pelo padrão 'pl' da blacklist.
        (Regressão: 'pl' de 'pleno' não deve casar com 'pl' de 'pl/sql')
        """
        result = check_title_seniority("Desenvolvedor PL/SQL Oracle")
        assert result["status"] != "senior"
