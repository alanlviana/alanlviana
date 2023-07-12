---
layout: post
title:  "Implementando TLS mútuo no Amazon API Gateway"
author: alan
categories: [ AWS ]
tags: [ api gateway, mtls, tls ]
image: assets/images/mtls_cover.png
---

Nesse artigo passaremos pelo processo de criação de chaves, implementação e consumo de TLS Mútuo em um AWS API Gateway.

## Introdução
 
Um fluxo de autenticação utilizando mTLS (Mutual Transport Layer Security) visa que ambas as partes de uma conexão de rede se autentiquem de forma mutua, sendo assim servidor e cliente validam os certificados um do outro. 

Nesse artigo crieremos par de chaves RSA, criaremos um certificado para nossa API no AWS ACM, criaremos um dominio customizado para nossa API, enfim, tentaremos cobrir os principais pontos da implementação desse fluxo de autenticação.

## Pré-requisitos
Para que possamos começar com essa implementação, é necessário:
- Possuir um conhecimento básico de AWS S3 e AWS API Gateway
- Possuir uma API exposta no AWS API Gateway.
- Possuir um dominio na internet.

## Criando um par de chaves RSA
Iniciaremos criando um par de chaves RSA, primeiro criamos nossa chave privada e um arquivo .csr (Certificate Signing Request) que contem as informações que estão contidas no nosso certificado.

```bash
openssl req -newkey rsa:2048  \
  -nodes -keyout cliente1.key \
  -out cliente1.csr
```
O usamos o comando abaixo para criar um arquivo .crt, que é o certificado assinado utilizando a chave privada:
```bash
openssl x509 -signkey cliente1.key \
  -in cliente1.csr -req -days 365 \
  -out cliente1.crt
```
Depois disso podemos copiar o certificado para um novo arquivo de Truststore:
```bash
cat cliente1.crt > truststore.pem
```

Uma vez criado arquivo de truststore, você já podemos criar um bucket s3 e realizar o upload desse arquivo para esse bucket, como é uma tarefa trivial, vou pular esses passos nesse artigo.

## Criação de certificado no AWS ACM

Para que possamos criar habilitar o uso de um dominio customizado no API Gateway, precisamos antes criar um certificado no AWS ACM (Amazon Certificate Manager).

Para isso podemos criar o certificado pelo console da AWS seguindo os seguintes passos:

1. Acessar o serviço e clicar em "Request"

2. Solicitar um certificado público
![Solicitar um certificado público](/assets/images/mtls_acm_01.png "Imagem AWS ACM para solicitação de certificado.")

3. Informar o dominio completo que será usado no certificado
![Informar dominio do certificado](/assets/images/mtls_acm_02.png "Imagem com dominio informado para criação de certificado.")

4. O certificado pode ser validado utilizando DNS ou E-mail, selecione a opção desejada. Após a requisição ele aparecerá na lista com validação pendente.
![Certificado pendente de validação](/assets/images/mtls_acm_03.png "Imagem com certificado pendente de validação.")

5. Após a validação o certificado será gerado
![Certificado validado](/assets/images/mtls_acm_04.png "Imagem com certificado gerado.")

## Criação de um dominio personalizado para a API

Precisamos criar um nome de dominio customizado, para isso seguimos os seguintes passos:

1. Acessar recurso "Custom Domain Names" dentro do serviço API Gateway e selecionamos a opção "Create".

2. Preenchemos o dominio que usaremos na API (o mesmo que usamos no ACM). Também habilitamos o "Mutual TLS Authentication" passando o S3 URI da truststore que criamos e enviamos ao S3.
![Configuração do Custom Domain Name](/assets/images/mtls_cnd_01.png "Imagem com configuração do Custom Domain Name.")
3. Na sessão "Endpoint Configuration" selecionamos o certificado que criamos no ACM
![Configuração do Custom Domain Name](/assets/images/mtls_cnd_02.png "Imagem com configuração do Custom Domain Name.")

4. Após criado o custom domain name, podemos acessar as informações que utilizaremos para a configuração do DNS na aba "Endpoint Configuration"
![Configuração do Custom Domain Name](/assets/images/mtls_cnd_03.png "Imagem com configuração do Custom Domain Name.")

5. Podemos vincular a API que queremos proteger na Aba "API mappings" com botão "Configure API mappings". Na nova página podemos clicar em "Add new mapping":
![Configuração do Custom Domain Name](/assets/images/mtls_cnd_04.png "Imagem com configuração do Custom Domain Name.")
Temos um aviso de que o endpoint default da API está ativo, para que a API esteja de fato protegida é necessário desabilitar esse endpoint. Essa uma tarefa relativamente simples que não será coberta nesse artigo. Podemos concluir o processo de mapeamento do dominio.

## Configurando registros em DNS para acesso a API

Como possuo um registro .com.br, vou realizar o cadastro do subdominio criado no registro.br. Caso seu dominio já esteja na custódia da AWS, você pode configurar diretamente no AWS Route 53.
Vamos adicionar um registro do time "CNAME" vinculando o subdominio ao "API Gateway domain name" que podemos consultar no Custom Domain Name.

No meu caso a configuração ficou:
![Configuração do DNS no registro.br](/assets/images/mtls_dns_01.png "Configuração do DNS no registro.br")


## Teste do consumo da API
Após propagado o DNS, podemos utilizar o seguinte comando para tentar consumir a API:

```bash
curl https://mtls.alanlviana.com.br/pets
```

Resultado:
![Consumo de uma API utilizando mTLS - Sem certificado](/assets/images/mtls_curl_01.png "SSL_Connect: Connection reset by peer in connection to mtls.alanlviana.com.br:443")
Podemos observar que o resultado do comando foi uma falha ao tentar se conectar, o que é esperado, pois não utilizamos os certificados criados para consumo da API. Tentando novamente da forma correta:

```bash
curl https://mtls.alanlviana.com.br/pets --cert cliente1.crt --key cliente1.key
```
![Consumo de uma API utilizando mTLS - Com certificado](/assets/images/mtls_curl_02.png "Consumo de uma API utilizando mTLS - Com certificado")

Obtemos sucesso e garantimos que somente quem possuir a chave privada pode consumir a API.

Espero que venha a ser útil para quem está implantando esse fluxo!

Gostou? Tem alguma sugestão ou dúvida? Deixa ai nos comentários!