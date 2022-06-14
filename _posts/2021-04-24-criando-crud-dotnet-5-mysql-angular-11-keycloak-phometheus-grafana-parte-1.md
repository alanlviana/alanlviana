---
layout: post
title:  "Criando um CRUD com .NET 5, MySQL, Angular 11, Keycloak, Phometheus e Grafana — Parte 1"
author: alan
categories: [ On-Premise ]
tags: [ .netcore, docker, entity-framework, web-api, swagger ]
image: assets/images/crud-1.png
---

Nesse artigo pretendo apresentar uma solução completa para uma aplicação simples de cadastro. Para isso vamos construir uma api utilizando .NET 5, que vai incluir, excluir, listar e atualizar produtos em uma base de dados MySQL.

Vamos criar uma aplicação Angular capaz de requisitar todas as funcionalidades da API, apesar de não ser o objetivo do artigo vai haver uma estilização simples e onde vamos usar alguns recursos legais de CSS.

Por ultimo, mas não menos importante, vamos implementar autenticação e monitoramento para a aplicação, para isso vamos utilizar o Keycloak para gerenciamento de usuários e para o acompanhamento de métricas em tempo real da API utilizaremos phometheus e grafana.

## Requisitos
Para esse tutorial tenho as seguintes ferramentas instaladas:

* Docker na versão 20
* .NET na versão 5.0
* Angular CLI na versão 11
* Visual Studio Code

## Roteiro
Esse projeto seria muito grande se fosse escrito em somente uma parte, então ele será dividido da seguinte maneira:

1. Criação da API .NET (Neste artigo)
2. Configurando a autenticação com Keycloak
3. Criação do Frontend Angular
4. Configurando monitoração com Prometheus e Grafana

## Configurando banco de dados
Vamos começar com a criação e configuração do nosso arquivo docker-compose.yml, com isso vamos ganhar uma instancia do banco MySQL que será usada para armazenar nosso cadastro de produtos.

Crie o arquivo docker-compose.yml na raiz do seu repositório com a seguinte estrutura:

```yaml
version: '3.0'

services:
  db:
    image: mysql:5.7
    container_name: db
    environment:
      MYSQL_RANDOM_ROOT_PASSWORD: 1
      MYSQL_DATABASE: productsdb
      MYSQL_USER: dbuser
      MYSQL_PASSWORD: dbuserpassword
    ports:
      - "3306:3306"
    restart: always
```

## Criando a aplicação .NET

Tendo criado o nosso banco de dados, podemos iniciar a criação da API, vamos fazer isso executando os seguintes comandos na raiz do nosso repositório:

```yaml
mkdir Products.API
cd Products.API
dotnet new webapi
```

Depois de criada a aplicação podemos abrir o visual studio code nessa pasta:

```plaintext
code .
```

## Apagando arquivos desnecessários

O projeto de exemplo criado possui um modelo e um controller que não é necessário para o nosso estudo, podemos apagar os seguintes arquivos:

```plaintext
Controllers\WeatherForecastController.cs
WeatherForecast.cs
```

## Instalando Entity Framework Core

Nesse projeto vamos fazer uso do entityframework com MySQL, para isso precisamos da seguinte dependência:

```plaintext
dotnet add package Pomelo.EntityFrameworkCore.MySql --version 5.0.0-alpha.
```

Também vamos precisar da seguinte dependência para trabalhar com migrations:

```plaintext
dotnet add package Microsoft.EntityFrameworkCore.Design --version 5.0.5
```

## Configuração do banco de dados

Adicione as seguintes ConnectionsString nos arquivos de appsettings.json:

```json
{
  [...]
  "ConnectionStrings": {
    "DefaultConnection": "server=db;port=3306;userid=dbuser;password=dbuserpassword;database=productsdb;"
  }
  [...]
}
```

A diferença entre os dois arquivos está que no arquivo de desenvolvimento usamos localhost como nome do server, já no nosso arquivo de produção usamos db, que é o nome do nosso container de banco de dados dentro do docker-compose.

```json
{
  [...]
  "ConnectionStrings": {
    "DefaultConnection": "server=localhost;port=3306;userid=dbuser;password=dbuserpassword;database=productsdb;"
  }
  [...]
}
```

## Criando nosso modelo, contexto e repositório

Vamos criar a classe que vai representar o nosso modelo de produtos, para isso devemos criar uma pasta Models e dentro dela uma classe Product.cs:

```csharp
using System;
using System.ComponentModel.DataAnnotations;

namespace Products.API.Models
{
    public class Product
    {

        [Required]
        public Guid Id { get; set; }
        [Required(AllowEmptyStrings = false, ErrorMessage = "The Product Name is Required")]
        public string ProductName { get; set; }
        [Required(AllowEmptyStrings = false, ErrorMessage = "The SKU is required.")]
        public string SKU { get; set; }
        [Required(AllowEmptyStrings = false, ErrorMessage = "The UPC is required.")]
        public string UPC { get; set; }
        [Range(0, 1_000_000, ErrorMessage = "The product price must to be between 0 and 1.000.000")]
        public decimal Price { get; set; }
    }
}
```

