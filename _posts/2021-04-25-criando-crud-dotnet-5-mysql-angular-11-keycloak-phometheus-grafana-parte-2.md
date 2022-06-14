---
layout: post
title:  "Criando um CRUD com .NET 5, MySQL, Angular 11, Keycloak, Phometheus e Grafana — Parte 2"
author: alan
categories: [ On-Premise ]
tags: [ Keycloak, postman, .netcore, docker, entity-framework ]
image: assets/images/crud-2.png
---
Esse artigo faz parte de uma série onde criamos uma solução completa de cadastro de produtos, com separação entre API e Frontend, autenticação e monitoramento. Caso não tenha visto a parte 1, ela pode ser encontrada aqui.
Nesse artigo vamos configurar o Keycloak, criando um reaml e um client que serão usados pela nossa API para autenticar usuários.
Será configurada a API para validar os tokens recebidos no servidor Keycloak.
Também vamos configurar o Postman para que possamos testar nossa autenticação.

## Subindo uma instancia do Keycloak com Docker

Para ter o servidor de autenticação funcionando em nossas máquinas precisamos criar um banco de dados para usuários e uma instância do keycloak com uma porta exposta para o nosso host, essa configuração deve ser adicionada no arquivo docker-compose.yml:

```yaml
  [...]
  db_auth:
    image: postgres:13
    container_name: db_auth
    environment:
      POSTGRES_DB: keycloak
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: password

  keycloak:
    image: quay.io/keycloak/keycloak:12.0.4
    container_name: keycloak
    environment:
      DB_VENDOR: POSTGRES
      DB_ADDR: db_auth
      DB_DATABASE: keycloak
      DB_USER: keycloak
      DB_SCHEMA: public
      DB_PASSWORD: password
      KEYCLOAK_USER: admin
      KEYCLOAK_PASSWORD: admin123
    ports:
      - 8080:8080
    depends_on:
      - db_auth
    restart: always
```

Agora podemos subir nossa infraestrutura com:

```plaintext
docker-compose up --build
```

Depois de criada a aplicação podemos abrir o visual studio code nessa pasta:

```plaintext
code .
```

