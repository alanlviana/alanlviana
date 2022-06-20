---
layout: post
title:  "Criando um CRUD com .NET 5, MySQL, Angular 11, Keycloak, Phometheus e Grafana — Parte 4"
author: alan
categories: [ On-Premise ]
tags: [ grafana, dotnet, phometheus, docker ]
image: assets/images/crud-4.png
---
Nesse artigo vamos alterar nossa API para fornecer métricas de uso, configurar o phometheus para coletar essas métricas e configurar um dashboard no grafana para acompanhar tudo isso de forma visual.

## Instalando dependências

Primeiro precisamos instalar as dependências do App Metrics, biblioteca que utilizaremos para criar a monitoração, para isso executamos os seguintes comandos na pasta Products.API:

```plaintext
dotnet add package App.Metrics.AspNetCore.All --version 4.2.0
dotnet add package App.Metrics.Formatters.Prometheus --version 4.2.0
```

## Configurando a API para fornecer métricas

Agora vamos ao arquivo _Program.cs_ e configuraremos nosso host para usar métricas, o arquivo deve ficar como a seguir:

```csharp
using App.Metrics;
using App.Metrics.AspNetCore;
using App.Metrics.Formatters.Prometheus;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Hosting;

namespace Products.API
{
    public class Program
    {
        public static void Main(string[] args)
        {
            CreateHostBuilder(args).Build().Run();
        }

        public static IHostBuilder CreateHostBuilder(string[] args) {

            var hostBuilder = Host.CreateDefaultBuilder(args)
                                  .UseMetrics(options =>
                                      {
                                          options.EndpointOptions = endpointsOptions =>
                                          {
                                              endpointsOptions.MetricsTextEndpointOutputFormatter = new MetricsPrometheusTextOutputFormatter();
                                              endpointsOptions.MetricsEndpointOutputFormatter = new MetricsPrometheusTextOutputFormatter();
                                          };
                                      })
                                  .ConfigureWebHostDefaults(webBuilder =>
                                  {
                                      webBuilder.UseStartup<Startup>();
                                  });
            return hostBuilder;
        }            
    }
}
```

Para esse arquivo configuramos o método _UseMetrics_ para os formatters do phometheus. Também precisamos adicionar a seguinte instrução dentro do método _ConfigureServices_ do arquivo Startup.cs:

```csharp
public void ConfigureServices(IServiceCollection services)
{
  [...]
  services.AddMvc().AddMetrics();
}
```

Precisamos dessa configuração para que o App Metrics consiga capturar métricas de cada rota do nosso sistema.

## Configurando o Phometheus

O prometheus será responsável por capturar as métricas na nossa API a cada intervalo de tempo, essa configuração é feita no arquivo _prometheus.yml_ que deve ser criado no seguinte caminho:

```plaintext
docker\prometheus\prometheus.yml
```

O conteúdo desse arquivo deve ser:

```yaml
scrape_configs:
- job_name: api
  scrape_interval: 5s
  static_configs:
  - targets:
    - api:80
  metrics_path: metrics-text
```

Nesse arquivo estamos configurando um job que será executado a cada 5 segundos e buscará informações no servidor API, na porta 80 e no endpoint _metrics-text_.

Também precisamos configurar nosso _docker-compose.yml_ para subir um servidor Phometheus usando essas configurações:

```yaml
 [...]
  prometheus:
    image: prom/prometheus:v2.26.0
    container_name: prometheus
    ports:
    - 9090:9090
    volumes:
    - ./docker/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    depends_on:
    - api
    restart: always
```

## Configurando o Grafana

Vou mostrar brevemente como realizar a configuração do grafana e depois como podemos automatizar esse processo. Começamos por adicionar ao docker-compose.yml nosso serviço grafana:

```yaml
  [...]
  grafana:
    image: grafana/grafana:6.7.2
    container_name: grafana
    ports:
      - 3000:3000
    depends_on:
      - prometheus
```

Podemos também subir nossa infraestrutura com o comando:

```plaintext
docker-compose up --build -d
```

