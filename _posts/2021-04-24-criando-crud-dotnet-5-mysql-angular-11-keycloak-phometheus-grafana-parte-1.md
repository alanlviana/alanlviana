---
layout: post
title:  "Criando um CRUD com .NET 5, MySQL, Angular 11, Keycloak, Phometheus e Grafana — Parte 1"
author: alan
categories: [ Docker ]
tags: [ Keycloak ]
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

{% gist 8537653416939a70926239615ea4c071 docker-compose.yml %}

## Criando a aplicação .NET
Tendo criado o nosso banco de dados, podemos iniciar a criação da API, vamos fazer isso executando os seguintes comandos na raiz do nosso repositório:

>mkdir Products.API

>cd Products.API

>dotnet new webapi


Depois de criada a aplicação podemos abrir o visual studio code nessa pasta:

>code .

## Apagando arquivos desnecessários
O projeto de exemplo criado possui um modelo e um controller que não é necessário para o nosso estudo, podemos apagar os seguintes arquivos:


>Controllers\WeatherForecastController.cs

>WeatherForecast.cs

## Instalando Entity Framework Core
Nesse projeto vamos fazer uso do entityframework com MySQL, para isso precisamos da seguinte dependência:

>dotnet add package Pomelo.EntityFrameworkCore.MySql --version 5.0.0-alpha.

Também vamos precisar da seguinte dependência para trabalhar com migrations:


>dotnet add package Microsoft.EntityFrameworkCore.Design --version 5.0.5


## Configuração do banco de dados:
Adicione as seguintes ConnectionsString nos arquivos de appsettings.json:

{% gist 614fa421ce9bcb09ef79d05af1646cca appsettings.json %}

A diferença entre os dois arquivos está que no arquivo de desenvolvimento usamos localhost como nome do server, já no nosso arquivo de produção usamos db, que é o nome do nosso container de banco de dados dentro do docker-compose.

{% gist 16214ecd70485159fc2efc82d02efdc9 appsettings.Development.json %}

## Criando nosso modelo, contexto e repositório
Vamos criar a classe que vai representar o nosso modelo de produtos, para isso devemos criar uma pasta Models e dentro dela uma classe Product.cs:
{% gist 928c336bb8dc9780762c38db1f8916fa Products.cs %}

Agora iremos criar uma interface que define as responsabilidades do nosso repositório, essa classe deve ser criada dentro de Repositories/Interfaces, com o nome IProductRepository.cs:

{% gist 6a676731bbb518c6f9d27af097f90062 IProductRepositoy.cs %}

Também criaremos uma classe que implementa essa interface, ela pode ficar dentro da pasta Repositories e eu nomeei de ProductRepository.cs:

{% gist 3cd2d060692ac86a926a252f4516e4b7 ProductRepository.cs %}

## Configurando Entity Framework Core e Injeção de dependência
Precisamos configurar no método ConfigureServices da classe Startup o banco de dados e qual a implementação de IProductRepository devemos usar:

{% gist c773dbf8fe855a11d9cd9b5bac3f3c26 Startup.cs %}

## Criando nosso ProductsController
Nesse momento podemos criar nosso ProductController.cs dentro da pasta controller, essa é a classe que será responsável por definir os endpoints que nossa API vai responder:

{% gist 026d04e4a31f24e5e83fd737c850f643 ProductsController.cs %}

## Executando banco de dados e criando migrations
Para executar nossa infraestrutura atual podemos ir na raiz do nosso repositório ( e fora da nossa pasta Products.API ) e executar o comando:

>docker-compose up

Usando outro prompt de comando( afinal esse fica bloqueado enquanto nossa aplicação estiver ativa ), podemos voltar na pasta Projects.API e rodar o comando para criação da nossa migration:

>dotnet ef migrations add Initial

Nesse passo o entity framework vai comparar o nosso contexto com a estrutura do banco de dados que está rodando dentro do docker, sabendo assim o que precisa ser alterado no banco de dados.

O resultado dessa comparação deve estar na pasta Migrations (criada pelo Entity Framework):

{% gist 68b4a59ecb0f86d5875c5e46768bf5ee 20210414022509_Initial.cs %}

## Configurando a aplicação para rodar migrations automáticamente:

No método Configure da class Startup, podemos receber nosso contexto por parâmetro e executar migrations pendentes:

{% gist 7a244d1e9e4bd738894f82964b943391 Startup.cs %}

Nesse momento podemos rodar nossa aplicação! Isso pode ser feito executando o comando:

>dotnet run

Após o fim da execução podemos acessar [https://localhost:5001/swagger](https://localhost:5001/swagger) no navegador e verificar a documentação da API criada.

![Imagem da API dentro da ferramenta Swagger](/assets/images/crud-1-swagger.png "API Visualizada no Swagger").

## Rodando a API via docker-compose
Para rodar nossa API junto ao banco de dados ao subir nossa infra estrutura precisamos criar dentro da pasta Products.API o arquivo Dockerfile:

{% gist 99ddc50d5eae0dfc4b9f6766c3fe79c9 Dockerfile %}

Nesse arquivo Dockerfile usamos o Dockerize para esperar o banco de dados estar pronto antes de executar nossa API.

Agora só precisamos configurar nossa API no arquivo docker-compose.yml na raiz do repositório, ficando da seguinte maneira:

{% gist 52cd17fc303b6bf8e18e67e2a0862ed4 docker-compose.yml %}

Feita essa configuração, podemos buildar e subir nossa infraestrutura com o seguinte comando na raiz do repositório:

>docker-compose up --build

Ufa! Acho que chegamos ao fim dessa primeira parte! Espero que tenham gostado da aplicação até aqui!

Caso tenham dúvidas ou sugestões, deixem nos comentários :D

Segue também o link do repositório com todo o código da aplicação até aqui:

[Repositório Products Management](https://github.com/alanlviana/Products-Management/tree/v1)