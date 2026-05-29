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

    def test_4_anos_deve_descartar(self):
        result = analyze_description("Mínimo de 4 anos de experiência.")
        assert result["discard"] is True
        assert result["required_years"] == 4

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