Agora iremos criar uma interface que define as responsabilidades do nosso repositório, essa classe deve ser criada dentro de Repositories/Interfaces, com o nome IProductRepository.cs:

```csharp
using System;
using System.Collections.Generic;
using Products.API.Models;

namespace Products.API.Repositories.Interfaces
{
    public interface IProductRepository
    {
        Product Insert(Product product);
        IEnumerable<Product> GetAll();
        void Delete(Guid productId);
        Product GetById(Guid id);
        void Update(Guid productId, Product product);
    }
}
```

Também criaremos uma classe que implementa essa interface, ela pode ficar dentro da pasta Repositories e eu nomeei de ProductRepository.cs:

```csharp
using System;
using System.Collections.Generic;
using System.Linq;
using Products.API.Models;
using Products.API.Repositories.Interfaces;

namespace Products.API.Repositories
{
    public class ProductRepository: IProductRepository
    {
        public DatabaseContext Context { get; }

        public ProductRepository(DatabaseContext context)
        {
            this.Context = context;
        }

        public Product Insert(Product product)
        {
            Context.Products.Add(product);
            Context.SaveChanges();

            return product;
        }

        public IEnumerable<Product> GetAll()
        {
            var list = Context.Products;
            return list;
        }

        public void Delete(Guid productId)
        {
            var product = Context.Products.Where(ta => ta.Id == productId).FirstOrDefault();
            Context.Products.Remove(product);
            Context.SaveChanges();
        }

        public Product GetById(Guid productId)
        {
            return Context.Products.Where(a => a.Id == productId).FirstOrDefault();
        }

        public void Update(Guid productId, Product product)
        {
            var oldProduct = Context.Products.Where(ta => ta.Id == productId).FirstOrDefault();
            if (oldProduct == null) return;

            oldProduct.ProductName = product.ProductName;
            oldProduct.SKU = product.SKU;
            oldProduct.UPC = product.UPC;
            oldProduct.Price = product.Price;

            Context.SaveChanges();
        }
    }
}
```

## Configurando Entity Framework Core e Injeção de dependência

Precisamos configurar no método ConfigureServices da classe Startup o banco de dados e qual a implementação de IProductRepository devemos usar:

```csharp
[...]
            services.AddDbContextPool<DatabaseContext>(options => {
                var connectionString = Configuration.GetConnectionString("DefaultConnection");
                var serverVersion = ServerVersion.AutoDetect(connectionString);
                options.UseMySql(connectionString, serverVersion);
            });
[...]
            services.AddTransient<IProductRepository, ProductRepository>();
[...]
```

## Criando nosso ProductsController

Nesse momento podemos criar nosso ProductController.cs dentro da pasta controller, essa é a classe que será responsável por definir os endpoints que nossa API vai responder:

```csharp
using System;
using System.Collections.Generic;
using Microsoft.AspNetCore.Mvc;
using Products.API.Models;
using Products.API.Repositories.Interfaces;

namespace Products.API.Controllers
{
    [ApiController]
    [Route("[controller]")]
    public class ProductsController : ControllerBase
    {
        public IProductRepository ProductRepository { get; }
        public ProductsController(IProductRepository productRepository)
        {
            ProductRepository = productRepository;
        }


        /// <summary>
        /// Get all products
        /// </summary>
        /// <returns>product list</returns>
        [ProducesResponseType(typeof(IEnumerable<Product>), 200)]
        [HttpGet]
        public IActionResult GetAll()
        {
            return Ok(ProductRepository.GetAll());
        }

        /// <summary>
        /// Get product by ID
        /// </summary>
        /// <returns></returns>
        /// <response code="200">Product found.</response>
        /// <response code="404">Product not found.</response>
        [ProducesResponseType(typeof(Product), 200)]
        [HttpGet("{id}")]
        public IActionResult GetById(Guid id)
        {
            var product = ProductRepository.GetById(id);

            if (product == null)
            {
                return NotFound();
            }

            return Ok(product);
        }

        /// <summary>
        /// Remove product by ID
        /// </summary>
        /// <returns></returns>
        /// <response code="200">Product removed.</response>
        [ProducesResponseType(typeof(Product), 200)]
        [HttpDelete("{id}")]
        public IActionResult RemoveById(Guid id)
        {
            ProductRepository.Delete(id);
            return Ok();
        }

        /// <summary>
        /// Create a new product
        /// </summary>
        /// <param name="newProduct">new product details</param>
        /// <response code="201">product created.</response>
        /// <response code="400">bad request</response>
        [ProducesResponseType(typeof(Product), 201)]
        [ProducesResponseType(400)]
        [HttpPost]
        public IActionResult Insert(Product newProduct)
        {
            newProduct.Id = Guid.NewGuid();
            ProductRepository.Insert(newProduct);
            return CreatedAtAction(nameof(GetById), new { id = newProduct.Id }, newProduct);
        }

        /// <summary>
        /// Update a product
        /// </summary>
        /// <param name="id">product id</param>
        /// <param name="newProduct">new product details</param>
        /// <response code="201">product updated.</response>
        /// <response code="400">bad request</response>
        [ProducesResponseType(typeof(Product), 201)]
        [ProducesResponseType(400)]
        [HttpPut("{id}")]
        public IActionResult Update(Guid id, Product newProduct)
        {
            ProductRepository.Update(id, newProduct);
            return Ok();
        }

    }
}
```

