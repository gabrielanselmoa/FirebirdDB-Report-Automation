import fdb
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import locale
import google.generativeai as genai

# Configura a localização para formato monetário brasileiro
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    st.warning("Configuração 'pt_BR.UTF-8' não encontrada.")
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR')
    except locale.Error:
        st.warning("Configuração 'pt_BR' também não encontrada.")

# Função para formatar valores como moeda
def formatar_moeda(valor):
    try:
        if pd.isna(valor):
            return "N/A"
        # Converte para float antes de formatar
        return locale.currency(float(valor), grouping=True, symbol=True)
    except (locale.Error, ValueError):
        # Retorna formato manual se houver erro na localização
        return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# Configurações iniciais da página Streamlit
st.set_page_config(layout="wide")
st.title("Dashboard de Crescimento de Negócios 📈")
st.write("Explore métricas, gráficos e dados de pagamentos e crescimento.")

# Inicializa variáveis para evitar NameError caso a conexão falhe
con = None
cur = None
df = pd.DataFrame()
df_grafico_acumulado = pd.DataFrame()
df_mensal_sum = pd.DataFrame()
total_revenue = 0
num_unique_clients = 0
avg_payment_value = 0
df_top_clients = pd.DataFrame()
df_latest_payments = pd.DataFrame()

# --- Conecta ao banco de dados e carrega dados de pagamentos ---
# Usando as credenciais do arquivo .streamlit/secrets.toml
try:
    # Acessa as credenciais Firebird a partir de st.secrets
    # As chaves devem corresponder à estrutura definida no secrets.toml
    db_dsn = st.secrets.connections.firebird.dsn
    db_user = st.secrets.connections.firebird.user
    db_password = st.secrets.connections.firebird.password

    print("Tentando conectar ao banco de dados usando secrets...") # Log para debug
    con = fdb.connect(dsn=db_dsn, user=db_user, password=db_password)
    cur = con.cursor()
    print("Conexão com banco de dados bem-sucedida.") # Log para debug

    query = """
    SELECT
        cli.ID AS cliente_id,
        cli.NOME AS cliente_nome,
        pag.ID AS pagamento_id,
        pag.DATA_PAGAMENTO AS data_pagamento,
        pag.VALOR_PAGO AS valor_pago
    FROM PAGAMENTOS pag
    JOIN CONTRATOS con ON pag.CONTRATO_ID = con.ID
    JOIN CLIENTES cli ON con.CLIENTE_ID = cli.ID
    ORDER BY pag.DATA_PAGAMENTO DESC; -- Ordenado por data descendente para os últimos pagamentos
    """
    cur.execute(query)
    dados = cur.fetchall()
    colunas = [desc[0] for desc in cur.description]
    df = pd.DataFrame(dados, columns=colunas)

    # --- Processamento dos Dados no Pandas ---
    if not df.empty:
        df_processado = df.copy()
        df_processado.rename(columns={
            'DATA_PAGAMENTO': 'data_pagamento',
            'CLIENTE_NOME': 'cliente_nome',
            'CLIENTE_ID': 'cliente_id',
            'VALOR_PAGO': 'valor_pago'
        }, inplace=True)

        try:
            df_processado['data_pagamento'] = pd.to_datetime(df_processado['data_pagamento'], errors='coerce')
            df_processado['valor_pago'] = pd.to_numeric(df_processado['valor_pago'], errors='coerce')
            df_processado.dropna(subset=['data_pagamento', 'valor_pago'], inplace=True)
        except Exception as e:
            st.error(f"Erro ao processar colunas de data ou valor: {e}")
            df_processado = pd.DataFrame()

        if not df_processado.empty:
            # Calcula métricas principais
            total_revenue = df_processado['valor_pago'].sum()
            num_unique_clients = df_processado['cliente_id'].nunique()
            avg_payment_value = df_processado['valor_pago'].mean()

            # Prepara dados para gráfico de top clientes
            df_top_clients = df_processado.groupby('cliente_nome')['valor_pago'].sum().sort_values(ascending=False).head(10).reset_index()
            df_top_clients.rename(columns={'cliente_nome': 'Cliente', 'valor_pago': 'Total Pago'}, inplace=True)
            df_top_clients = df_top_clients.set_index('Cliente')

            # Prepara dados para tabela de últimos pagamentos
            df_latest_payments = df_processado.head(10)

            # Prepara dados para gráfico de crescimento acumulado
            try:
                df_crescimento = df_processado.sort_values(by=['cliente_id', 'data_pagamento']).copy()
                df_crescimento['total_pago_cliente_acumulado'] = df_crescimento.groupby('cliente_id')['valor_pago'].cumsum()
                df_crescimento['mes_pagamento'] = df_crescimento['data_pagamento'].dt.to_period('M').dt.to_timestamp()

                df_mensal_acumulado = df_crescimento.groupby(['cliente_id', 'cliente_nome', 'mes_pagamento'])['total_pago_cliente_acumulado'].max().reset_index()
                df_grafico_acumulado = df_mensal_acumulado.pivot_table(index='mes_pagamento', columns='cliente_nome', values='total_pago_cliente_acumulado', aggfunc='max')
                df_grafico_acumulado = df_grafico_acumulado.fillna(method='ffill').fillna(0).reset_index()
                df_grafico_acumulado.rename(columns={'mes_pagamento': 'Data Referência (Mês)'}, inplace=True)
            except Exception as e:
                st.error(f"Erro ao calcular crescimento acumulado: {e}")
                df_grafico_acumulado = pd.DataFrame()

            # Prepara dados para gráfico de total pago por mês
            try:
                df_mensal_sum = df_processado.copy()
                df_mensal_sum['mes_pagamento'] = df_mensal_sum['data_pagamento'].dt.to_period('M').dt.to_timestamp()
                df_mensal_sum = df_mensal_sum.groupby('mes_pagamento')['valor_pago'].sum().reset_index()
                df_mensal_sum.rename(columns={'mes_pagamento': 'Mês Referência', 'valor_pago': 'Total Pago'}, inplace=True)
                df_mensal_sum = df_mensal_sum.set_index('Mês Referência')
            except Exception as e:
                st.error(f"Erro ao calcular total pago por mês: {e}")
                df_mensal_sum = pd.DataFrame()

