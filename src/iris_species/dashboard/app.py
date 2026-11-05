"""Entrypoint do dashboard: ``poetry run streamlit run src/iris_species/dashboard/app.py``.

Só orquestra: lê os dados (:mod:`~iris_species.dashboard.dados`), aplica os filtros e
mostra os KPIs (:mod:`~iris_species.dashboard.kpis`) e as figuras
(:mod:`~iris_species.dashboard.graficos`). Não grava nada no banco.
"""

import logging
from collections.abc import Sequence

import streamlit as st

from iris_species.dashboard import graficos, kpis
from iris_species.dashboard.dados import DadosIndisponiveisError, DadosPainel, carregar_dados

logger = logging.getLogger(__name__)

_CONFIG_PLOTLY = {"displaylogo": False}


@st.cache_data(ttl=300, show_spinner="Lendo o iris.duckdb...")
def _dados() -> DadosPainel:
    return carregar_dados()


def _linha_kpis(indicadores: Sequence[kpis.Kpi]) -> None:
    for coluna, kpi in zip(st.columns(len(indicadores)), indicadores, strict=True):
        coluna.metric(kpi.rotulo, kpi.valor, help=kpi.ajuda, border=True)


def _grafico(figura: object) -> None:
    st.plotly_chart(figura, theme=None, config=_CONFIG_PLOTLY)


def main() -> None:
    """Monta a página do dashboard."""
    st.set_page_config(page_title="Iris: flores e mundo", page_icon="🌸", layout="wide")
    st.title("Iris: flores medidas e ocorrências no mundo")
    st.caption(
        "150 flores medidas (Kaggle) unidas pela espécie a registros georreferenciados da "
        "[GBIF](https://www.gbif.org)."
    )

    try:
        dados = _dados()
    except DadosIndisponiveisError as exc:
        logger.error("dashboard sem dados: %s", exc)
        st.error(f"Não foi possível carregar os dados: {exc}.")
        st.stop()

    anos = dados.ocorrencias["ano"].dropna()
    ano_min, ano_max = int(anos.min()), int(anos.max())
    filtro_especie, filtro_ano = st.columns([2, 3])
    especies = filtro_especie.multiselect(
        "Espécies", graficos.ORDEM_ESPECIES, default=graficos.ORDEM_ESPECIES
    )
    periodo = filtro_ano.slider(
        "Período das ocorrências (GBIF)", ano_min, ano_max, (ano_min, ano_max)
    )
    if not especies:
        st.info("Selecione ao menos uma espécie.")
        st.stop()

    flores = kpis.filtrar(dados.flores, especies)
    ocorrencias = kpis.filtrar(dados.ocorrencias, especies, periodo)

    st.subheader("Flores medidas (Kaggle)")
    _linha_kpis(kpis.kpis_flores(flores))
    esquerda, direita = st.columns(2)
    with esquerda:
        st.markdown("**Pétala: comprimento x largura**")
        _grafico(graficos.dispersao_petala(flores))
    with direita:
        medida = st.selectbox(
            "Distribuição por espécie",
            list(graficos.ROTULOS_MEDIDAS),
            index=2,
            format_func=graficos.ROTULOS_MEDIDAS.__getitem__,
        )
        _grafico(graficos.distribuicao_medida(flores, medida))

    st.subheader("Ocorrências no mundo (GBIF)")
    _linha_kpis(kpis.kpis_ocorrencias(ocorrencias))
    st.caption(
        "A GBIF devolve primeiro os registros mais recentes e a extração guarda até 3.000 por "
        "espécie, por isso os últimos anos concentram a amostra. Compare as espécies entre si, "
        "não a tendência ao longo do tempo."
    )
    if ocorrencias.empty:
        st.info("Nenhuma ocorrência no recorte.")
    else:
        st.markdown("**Onde foram registradas**")
        _grafico(graficos.mapa_ocorrencias(ocorrencias))
        esquerda, direita = st.columns(2)
        with esquerda:
            st.markdown("**Ocorrências por ano**")
            _grafico(graficos.linha_ocorrencias_ano(kpis.ocorrencias_por_ano(ocorrencias)))
        with direita:
            st.markdown("**10 países com mais ocorrências**")
            _grafico(graficos.barras_top_paises(kpis.top_paises(ocorrencias)))

    st.subheader("Panorama por espécie (JOIN Kaggle x GBIF)")
    st.caption("analytics.panorama, sem filtro de período.")
    st.dataframe(
        kpis.filtrar(dados.panorama, especies),
        hide_index=True,
        column_config={
            "media_comprimento_sepala_cm": st.column_config.NumberColumn(format="%.2f"),
            "media_largura_sepala_cm": st.column_config.NumberColumn(format="%.2f"),
            "media_comprimento_petala_cm": st.column_config.NumberColumn(format="%.2f"),
            "media_largura_petala_cm": st.column_config.NumberColumn(format="%.2f"),
            "latitude_media": st.column_config.NumberColumn(format="%.1f"),
            "gbif_codigo": st.column_config.NumberColumn(format="%d"),
        },
    )
    with st.expander("Tabela das flores do recorte"):
        st.dataframe(flores, hide_index=True)


if __name__ == "__main__":
    main()