Podemos acessar o portal de administração no endereço [http://keycloak:8080/auth/admin](http://keycloak:8080/auth/admin), o usuário e senha de administração está configurada no docker-compose.yml. No nosso caso está como usuário admin e senha admin123.

## Configurando o Keycloak

Primeiro precisamos criar um reaml, que de forma bem abstrata pode ser encarado como um repositório de usuários. Essa criação pode ser feita em:

![Menu lateral do Keycloak Administration Console](/assets/images/crud-2-keycloak.png "Menu lateral do Keycloak Administration Console")

O nome do nosso realm vai ser products_api:

![Tela de cadastro de realm](/assets/images/crud-2-keycloak-add-realm.png "Tela de cadastro de realm")

Não precisamos alterar nenhuma informação na aba General. Na aba Login vamos precisar habilitar o User Registration e desabilitar o Login with Email, ficando da seguinte maneira:

![Configurações de Login](/assets/images/crud-2-keycloak-login.png "Configurações de Login")

Podemos salvar.

Agora vamos criar um cliente chamado api, isso pode ser feito clicando em Clients no menu lateral esquerdo e depois em create.

![Cadastro do Cliente](/assets/images/crud-2-keycloak-add_client.png "Cadastro do Cliente")

Podemos salvar.

Precisamos adicionar a url _http://localhost:4200/*_ (URL que nossa aplicação angular vai ter) ao campo Valid Redirect URIs e * ao campo Web Origins (Para não termos problemas com CORS):

![Configuração do Cliente](/assets/images/crud-2-keycloak-configure-client.png "Configuração do Cliente")

## Exportando nossas configurações do Keycloak

Sempre que destruímos nosso container essa configuração é perdida, para evitar ter que fazer essa configuração a cada execução, vamos exportar nosso realm para um arquivo.

Para exportar o realm acessamos a opção _Export_ no menu lateral esquerdo.

Vamos marcar as opções _Export groups and roles_ e a opção _Export Clients_:

![Tela de exportação de realm](/assets/images/crud-2-keycloak-export.png "Tela de exportação de realm")

Podemos exportar e guardar esse arquivo.

## Importando automaticamente o reaml

Para automatizar o processo de criação do realm criaremos uma pasta chamada docker na raiz do nosso repositório. Dentro dessa pasta vamos criar uma outra pasta chamada keycloak e dentro dela vamos colocar o arquivo de configuração do reaml que baixamos no passo anterior.

O caminho final do arquivo dentro do nosso repositório deve ser:

```plaintext
docker\keycloak\realm-export.json
```

Depois disso precisaremos alterar a configuração do nosso keycloak dentro do arquivo docker-compose.yml:

```yaml
[...]
  keycloak:
    image: quay.io/keycloak/keycloak:12.0.4
    container_name: keycloak
    volumes:
      - ./docker/keycloak:/opt/jboss/keycloak/imports
    environment:
      KEYCLOAK_IMPORT: /opt/jboss/keycloak/imports/realm-export.json
      DB_VENDOR: POSTGRES
      DB_ADDR: db_auth
      DB_DATABASE: keycloak
      DB_USER: keycloak
      DB_SCHEMA: public
      DB_PASSWORD: password
      KEYCLOAK_USER: admin
      KEYCLOAK_PASSWORD: admin123
    ports:
      - 8080:8080
    depends_on:
      - db_auth
    restart: always
```

No trecho acima adicionamos um volume para compartilhar com o container a pasta criada anteriormente e usamos a variável de ambiente _KEYCLOAK_IMPORT_ para informar ao keycloak que arquivo deve ser importado na criação do serviço.

## Configurando nossa maquina para uso do keycloak

O servidor do keycloak precisa ter o mesmo endereço tanto para o frontend que vai obter o token no navegador, quanto para a api que vai validar o token dentro do docker. No nosso caso, dentro do ambiente do docker, nosso container responde pelo nome de keycloak, pois esse é o nome do nosso serviço. Fora do docker, quando acessamos o servidor usamos o endereço localhost:8080.

Essa diferença de nome de host faz com que os tokens não possam ser validados. Para corrigir isso precisaremos criar um endereçamento keycloak no nosso host, adicionando ao arquivo C:\Windows\System32\drivers\etc\hosts a seguinte entrada:

```plaintext
# Para usar o keycloak via docker
127.0.0.1 keycloak
```

Dessa forma fazemos com que seja redirecionado para nosso ip de loopback o host “keycloak”.

Podemos testar se tudo funcionou acessando a url [http://keycloak:8080/auth/admin](http://keycloak:8080/auth/admin), que deve levar para o mesmo servidor que configuramos anteriormente.

## Configurando a API .NET para validar tokens no keycloak

Nesse passo vamos configurar nosso controller para exigir autenticação e vamos fazer com que nossa API valide os tokens recebidos no keycloak. Para isso vamos começar indo até a parta Products.API com o terminal e instalando as seguintes dependências:

```plaintext
dotnet add package Microsoft.AspNetCore.Authentication.JwtBearer --version 5.0.5
```

Vamos também precisar criar nossa configuração de JWT nos arquivos appsettings.json e appsettings.Development.json:

```json
{
  "Jwt": {
    "Authority": "http://keycloak:8080/auth/realms/products_api",
    "Audience": "account"
  },
  [...]
}
```

Nesse caso vamos usar o mesmo host para desenvolvimento e produção, pois já equalizamos isso na configuração do arquivo hosts.
Nosso próximo passo está no arquivo _Startup.cs_, vamos precisar adicionar as seguintes instruções no método ConfigureServices:

```csharp
public void ConfigureServices(IServiceCollection services)
{
    services.AddAuthentication(options =>
    {
        options.DefaultAuthenticateScheme = JwtBearerDefaults.AuthenticationScheme;
        options.DefaultChallengeScheme = JwtBearerDefaults.AuthenticationScheme;
    }).AddJwtBearer(o =>
    {
        o.Authority = Configuration["Jwt:Authority"];
        o.Audience = Configuration["Jwt:Audience"];
        o.RequireHttpsMetadata = false;
        o.Events = new JwtBearerEvents()
        {
            OnAuthenticationFailed = c =>
            {
                c.Response.StatusCode = 500;
                c.Response.ContentType = "text/plain";
                return c.Response.WriteAsync(c.Exception.ToString());
            }
        };
    });
    [...]
}
```

Também precisamos configurar nosso app para usar autenticação no método Configure:

```csharp
public void Configure(IApplicationBuilder app, IWebHostEnvironment env, DatabaseContext context)
{
    app.UseAuthentication();
    [...]
}
```

Também precisamos anotar a classe ProductsController com AutorizeAttribute:

```csharp
[ApiController]
[Route("[controller]")]
[Authorize]
public class ProductsController : ControllerBase
{
    [...]
}
```

Para que nossa documentação reflita nosso modelo de autenticação, precisamos dentro de _ConfigureServices_ adicionar as instruções _AddSecurityDefinition_ e _AddSecurityRequirement_ no método AddSwaggerGen:

```csharp
services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo { Title = "Products.API", Version = "v1" });
    c.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
    {
        Description = @"Put **_ONLY_** your JWT Bearer token on textbox below!",
        Name = "JWT Authentication",
        BearerFormat = "JWT",
        In = ParameterLocation.Header,
        Type = SecuritySchemeType.Http,
        Scheme = "Bearer"
    });
    c.AddSecurityRequirement(new OpenApiSecurityRequirement()
      {
        {
          new OpenApiSecurityScheme
          {
            Reference = new OpenApiReference
              {
                Type = ReferenceType.SecurityScheme,
                Id = "Bearer"
              },
              Scheme = "oauth2",
              Name = "Bearer",
              In = ParameterLocation.Header,
            },
            new List<string>()
          }
        });
});
```

Por padrão a página que descreve nossa API só é exibida em desenvolvimento, para fins didáticos vamos retirar essa restrição. Para isso vamos retirar as instruções UseSwagger e UseSwaggerUI da condição que verifica se é um ambiente de desenvolvimento no método Configure:

```csharp
[...]
  if (env.IsDevelopment())
  {
      app.UseDeveloperExceptionPage();
  }
  app.UseSwagger();
  app.UseSwaggerUI(c => c.SwaggerEndpoint("/swagger/v1/swagger.json", "Products.API v1"));
[...]
```

Ao acessar [http://localhost:5000/swagger/](http://localhost:5000/swagger/) podemos ver nossa documentação já com o botão Authorize onde podemos configurar nosso token:

![Tela de autenticação do Swagger](/assets/images/crud-2-swaggger-auth.png "Tela de autenticação do Swagger")

## Habilitando CORS

Precisamos configurar nossa API para receber requisições de domínios distintos (CORS), para fins didáticos vamos permitir requisições de qualquer domínio. Essa configuração é feita na classe Startup nos métodos _ConfigureServices_ e _Configure_:

```csharp
    public void ConfigureServices(IServiceCollection services)
    {
        services.AddCors();
        [...]
    }
    
    public void Configure(IApplicationBuilder app, IWebHostEnvironment  DatabaseContext context)
    {
        app.UseCors(builder => builder
            .AllowAnyOrigin()
            .AllowAnyMethod()
            .AllowAnyHeader());
        [...]
    }
```

## Testando nossa autenticação com Postman

Para testar nossa aplicação vou utilizar o postman, mas primeiro precisamos subir nosso ambiente novamente:

```plaintext
docker-compose up --build
```

Já dentro do postman, vamos fazer uma requisição do tipo GET para [http://localhost:5000/products](http://localhost:5000/products) e receberemos um status 401, indicando que não estamos autorizados:

![Requisição não autorizada no postman](/assets/images/crud-2-postman.png "Requisição não autorizada no postman")

Precisamos configurar o postman para obter um token no keycloak e usar esses token na requisição, isso pode ser feito indo a aba Authorization e selecionando o tipo de autenticação _OAuth 2.0_.

Eu preenchi essa tela com os seguintes parâmetros:

```plaintext
Header Prefix: Bearer
Token Name: API
Grant Type: Authorization Code
Callback URL: http://localhost:4200/callback
Authorize using browser: false
Auth URL: http://keycloak:8080/auth/realms/products_api/protocol/openid-connect/auth
Access Token URL:http://keycloak:8080/auth/realms/products_api/protocol/openid-connect/token
Client ID: api
Client Secret: <vazio>
Scope: email
State: <vazio>
Client Authentication: Send as Basic Auth header
```

Agora já podemos clicar no botão Get new access token, fazendo isso vamos nos deparar com a tela de login do nosso sistema:

![Tela de Login da aplicação](/assets/images/crud-2-login.png "Tela de Login da aplicação")

Como ainda não temos um usuário, podemos clicar no botão _Register_.

Ao fim do registro o Postman vai mostrar o token recebido:

![Gerenciador de Tokens do Postman](/assets/images/crud-2-postman-token-manager.png "Gerenciador de Tokens do Postman")

Podemos clicar no botão _Use Token_ e enviar novamente nossa requisição:

![Requisição realizada com sucesso](/assets/images/crud-2-postman-success.png "Requisição realizada com sucesso")

Pronto, recebemos um status 200 que indica que a operação foi efetuada com sucesso!

Assim finalizamos nossa segunda parte da construção do sistema, na próxima parte vamos criar nossa aplicação angular para consumir nossa API.

Gostou? Tem alguma sugestão ou dúvida? Deixa ai nos comentários!

Segue o link do repositório no estado atual do projeto:

[Repositório Products Management](https://github.com/alanlviana/Products-Management/tree/v2)