## Executando banco de dados e criando migrations

Para executar nossa infraestrutura atual podemos ir na raiz do nosso repositório ( e fora da nossa pasta Products.API ) e executar o comando:

```plaintext
docker-compose up
```

Usando outro prompt de comando( afinal esse fica bloqueado enquanto nossa aplicação estiver ativa ), podemos voltar na pasta Projects.API e rodar o comando para criação da nossa migration:

```plaintext
dotnet ef migrations add Initial
```

Nesse passo o entity framework vai comparar o nosso contexto com a estrutura do banco de dados que está rodando dentro do docker, sabendo assim o que precisa ser alterado no banco de dados.

O resultado dessa comparação deve estar na pasta Migrations (criada pelo Entity Framework):

```csharp
using System;
using Microsoft.EntityFrameworkCore.Migrations;

namespace Products.API.Migrations
{
    public partial class Initial : Migration
    {
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "Products",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "char(36)", nullable: false),
                    ProductName = table.Column<string>(type: "longtext CHARACTER SET utf8mb4", nullable: false),
                    SKU = table.Column<string>(type: "longtext CHARACTER SET utf8mb4", nullable: false),
                    UPC = table.Column<string>(type: "longtext CHARACTER SET utf8mb4", nullable: false),
                    Price = table.Column<decimal>(type: "decimal(65,30)", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Products", x => x.Id);
                });
        }

        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "Products");
        }
    }
}
```

## Configurando a aplicação para rodar migrations automáticamente

No método Configure da class Startup, podemos receber nosso contexto por parâmetro e executar migrations pendentes:

```csharp
public void Configure(IApplicationBuilder app, IWebHostEnvironment env, DatabaseContext context)
{
    [...]
    context.Database.Migrate();
}
```

Nesse momento podemos rodar nossa aplicação! Isso pode ser feito executando o comando:

```plaintext
dotnet run
```

Após o fim da execução podemos acessar [https://localhost:5001/swagger](https://localhost:5001/swagger) no navegador e verificar a documentação da API criada.

![Imagem da API dentro da ferramenta Swagger](/assets/images/crud-1-swagger.png "API Visualizada no Swagger").

## Rodando a API via docker-compose

Para rodar nossa API junto ao banco de dados ao subir nossa infra estrutura precisamos criar dentro da pasta Products.API o arquivo Dockerfile:

```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:5.0 AS build-env
WORKDIR /app

# Copy csproj and restore as distinct layers
COPY *.csproj ./
RUN dotnet restore

# Copy everything else and build
COPY . ./
RUN dotnet publish -c Release -o out

# Build runtime image
FROM mcr.microsoft.com/dotnet/aspnet:5.0 as publishing
WORKDIR /app
COPY --from=build-env /app/out .

RUN apt-get update && apt-get install -y wget

ENV DOCKERIZE_VERSION v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && rm dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

CMD dockerize -wait tcp://db:3306 -timeout 30s dotnet Products.API.dll
```

Nesse arquivo Dockerfile usamos o Dockerize para esperar o banco de dados estar pronto antes de executar nossa API.

Agora só precisamos configurar nossa API no arquivo docker-compose.yml na raiz do repositório, ficando da seguinte maneira:

```yaml
version: '3.0'

services:
  db:
    image: mysql:5.7
    container_name: db
    environment:
      MYSQL_RANDOM_ROOT_PASSWORD: 1
      MYSQL_DATABASE: productsdb
      MYSQL_USER: dbuser
      MYSQL_PASSWORD: dbuserpassword
    ports:
      - "3306:3306"
    restart: always

  api:
    depends_on:
      - db
    container_name: api
    build: Products.API/.
    ports:
      - "5000:80"
    restart: always
```

Feita essa configuração, podemos buildar e subir nossa infraestrutura com o seguinte comando na raiz do repositório:

```plaintext
docker-compose up --build
```

Ufa! Acho que chegamos ao fim dessa primeira parte! Espero que tenham gostado da aplicação até aqui!

Caso tenham dúvidas ou sugestões, deixem nos comentários :D

Segue também o link do repositório com todo o código da aplicação até aqui:

[Repositório Products Management](https://github.com/alanlviana/Products-Management/tree/v1)
