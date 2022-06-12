---
layout: post
title:  "Criando um CRUD com .NET 5, MySQL, Angular 11, Keycloak, Phometheus e Grafana — Parte 1"
author: alan
categories: [ Docker ]
tags: [ Keycloak ]
image: assets/images/crud-1.png
rating: 4.5
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

{% highlight ccp %}
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
{% endhighlight %}

## Criando a aplicação .NET
Tendo criado o nosso banco de dados, podemos iniciar a criação da API, vamos fazer isso executando os seguintes comandos na raiz do nosso repositório:

```bash
mkdir Products.API
cd Products.API
dotnet new webapi
```