Ao fim do processo podemos acessar nosso servidor grafana no endereço [http://localhost:3000](http://localhost:3000):

![Página de Login grafana](/assets/images/crud-4-login-grafana.png "Página de Login grafana")

O login padrão é _admin_ e a senha padrão também é _admin_.

Após o login precisamos configurar as fontes de dados que serão utilizadas pelo grafana, podemos fazer isso no menu lateral _Configuration > Data Sources_:

![Caminho para cadastro do Data Source](/assets/images/crud-4-grafana-data-source.png "Caminho para cadastro do Data Source")

Podemos clicar no botão _Add Data Source_ e selecionar o Phometheus:

![Página de cadastro do Data Source — Phometheus](/assets/images/crud-4-grafana-data-source-phometheus.png "Página de cadastro do Data Source — Phometheus")

Precisamos informar a URL do phometheus como [http://prometheus:9090](http://prometheus:9090).

Depois disso podemos clicar no botão _Save & Test_.

## Importando o dashboard

O Grafana possui um repositório enorme de dashboards prontos para uso, no nosso exemplo vou utilizar um dashboard do App Metrics, ele pode ser encontrado no endereço [https://grafana.com/grafana/dashboards/2204/revisions](https://grafana.com/grafana/dashboards/2204/revisions).

Para esse projeto vamos usar a revisão 3 do dashboard, podemos baixar esse arquivo:

![Página de revisões do dashboard](/assets/images/crud-4--grafana-dashboard-revision.png "Página de revisões do dashboard")

Podemos começar a importação do dashboard pelo menu lateral _Create > Import_:

![Caminho para importação do dashboard](/assets/images/crud-4-grafana-create-import.png "Caminho para importação do dashboard")

Na tela apresentada podemos clicar no botão _Upload .json file_ e selecionar o arquivo app-metrics-web-monitoring-prometheus_rev3.json:

![Configuração da fonte de dados do dashboard](/assets/images/crud-4-grafana-configure-dashboard-data-source.png "Configuração da fonte de dados do dashboard")

Para o campo “Prometheus App Metrics” selecionaremos nosso Data Source Phometheus.

Ao clicar em _Import_ nosso dashboard é aberto:

![Dashboard criado](/assets/images/crud-4-grafana-dashboard.png "Dashboard criado")

Podemos abrir nosso frontend, fazer o login e cadastrar alguns produtos, e veremos que o relatório vai ser atualizado alguns segundos depois.

![Métricas gerais da API](/assets/images/crud-4-grafana-dashboard-metrics.png "Métricas gerais da API")

Também podemos acompanhar métricas por endpoint:

![Métricas por endpoint](/assets/images/crud-4-dashboard-metrics-endpoint.png "Métricas por endpoint")

## Exportando o dashboard configurado

Precisamos acessar a configuração do nosso dashboard:

![Configurações do dashboard](/assets/images/crud-4-grafana-dashboard-config.png "Configurações do dashboard")

Podemos clicar em JSON Model:

![Configurações do dashboard - JSON Model](/assets/images/crud-4-dashboard-json-model.png "Configurações do dashboard - JSON Model")

Podemos copiar esse JSON e criar um arquivo chamado dashboard_01.json.

## Automatizando a configuração do Grafana

Nesse ultimo passo vamos criar arquivos para automatizar a criação do Data Source, fazemos isso no arquivo _datasource.yml_ que deve ser criado no caminho:

```plaintext
docker\grafana\provisioning\datasources\datasource.yml
```

O conteúdo desse arquivo deve ser:

```yaml
# config file version
apiVersion: 1

# list of datasources that should be deleted from the database
deleteDatasources:
  - name: Prometheus
    orgId: 1

# list of datasources to insert/update depending
# whats available in the database
datasources:
  # <string, required> name of the datasource. Required
- name: Prometheus
  # <string, required> datasource type. Required
  type: prometheus
  # <string, required> access mode. direct or proxy. Required
  access: proxy
  # <int> org id. will default to orgId 1 if not specified
  orgId: 1
  # <string> url
  url: http://prometheus:9090
  # <string> database password, if used
  password:
  # <string> database user, if used
  user:
  # <string> database name, if used
  database:
  # <bool> enable/disable basic auth
  basicAuth: true
  # <string> basic auth username
  basicAuthUser: admin
  # <string> basic auth password
  basicAuthPassword: foobar
  # <bool> enable/disable with credentials headers
  withCredentials:
  # <bool> mark as default datasource. Max one per org
  isDefault:
  # <map> fields that will be converted to json and stored in json_data
  jsonData:
     graphiteVersion: "1.1"
     tlsAuth: false
     tlsAuthWithCACert: false
  # <string> json object of data that will be encrypted.
  secureJsonData:
    tlsCACert: "..."
    tlsClientCert: "..."
    tlsClientKey: "..."
  version: 1
  # <bool> allow users to edit datasources from the UI.
  editable: true
```

Também criaremos um arquivo para automatizar a importação dos dashboards, esse arquivo se chamara _dashboard.yml_ e deve ser criado no seguinte caminho:

```plaintext
docker\grafana\provisioning\dashboards\dashboard.yml
```

O conteúdo do arquivo dashboard.yml deve ser:

```yaml
apiVersion: 1

providers:
- name: 'Prometheus'
  orgId: 1
  folder: ''
  type: file
  disableDeletion: false
  editable: true
  options:
    path: /etc/grafana/provisioning/dashboards
```

Também precisamos colocar o arquivo dashboard_01.json na pasta dashboards, ficando com o seguinte caminho:

```plaintext
docker\grafana\provisioning\dashboards\dashboard_01.json
```

O último passo é atualizar nosso service grafana no _docker-compose.yml_ para utilizar esses arquivos:

```yaml
  [...]
  grafana:
    image: grafana/grafana:6.7.2
    container_name: grafana
    ports:
      - 3000:3000
    volumes:
      - ./docker/grafana/provisioning/:/etc/grafana/provisioning/
    environment:
      GF_INSTALL_PLUGINS: grafana-piechart-panel,grafana-clock-panel,briangann-gauge-panel,natel-plotly-panel,grafana-simple-json-datasource
    depends_on:
      - prometheus
```

Também configuramos a variável de ambiente com plugins usados pelo nosso dashboard, assim serão instalados automaticamente.

Podemos agora derrubar toda nossa infraestrutura e subir novamente, já com todos os serviços configurados:

```plaintext
docker-compose down
docker-compose up --build -d 
```

![Imagem com todos os serviços criados](/assets/images/crud-4-docker-compose-all-services.png "Imagem com todos os serviços criados")

Assim finalizamos nossa série, espero que tenha sido útil para entender um pouco de cada ferramenta e a forma como elas interagem!

Gostou? Tem alguma sugestão ou dúvida? Deixa ai nos comentários!

Segue o link do repositório no estado atual do projeto:

[Repositório Products Management](https://github.com/alanlviana/Products-Management/tree/v4)