except fdb.DatabaseError as e:
    st.error("Erro ao conectar ou operar no Banco de Dados Firebird!")
    st.error(f"Detalhes: {e}")
    st.warning("Verifique suas credenciais de banco de dados no arquivo `.streamlit/secrets.toml`.")

except AttributeError as e:
     st.error(f"Erro ao acessar credenciais no secrets.toml: {e}")
     st.warning(f"Verifique se as chaves 'connections.firebird.dsn', 'connections.firebird.user' e 'connections.firebird.password' estão corretamente definidas no seu arquivo `.streamlit/secrets.toml`.")


except Exception as e:
    st.error(f"Erro inesperado ao carregar dados do banco: {e}")

finally:
    # Garante que a conexão seja fechada mesmo que ocorra um erro
    if cur is not None:
        try:
            cur.close()
            # print("Cursor do banco de dados fechado.") # Log para debug
        except Exception as e:
            print(f"Erro ao fechar cursor: {e}") # Log para debug
    if con is not None:
        try:
            con.close()
            # print("Conexão com banco de dados fechada.") # Log para debug
        except Exception as e:
             print(f"Erro ao fechar conexão: {e}") # Log para debug

# Exibe métricas principais no topo
st.subheader("Métricas Principais")
metric_col1, metric_col2, metric_col3 = st.columns(3)

with metric_col1:
    st.metric(label="Receita Total", value=formatar_moeda(total_revenue))

with metric_col2:
    st.metric(label="Clientes Únicos com Pagamento", value=num_unique_clients)

with metric_col3:
    st.metric(label="Valor Médio por Pagamento", value=formatar_moeda(avg_payment_value))

st.markdown("---")

# Exibe gráfico de total pago por mês
st.subheader("Total Pago por Mês")
if not df_mensal_sum.empty:
    st.bar_chart(df_mensal_sum)
else:
    st.info("Dados insuficientes para gerar o gráfico.")

st.markdown("---")

# Exibe gráfico de crescimento acumulado
st.subheader("Crescimento do Pagamento Acumulado por Cliente")
if not df_grafico_acumulado.empty:
    coluna_data_x = 'Data Referência (Mês)'
    if coluna_data_x in df_grafico_acumulado.columns and len(df_grafico_acumulado.columns) > 1:
          st.line_chart(df_grafico_acumulado, x=coluna_data_x)
    else:
          st.warning("Dados insuficientes para o gráfico de crescimento acumulado.")
else:
    st.info("Não foi possível gerar o gráfico de crescimento acumulado.")

st.markdown("---")

# Exibe Top 10 Clientes e Últimos Pagamentos em colunas
st.subheader("Análises Adicionais de Pagamentos")
col_top_clients, col_latest_payments = st.columns([1, 1])

with col_top_clients:
    st.subheader("Top 10 Clientes por Total Pago")
    if not df_top_clients.empty:
        st.bar_chart(df_top_clients)
    else:
        st.info("Dados insuficientes para o gráfico de Top 10 Clientes.")

with col_latest_payments:
    st.subheader("Últimos 10 Pagamentos")
    if not df_latest_payments.empty:
        st.dataframe(df_latest_payments[['cliente_nome', 'data_pagamento', 'valor_pago']])
    else:
        st.info("Nenhum dado de último pagamento disponível.")

st.markdown("---")

# Expander para exibir os dados brutos
with st.expander("Ver Dados Brutos de Pagamentos"):
    st.subheader("Dados Brutos da Tabela PAGAMENTOS (Primeiras 100 Linhas)")
    if not df.empty:
        st.dataframe(df.head(100))
    else:
        st.info("Nenhum dado bruto carregado.")

# --- Integração de análise de dados usando IA ---
st.markdown("---")
st.subheader("Análise por IA")
st.write("Clique no botão abaixo para que a IA gere insights sobre seus dados de pagamentos.")

# --- Configurar API da IA (sem listar modelos para evitar erro) ---
# Esta parte já estava usando st.secrets, mantida e ajustada para melhor feedback de erro
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        # st.success("API da IA configurada.") # Removido para manter a interface limpa
        api_configured = True
    else:
        st.error("Erro: Chave 'GOOGLE_API_KEY' não encontrada nos secrets do Streamlit.")
        st.warning("Crie o arquivo `.streamlit/secrets.toml` com `GOOGLE_API_KEY = 'SUA_CHAVE'`.")
        api_configured = False
except Exception as e:
    st.error(f"Erro inesperado na configuração da API: {e}")
    api_configured = False
# --- Fim da Configuração da API ---


# Botão para gerar insights usando IA
if st.button("Gerar Insights de Negócios por IA"):
    # Só tenta gerar insights se a API estiver configurada, houver dados e a conexão com DB foi bem sucedida
    if api_configured and not df_mensal_sum.empty and not df_top_clients.empty and con is not None: # Verifica se con não é None

        # --- Preparar os dados para a IA ---
        insights_data = {
            "Receita Total Geral": formatar_moeda(total_revenue),
            "Número de Clientes Únicos com Pagamento": num_unique_clients,
            "Valor Médio por Pagamento": formatar_moeda(avg_payment_value),
            "Total Pago por Mês (Dados)": df_mensal_sum.to_markdown(),
            "Top 10 Clientes por Total Pago (Dados)": df_top_clients.to_markdown(),
        }

        # --- Construir o Prompt para a IA ---
        prompt = """
        Analise os dados de pagamentos de uma empresa fornecidos abaixo.
        Forneça insights de negócios em formato de bullet points fáceis de entender.
        Identifique tendências no crescimento mensal total e nos pagamentos por cliente.
        Sugira possíveis áreas para focar para aumentar a receita ou reter clientes.

        Dados para Análise:
        """
        for key, value in insights_data.items():
            prompt += f"\n\n## {key}:\n{value}"
        prompt += """

        Com base nesses dados, quais são os principais insights e recomendações de negócios?
        """

        # --- Chamar a API da IA ---
        try:
         
            model_name_to_try = 'models/gemini-2.0-flash'

            model = genai.GenerativeModel(model_name_to_try)

            # Mostra um indicador de carregamento
            with st.spinner(f"A IA ({model_name_to_try}) está analisando os dados e gerando insights..."):
                response = model.generate_content(prompt)

            # --- Exibir os Insights ---
            st.subheader("Insights Gerados pela IA:")
            st.write(response.text)

        except Exception as e:
            # Este except agora vai capturar erros como o 404 de modelo não encontrado
            # ou outros erros na chamada da API
            st.error(f"Erro ao chamar a API da IA: {e}")
            st.warning(f"Pode ser que o modelo '{model_name_to_try}' não esteja disponível para sua chave ou região, ou que haja outro problema na chamada.")
            st.info("Se o erro persistir, tente alterar o nome do modelo na linha `model_name_to_try` para outro nome como 'models/gemini-1.0-pro'.")


    elif not api_configured:
        st.warning("Não é possível gerar insights: A API da IA não foi configurada corretamente. Verifique o arquivo `.streamlit/secrets.toml`.")
    elif con is None: # Verifica se a conexão com o DB falhou
         st.warning("Não é possível gerar insights: Falha ao conectar ao banco de dados.")
    else:
        st.info("Dados insuficientes para gerar insights. Verifique se os DataFrames de resumo não estão vazios após carregar os dados.")